import socket
import struct
import matplotlib.pyplot as plt
from collections import deque

UDP_IP = "0.0.0.0"
UDP_PORT = 5005

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind((UDP_IP, UDP_PORT))

print("Listening for UDP packets on port", UDP_PORT)

mems_buffer = deque(maxlen=2000)
ref_buffer = deque(maxlen=2000)

plt.ion()
fig, ax = plt.subplots()

while True:

    data, addr = sock.recvfrom(2048)

    num_samples = len(data) // 4

    for i in range(num_samples):

        sample = struct.unpack_from("<I", data, i*4)[0]

        mems = sample & 0xFFFF
        ref = sample >> 16

        mems_buffer.append(mems)
        ref_buffer.append(ref)

    print("Received", num_samples, "samples")

    ax.clear()
    ax.plot(mems_buffer, label="MEMS")
    ax.plot(ref_buffer, label="REF")
    ax.legend()
    plt.pause(0.001)