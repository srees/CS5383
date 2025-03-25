from more_reliable_UDP import RDTOverUDP

# Server details
SERVER_IP = "127.0.0.1"  # Change to the actual server IP if running remotely
SERVER_PORT = 12345

print("Welcome to the Magic 8-Ball! Type your question and press Enter.")
print("Type 'exit' to quit.\n")

# Setup reliable data transfer connection
rdtConnect = RDTOverUDP(SERVER_IP, SERVER_PORT)
rdtConnect.rdt_client_connect()

# Loop until exited
while True:
    # Get user input
    question = input("Ask the Magic 8-Ball a question: ").strip()

    # Close connection and quit
    if question.lower() == "exit":
        print("Goodbye!")
        rdtConnect.close()
        break

    # Send question to server
    rdtConnect.rdt_send(question.encode())

    # Receive response
    response = rdtConnect.rdt_receive()
    # Detect remote close
    if rdtConnect.state == rdtConnect.STATE_CLOSED:
        break
    print(f"Magic 8-Ball says: {response.decode()}\n")

