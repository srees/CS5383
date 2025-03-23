import struct
import socket

# Class for managing reliable data transfer over UDP
# This is a basic form of reliability for a class homework assignment
# and not intended to be thorough! Do not use in production environment!
class RDTOverUDP:
    PACKET_TYPE_CONNECT = 0x01
    PACKET_TYPE_SYNACK = 0x02
    PACKET_TYPE_ACK = 0x03
    PACKET_TYPE_DISCONNECT = 0x04
    PACKET_TYPE_DISCONNECT_ACK = 0x05
    PACKET_TYPE_DATA = 0x06
    PACKET_TYPE_RESET = 0x07

    MORE_FLAG = 0x00
    FINAL_FLAG = 0x01

    # Server states
    STATE_LISTEN = "LISTEN"
    STATE_SYNACK_SENT = "SYNACK_SENT"

    # Client states
    STATE_SYN_REQUESTED = "SYN_REQUESTED"
    STATE_SYNACK_RECEIVED = "SYNACK_RECEIVED"

    # Shared states
    STATE_INIT = "INIT"
    STATE_ESTABLISHED = "ESTABLISHED"
    STATE_CLOSE_WAIT = "CLOSE_WAIT"
    STATE_LAST_ACK = "LAST_ACK"
    STATE_CLOSING = "CLOSING"
    STATE_CLOSED = "CLOSED"

    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.header_format = "!BIIB"
        self.header_size = struct.calcsize(self.header_format)
        self.set_state(self.STATE_INIT)
        self.seq_num = 0 # Holds local sequence number
        self.ack_num = 0 # Holds remote sequence number +1
        self.final = False
        self.udp_socket = None
        self.client_address = host
        self.connect_retry = 3
        self.udp_buffer = 1024
        self.send_byte_size = 8

    def set_state(self, state):
        self.state = state
        print(f"Setting state to {state}")

    def do_reset(self):
        self.seq_num = 0
        self.ack_num = 1
        self.final = False

    def wait_for_packet(self):
        # Receive packet
        data, client_address = self.udp_socket.recvfrom(self.udp_buffer)
        # Store client address
        self.client_address = client_address

        # Split out and parse header
        header = data[:self.header_size]
        payload = data[self.header_size:]
        packet_type, seq_num, ack_num, final = struct.unpack(self.header_format, header)
        print(f"Received packet type {packet_type} with sequence {seq_num}, ack {ack_num}, final {final}, payload '{payload.decode()}'")
        return packet_type, seq_num, ack_num, final, payload

    def rdt_server_wait_connect(self):
        retries = 0
        self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.udp_socket.bind((self.host, self.port))
        self.set_state(self.STATE_LISTEN)
        while not self.state == self.STATE_ESTABLISHED and not retries == self.connect_retry:
            # Get packet
            packet_type, seq_num, ack_num, final, payload = self.wait_for_packet()

            # State machine handling
            # Handle SYN
            if self.state == self.STATE_LISTEN:
                # We really only care if we are receiving a SYN request
                if packet_type == self.PACKET_TYPE_CONNECT:
                    self.ack_num = seq_num + 1
                    # Send a SYNACK packet
                    self.send_packet(self.PACKET_TYPE_SYNACK, b"")
                    self.set_state(self.STATE_SYNACK_SENT)
                elif packet_type == self.PACKET_TYPE_RESET:
                    self.do_reset()
                # Anything else is unexpected, return a RESET
                else:
                    self.send_packet(self.PACKET_TYPE_RESET, b"")
                    self.do_reset()
                    self.set_state(self.STATE_LISTEN)
                    retries += 1
            # Handle ACK
            elif self.state == self.STATE_SYNACK_SENT:
                if packet_type == self.PACKET_TYPE_ACK and ack_num == self.seq_num + 1:
                    self.set_state(self.STATE_ESTABLISHED)
                    self.ack_num = 1 # This is intentional to request the first set of data
                    # No response necessary
                elif packet_type == self.PACKET_TYPE_RESET:
                    self.do_reset()
                # Anything else is unexpected, return a RESET
                else:
                    self.send_packet(self.PACKET_TYPE_RESET, b"")
                    self.do_reset()
                    self.set_state(self.STATE_LISTEN)
                    retries += 1
        if retries == self.connect_retry:
            self.set_state(self.STATE_CLOSED)
            print(f"Failed to connect - connect retry limit reached")

    def rdt_receive(self):
        # We should already have an established connection
        data_complete = False
        buffer = b''

        # Operational loop for reliable receive
        while not self.final and not self.state == self.STATE_CLOSED:

            # Get a packet
            packet_type, seq_num, ack_num, final, payload = self.wait_for_packet()

            # State machine handling
            if self.state == self.STATE_ESTABLISHED:
                # If we have data...
                if packet_type == self.PACKET_TYPE_DATA:
                    # If the sequence number is correct, increment what we expect
                    if seq_num == self.ack_num:
                        self.ack_num += 1
                        # Buffer the data
                        buffer += payload
                        # Send ack (this will be a re-ack for the previous packet if the numbers don't match)
                        self.send_packet(self.PACKET_TYPE_ACK, b"")
                        # Set variable to break out of while loop and return data to caller
                        if final == self.FINAL_FLAG:
                            self.final = True
                    else:
                        self.send_packet(self.PACKET_TYPE_ACK, b"",no_increment=True)
                # Handle disconnect
                elif packet_type == self.PACKET_TYPE_DISCONNECT:
                    self.set_state(self.STATE_CLOSE_WAIT)
                    # Doing this here allows us to close without finishing data send
                    # Adjusting this would be pretty easy - add code to the 'final' section
                    # above to detect the close_wait and finish it off.
                    self.send_packet(self.PACKET_TYPE_DISCONNECT_ACK, b"")
                    self.set_state(self.STATE_CLOSED)
                    self.udp_socket.close()
                elif packet_type == self.PACKET_TYPE_RESET:
                    self.do_reset()
                # Anything else is either unexpected or a reset
                else:
                    self.send_packet(self.PACKET_TYPE_RESET, b"")
                    self.do_reset()
                    self.set_state(self.STATE_LISTEN)
            # Auto-reconnect
            else:
                self.rdt_server_wait_connect()
        self.do_reset()
        return buffer

    def rdt_client_connect(self):
        self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.set_state(self.STATE_INIT)
        retries = 0
        while not self.state == self.STATE_ESTABLISHED and not retries == self.connect_retry:
            # Send options
            if self.state == self.STATE_INIT:
                self.send_packet(self.PACKET_TYPE_CONNECT, b"", use_tuple=True)
                self.set_state(self.STATE_SYN_REQUESTED)
            if self.state == self.STATE_SYNACK_RECEIVED:
                self.send_packet(self.PACKET_TYPE_ACK, b"")
                self.set_state(self.STATE_ESTABLISHED)

            # Listen for response
            if self.state == self.STATE_SYN_REQUESTED:
                # A better implementation would add timouts
                packet_type, seq_num, ack_num, final, payload = self.wait_for_packet()
                # Receive options
                if packet_type == self.PACKET_TYPE_SYNACK and ack_num == self.seq_num + 1:
                    self.ack_num = seq_num + 1
                    self.send_packet(self.PACKET_TYPE_ACK, b"")
                    self.set_state(self.STATE_ESTABLISHED)
                    self.seq_num = 0 # intentional for tracking data from the first segment
                elif packet_type == self.PACKET_TYPE_RESET:
                    self.do_reset()
                else:
                    self.send_packet(self.PACKET_TYPE_RESET, b"")
                    self.set_state(self.STATE_INIT)
                    retries += 1

    def send_packet(self, packet_type, payload, final=0, use_tuple=False, no_increment=False):
        if not no_increment:
            self.seq_num += 1
        print(f"Sending packet type {packet_type} with sequence {self.seq_num}, ack {self.ack_num}, final {final}, payload '{payload.decode()}'")
        header = struct.pack(self.header_format, packet_type, self.seq_num, self.ack_num, final)
        packet = header + payload
        # Send the packet using the UDP socket
        if use_tuple:
            self.udp_socket.sendto(packet, (self.client_address, self.port))
        else:
            self.udp_socket.sendto(packet, self.client_address)

    def rdt_send(self, payload):
        # Split the payload into smaller packets if necessary
        packets = self.split_payload(payload)
        sent = 0
        resend = False
        while sent < len(packets):
            if self.state == self.STATE_ESTABLISHED:
                # Send the packet
                if sent == len(packets) - 1:
                    self.send_packet(self.PACKET_TYPE_DATA, packets[sent], self.FINAL_FLAG, no_increment=resend)
                    self.final = True
                else:
                    self.send_packet(self.PACKET_TYPE_DATA, packets[sent], no_increment=resend)
                # Wait for the ACK
                packet_type, seq_num, ack_num, final, payload = self.wait_for_packet()

                # Check the ACK
                if packet_type == self.PACKET_TYPE_ACK:
                    if ack_num == self.seq_num + 1:
                        sent += 1
                        if self.final:
                            self.do_reset()
                    else:
                        print(f"ack:{ack_num} seq:{self.seq_num}")
                        resend = True
            else:
                # Auto-reconnect
                self.rdt_client_connect()


    def split_payload(self, payload):
        packets = []
        for i in range(0, len(payload), self.send_byte_size):
            packets.append(payload[i:i + self.send_byte_size])
        return packets

    # This is only going to work if the other end is actively listening...
    def close(self):
        while self.state != self.STATE_CLOSED:
            self.set_state(self.STATE_CLOSE_WAIT)
            self.send_packet(self.PACKET_TYPE_DISCONNECT, b"")
            packet_type, seq_num, ack_num, final, payload = self.wait_for_packet()
            if packet_type == self.PACKET_TYPE_DISCONNECT_ACK:
                self.set_state(self.STATE_CLOSED)
        self.udp_socket.close()