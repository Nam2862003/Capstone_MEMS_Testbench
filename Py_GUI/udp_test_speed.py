import socket
import time

UDP_IP = "0.0.0.0"
UDP_PORT = 5005

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

# increase OS buffer
sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 4*1024*1024)

sock.bind((UDP_IP, UDP_PORT))

print("Receiving...")

total_bytes = 0
start_time = time.perf_counter()

try:
    while True:
        data, addr = sock.recvfrom(65535)

        total_bytes += len(data)

        current_time = time.perf_counter()
        elapsed = current_time - start_time

        if elapsed >= 1.0:
            mbps = (total_bytes * 8) / (elapsed * 1e6)
            print(f"Speed: {mbps:.2f} Mbps")

            total_bytes = 0
            start_time = current_time

except KeyboardInterrupt:
    print("\nStopped")
    sock.close()