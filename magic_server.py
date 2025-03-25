import random
from more_reliable_UDP import RDTOverUDP

# Define server address and port
HOST = "0.0.0.0"  # Listen on all available network interfaces
PORT = 12345  # Choose any available port

# List of Magic 8-Ball responses
MAGIC_8_BALL_RESPONSES = [
    "Yes, definitely.",
    "It is certain.",
    "Without a doubt.",
    "Yes.",
    "Most likely.",
    "Outlook good.",
    "Signs point to yes.",
    "Reply hazy, try again.",
    "Ask again later.",
    "Better not tell you now.",
    "Cannot predict now.",
    "Concentrate and ask again.",
    "Don't count on it.",
    "My reply is no.",
    "My sources say no.",
    "Outlook not so good.",
    "Very doubtful.",
    "Absolutely!",
    "No way!",
    "Maybe, maybe not."
]

# Setup reliable data transfer connection
rdtConnect = RDTOverUDP(HOST, PORT)
rdtConnect.rdt_server_wait_connect()
print(f"Magic 8-Ball UDP server listening on {HOST}:{PORT}")

#Listen until exited
while True:
    # I designed this so that if the client exits cleanly, the server will
    # detect and reinitialize for another connection
    if rdtConnect.state == rdtConnect.STATE_CLOSED:
        rdtConnect.rdt_server_wait_connect()
    # Receive data from client (buffer size = 1024 bytes)
    data = rdtConnect.rdt_receive()
    if data:
        question = data.decode().strip()
        # The client can also request to kill the server
        # which ends it for both of them.
        if question.lower() == "kill":
            print("Server shutting down...")
            rdtConnect.close()
            break

        # Pick a random Magic 8-Ball response
        response = random.choice(MAGIC_8_BALL_RESPONSES)

        # Log the interaction
        print(f"Received question: '{question}' from {rdtConnect.client_address}")
        print(f"Magic 8-Ball response: '{response}'\n")

        # Send our response over our reliable data transfer object
        packet = rdtConnect.rdt_send(response.encode())