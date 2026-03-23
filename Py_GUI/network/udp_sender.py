# network/udp_sender.py

import socket


class UDPSender:

    def __init__(self, ip="192.168.0.123", port=5006):

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
    def start_aq(self):
        self.send("START")

    def stop_aq(self):
        self.send("STOP")

    def set_buffer(self, size):
        self.send(f"BUF,{size}")
    def set_sampling_rate(self, rate):
        self.send(f"SAMP,{rate}")