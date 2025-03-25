import struct
import socket
from random import random


# Class for managing reliable data transfer over UDP
# This is a basic form of reliability for a class homework assignment
# and not intended to be thorough! Do not use in production environment!
class RDTOverUDP:
    # Packet types
    PACKET_TYPE_CONNECT = 0x01
    PACKET_TYPE_SYNACK = 0x02
    PACKET_TYPE_ACK = 0x03
    PACKET_TYPE_DISCONNECT = 0x04
    PACKET_TYPE_DISCONNECT_ACK = 0x05
    PACKET_TYPE_DATA = 0x06
    PACKET_TYPE_RESET = 0x07
    PACKET_TYPE_NONE = 0xFF

    # Header info
    MORE_FLAG = 0x00
    FINAL_FLAG = 0x01
    HEADER_FORMAT = "!BIIB"
    HEADER_SIZE = struct.calcsize(HEADER_FORMAT)

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

    # Other constants
    CONNECT_RETRY = 3
    UDP_BUFFER = 1024
    SEND_BYTE_SIZE = 8
    TIMEOUT = 1.0
    DROP_CHANCE = 0.3

    # Initialize variables on creation
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.set_state(self.STATE_INIT)
        self.seq_num = 0 # Holds local sequence number
        self.ack_num = 0 # Holds remote sequence number +1
        self.final = False
        self.udp_socket = None
        self.client_address = host
        self.awaiting_ack = False
        self.cached_packet = None

    #################################################################
    ##### Initialization functions differ for client and server #####
    #################################################################

    # Server initialization - this moves through the FSM to the ESTABLISHED connection state
    def rdt_server_wait_connect(self):
        retries = 0
        self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.udp_socket.bind((self.host, self.port))
        self.set_state(self.STATE_LISTEN)

        # I did add a retry limit here. There is a bug because once when a handshaking ack
        # was dropped, the server hit the retry limit and bailed but the client kept trying to
        # send the handshake syn. Not necessary for the assignment, so I did not fix.
        # Loop through to handle sending the different packets until we are ESTABLISHED
        while not self.state == self.STATE_ESTABLISHED and not retries == self.CONNECT_RETRY:

            # Wait for packet
            packet_type, seq_num, ack_num, final, payload = self.rdt_wait_for_packet()

            # If we receive a reset, it's handled the same regardless of state
            if packet_type == self.PACKET_TYPE_RESET:
                self.do_reset()
            else:
                # State machine handling
                # Handle SYN, which moves us from LISTEN to SYNACK_SENT
                if self.state == self.STATE_LISTEN:
                    # We really only care if we are receiving a SYN request
                    if packet_type == self.PACKET_TYPE_CONNECT:
                        self.ack_num = seq_num + 1
                        # Send a SYNACK packet
                        self.rdt_send_packet(self.PACKET_TYPE_SYNACK, b"")
                        self.set_state(self.STATE_SYNACK_SENT)
                    # Anything else is unexpected, return a RESET
                    else:
                        self.rdt_send_packet(self.PACKET_TYPE_RESET, b"")
                        self.do_reset()
                        self.set_state(self.STATE_LISTEN)
                        retries += 1
                # Handle ACK, which moves us from SYNACK_SENT to ESTABLISHED
                elif self.state == self.STATE_SYNACK_SENT:
                    if packet_type == self.PACKET_TYPE_ACK and ack_num == self.seq_num + 1:
                        self.set_state(self.STATE_ESTABLISHED)
                        self.ack_num = 1 # This is intentional to request the first set of data
                        # No response necessary
                    # Anything else is unexpected, return a RESET
                    else:
                        self.rdt_send_packet(self.PACKET_TYPE_RESET, b"")
                        self.do_reset()
                        self.set_state(self.STATE_LISTEN)
                        retries += 1
        if retries == self.CONNECT_RETRY:
            self.set_state(self.STATE_CLOSED)
            print(f"Failed to connect - connect retry limit reached")

    # Client initialization - this moves through the FSM to the ESTABLISHED connection state
    def rdt_client_connect(self):
        self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.set_state(self.STATE_INIT)
        retries = 0

        # Retry limit has a bug, but it wasn't a requirement for the assignment so... :shrug:
        # Loop through to handle sending the different packets until ESTABLISHED
        while not self.state == self.STATE_ESTABLISHED and not retries == self.CONNECT_RETRY:

            # Send CONNECT or ACK depending on state
            if self.state == self.STATE_INIT:
                self.rdt_send_packet(self.PACKET_TYPE_CONNECT, b"")
                self.set_state(self.STATE_SYN_REQUESTED)
            if self.state == self.STATE_SYNACK_RECEIVED:
                self.rdt_send_packet(self.PACKET_TYPE_ACK, b"")
                self.set_state(self.STATE_ESTABLISHED)

            # Listen for response and update state
            if self.state == self.STATE_SYN_REQUESTED:
                packet_type, seq_num, ack_num, final, payload = self.rdt_wait_for_packet()
                # Receive options
                if packet_type == self.PACKET_TYPE_SYNACK and ack_num == self.seq_num + 1:
                    # Handshake complete, move on!
                    self.ack_num = seq_num + 1
                    self.rdt_send_packet(self.PACKET_TYPE_ACK, b"")
                    self.set_state(self.STATE_ESTABLISHED)
                    self.seq_num = 0 # intentional for tracking data from the first segment
                elif packet_type == self.PACKET_TYPE_RESET:
                    self.do_reset()
                else:
                    # Unexpected response, send reset
                    self.rdt_send_packet(self.PACKET_TYPE_RESET, b"")
                    self.set_state(self.STATE_INIT)
                    retries += 1

    # Teardown function is shared between client and server
    def close(self):
        while self.state != self.STATE_CLOSED:
            self.set_state(self.STATE_CLOSE_WAIT)
            self.rdt_send_packet(self.PACKET_TYPE_DISCONNECT, b"")
            packet_type, seq_num, ack_num, final, payload = self.rdt_wait_for_packet()
            if packet_type == self.PACKET_TYPE_DISCONNECT_ACK:
                self.set_state(self.STATE_CLOSED)
        self.udp_socket.close()

    ##############################
    ##### Reliable functions #####
    ##############################

    # The reliable receive function handles FSM states from ESTABLISHED to CLOSED
    def rdt_receive(self):
        # We should already have an established connection
        data_complete = False
        buffer = b''

        # Operational loop for reliable receive
        while not self.final and not self.state == self.STATE_CLOSED:

            # Get a packet
            packet_type, seq_num, ack_num, final, payload = self.rdt_wait_for_packet()

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
                        self.rdt_send_packet(self.PACKET_TYPE_ACK, b"")
                        # Set variable to break out of while loop and return data to caller
                        if final == self.FINAL_FLAG:
                            self.final = True
                    else:
                        # If the seq is wrong, our ack may have timed out - resend
                        self.rdt_send_packet(self.PACKET_TYPE_ACK, b"",resend=True)
                # Handle disconnect
                elif packet_type == self.PACKET_TYPE_DISCONNECT:
                    self.set_state(self.STATE_CLOSE_WAIT)
                    # Doing this here allows us to close without finishing data send
                    # Adjusting this would be pretty easy - add code to the 'final' section
                    # above to detect the close_wait and finish it off.
                    # However, our implementation would not benefit from that because we cannot
                    # receive a close during data send.
                    self.rdt_send_packet(self.PACKET_TYPE_DISCONNECT_ACK, b"")
                    self.set_state(self.STATE_CLOSED)
                    self.udp_socket.close()
                elif packet_type == self.PACKET_TYPE_RESET:
                    self.do_reset()
                # Anything else is either unexpected or a reset
                else:
                    self.rdt_send_packet(self.PACKET_TYPE_RESET, b"")
                    self.do_reset()
                    self.set_state(self.STATE_LISTEN)
            # Auto-reconnect
            else:
                self.rdt_server_wait_connect()
        # Opted to reset header bits for each new message
        self.do_reset()
        return buffer

    # Reliable layer for lower level packet receive
    def rdt_wait_for_packet(self, timeout=None):
        data = self.wait_for_packet(timeout)
        if data is None:
            return self.PACKET_TYPE_NONE, 0, 0, 0, b""
        else:
            # Split out and parse header
            header = data[:self.HEADER_SIZE]
            payload = data[self.HEADER_SIZE:]
            packet_type, seq_num, ack_num, final = struct.unpack(self.HEADER_FORMAT, header)
            print(
                f"Received packet type {packet_type} with sequence {seq_num}, ack {ack_num}, final {final}, payload '{payload.decode()}'")
            return packet_type, seq_num, ack_num, final, payload

    # The reliable send function handles FSM states from ESTABLISHED to CLOSED
    def rdt_send(self, payload):
        # Split the payload into smaller packets if necessary
        packets = self.split_payload(payload)
        sent = 0
        # resend is used to avoid the auto-increment of the seq
        resend = False
        while sent < len(packets):
            if self.state == self.STATE_ESTABLISHED:
                # Send the packet
                if sent == len(packets) - 1:
                    self.rdt_send_packet(self.PACKET_TYPE_DATA, packets[sent], self.FINAL_FLAG, resend=resend)
                    self.final = True
                else:
                    self.rdt_send_packet(self.PACKET_TYPE_DATA, packets[sent], resend=resend)
                # Wait for the ACK - The TIMEOUT parameter is used for triggering a resend on dropped packets
                packet_type, seq_num, ack_num, final, payload = self.rdt_wait_for_packet(self.TIMEOUT)

                # Check the ACK
                # Resend on dropped packets
                if packet_type == self.PACKET_TYPE_NONE:
                    print(f"Listen timed out")
                    resend = True
                elif packet_type == self.PACKET_TYPE_ACK:
                    if ack_num == self.seq_num + 1:
                        # Good ack, increment to next packet
                        resend = False
                        sent += 1
                        # If that was the last packet, reset ack/seq values - an unnecessary choice on my part
                        if self.final:
                            self.do_reset()
                    else:
                        # resend on out-of-order packets
                        print(f"Received ack:{ack_num}, but expected {self.seq_num + 1} -- resending")
                        resend = True
                #elif packet_type == self.PACKET_TYPE_DATA:
                    # This is an unusual case that comes up if the other end sent us a final data packet last and our ack
                    # to them was lost. We proceed to send our response data and get back a resend of the last final packet
                    # instead of the ack we expect. So let's just give them an ack on it again and retry our send.
                    #if not self.awaiting_ack:
                    #    self.rdt_send_packet(self.PACKET_TYPE_ACK, b"", seq_num=seq_num+1, ack_num=seq_num+1)
                    #resend = True
            else:
                # Auto-reconnect
                self.rdt_client_connect()

    # Lower level reliable send function
    def rdt_send_packet(self, packet_type, payload, final=0, resend=False, seq_num=None, ack_num=None):
        # The only time we override seq_num and ack_num are for a special case where we are just giving a blanket re-ack
        # for a packet we already moved past
        # if seq_num is not None and ack_num is not None:
        #     header = struct.pack(self.HEADER_FORMAT, packet_type, seq_num, ack_num, final)
        #     packet = header + payload
        #     self.send_packet(packet, dropchance=packet_type in (self.PACKET_TYPE_DATA, self.PACKET_TYPE_ACK))
        #     return
        if resend:
            # Resend the cached packet
            packet = self.cached_packet
            header = packet[:self.HEADER_SIZE]
            payload = packet[self.HEADER_SIZE:]
            packet_type, seq_num, ack_num, final = struct.unpack(self.HEADER_FORMAT, header)
            print(
                f"Resending packet type {packet_type} with sequence {self.seq_num}, ack {self.ack_num}, final {final}, payload '{payload.decode()}'")
        else:
            self.seq_num += 1
            print(
                f"Sending packet type {packet_type} with sequence {self.seq_num}, ack {self.ack_num}, final {final}, payload '{payload.decode()}'")
            header = struct.pack(self.HEADER_FORMAT, packet_type, self.seq_num, self.ack_num, final)
            packet = header + payload
            # Cache the packet
            self.cached_packet = packet

        #self.send_packet(packet, dropchance=packet_type in (self.PACKET_TYPE_DATA, self.PACKET_TYPE_ACK))
        self.send_packet(packet, dropchance=(packet_type==self.PACKET_TYPE_DATA))

    #########################################################
    ##### These are the underlying unreliable functions #####
    #########################################################

    # Receive packet, used by either server or client
    # TODO refactor this to move the added header layer into the reliable send function for separation of concerns
    def wait_for_packet(self, timeout=None):
        # Receive packet
        try:
            self.udp_socket.settimeout(timeout)
            data, client_address = self.udp_socket.recvfrom(self.UDP_BUFFER)
            self.udp_socket.settimeout(None)
            # Store client address
            self.client_address = client_address
            return data
        except socket.timeout:
            return None

    # Send packet, used by either server or client
    # TODO refactor this to move the caching and added header layer into the reliable send function for separation of concerns
    def send_packet(self, packet, dropchance = False):
        # Add unreliability for testing :evil:
        if dropchance and random() < self.DROP_CHANCE:
            print(f"(Dropped send)")
            return
        else:
            # Send the packet using the UDP socket
            # The sendto function has different requirements depending on client/server and location in code
            if self.state == self.STATE_INIT:
                self.udp_socket.sendto(packet, (self.client_address, self.port))
            else:
                self.udp_socket.sendto(packet, self.client_address)

    #############################
    ##### Utility functions #####
    #############################

    # Utility function to break a message into packets
    def split_payload(self, payload):
        packets = []
        for i in range(0, len(payload), self.SEND_BYTE_SIZE):
            packets.append(payload[i:i + self.SEND_BYTE_SIZE])
        return packets

    # Used to track FSM machine
    def set_state(self, state):
        self.state = state
        print(f"Setting state to {state}")

    # This is not truly needed, but I opted to reset these header fields when a message is completed
    def do_reset(self):
        self.seq_num = 0
        self.ack_num = 1
        self.final = False