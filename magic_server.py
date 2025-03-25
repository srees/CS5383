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

print(f"Magic 8-Ball UDP server listening on {HOST}:{PORT}")
rdtConnect.rdt_server_wait_connect()
while True:
    # As we are looping, if the client has called close we need to reopen for connections again
    if rdtConnect.state == rdtConnect.STATE_CLOSED:
        break
    # Receive data from client (buffer size = 1024 bytes)
    data = rdtConnect.rdt_receive()
    if data:
        question = data.decode().strip()

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