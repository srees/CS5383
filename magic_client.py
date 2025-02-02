import socket

# Server details
SERVER_IP = "127.0.0.1"  # Change to the actual server IP if running remotely
SERVER_PORT = 12345

# Create UDP socket
udp_client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

print("Welcome to the Magic 8-Ball! Type your question and press Enter.")
print("Type 'exit' to quit.\n")

while True:
    # Get user input
    question = input("Ask the Magic 8-Ball a question: ").strip()

    if question.lower() == "exit":
        print("Goodbye!")
        break

    # Send question to server
    udp_client.sendto(question.encode(), (SERVER_IP, SERVER_PORT))

    # Receive response
    response, server_address = udp_client.recvfrom(1024)
    print(f"Magic 8-Ball says: {response.decode()}\n")

# Close the socket when done
udp_client.close()
