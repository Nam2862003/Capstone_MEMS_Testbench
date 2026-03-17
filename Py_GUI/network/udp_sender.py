# network/udp_sender.py

import socket


class UDPSender:

    def __init__(self, ip="192.168.1.141", port=5006):

        self.ip = ip
        self.port = port

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    def send(self, cmd):

        try:
            self.sock.sendto(cmd.encode(), (self.ip, self.port))
            print("Sent:", cmd)

        except Exception as e:
            print("UDP error:", e)

    # convenience functions
    def start(self):
        self.send("START")

    def stop(self):
        self.send("STOP")

    def set_buffer(self, size):
        self.send(f"BUF,{size}")