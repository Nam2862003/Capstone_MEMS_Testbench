import socket
import time

UDP_IP = "0.0.0.0"
UDP_PORT = 5005

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind((UDP_IP, UDP_PORT))

print("Receiving...")

total_bytes = 0
start_time = time.time()

try:
    while True:
        data, addr = sock.recvfrom(2048)

        packet_size = len(data)
        total_bytes += packet_size

        # print(f"Packet: {packet_size}")

        # calculate every 1 second
        current_time = time.time()
        elapsed = current_time - start_time

        if elapsed >= 1.0:
            mbps = (total_bytes * 8) / (elapsed * 1e6)
            print(f"Speed: {mbps:.2f} Mbps\n")

            total_bytes = 0
            start_time = current_time

except KeyboardInterrupt:
    print("\nStopped by user")
    sock.close()