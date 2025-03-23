from more_reliable_UDP import RDTOverUDP

# Server details
SERVER_IP = "127.0.0.1"  # Change to the actual server IP if running remotely
SERVER_PORT = 12345

print("Welcome to the Magic 8-Ball! Type your question and press Enter.")
print("Type 'exit' to quit.\n")

while True:
    # Get user input
    question = input("Ask the Magic 8-Ball a question: ").strip()

    if question.lower() == "exit":
        print("Goodbye!")
        break

    # Setup reliable data transfer connection
    rdtConnect = RDTOverUDP(SERVER_IP, SERVER_PORT)

    # Send question to server
    rdtConnect.rdt_client_connect()
    rdtConnect.rdt_send(question.encode())

    # Receive response
    response = rdtConnect.rdt_receive()
    print(f"Magic 8-Ball says: {response.decode()}\n")

    # Close the socket when done (though we loopin'!)
    rdtConnect.close()
