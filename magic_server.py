import socket
import random

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

# Create a UDP socket
udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

# Bind the socket to the address and port
udp_socket.bind((HOST, PORT))

print(f"Magic 8-Ball UDP server listening on {HOST}:{PORT}")

while True:
    # Receive data from client (buffer size = 1024 bytes)
    data, client_address = udp_socket.recvfrom(1024)

    question = data.decode().strip()

    # Pick a random Magic 8-Ball response
    response = random.choice(MAGIC_8_BALL_RESPONSES)

    # Log the interaction
    print(f"Received question: '{question}' from {client_address}")
    print(f"Magic 8-Ball response: '{response}'\n")

    # Send the response back to the client
    udp_socket.sendto(response.encode(), client_address)
