import socket
import time

from network.command_sender import CommandSenderMixin


class UDPSender(CommandSenderMixin):
    def __init__(self, ip="192.168.0.123", port=5006):
        self.ip = ip
        self.port = int(port)
        self.sock = None
        self.connected = False
        self.last_send_time = None
        self.sent_count = 0
        self.error_count = 0
        self.last_error = ""
        self.board_mode = "PE"
        self.actuator_mode = "STM32"
        self.pe_gain_index = 0

    def open(self):
        if self.sock is not None:
            return

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.connected = True
        self.last_error = ""
        print(f"[UDP] Sender ready for {self.ip}:{self.port}")

    def close(self):
        if self.sock is not None:
            try:
                self.sock.close()
            except OSError:
                pass

        self.sock = None
        self.connected = False
        print("[UDP] Sender stopped")

    def configure(self, ip=None, port=None):
        if ip is not None:
            self.ip = ip
        if port is not None:
            self.port = int(port)

        self.close()
        self.open()

    def send(self, cmd):
        if not self.connected or self.sock is None:
            self.open()

        try:
            self.sock.sendto(cmd.encode(), (self.ip, self.port))
            self.last_send_time = time.time()
            self.sent_count += 1
            print("UDP Sent:", cmd)
            return True
        except Exception as e:
            self.error_count += 1
            self.last_error = str(e)
            self.connected = False
            print("UDP error:", e)
            return False

    def get_status(self):
        return {
            "ip": self.ip,
            "port": self.port,
            "connected": self.connected,
            "last_send_time": self.last_send_time,
            "sent_count": self.sent_count,
            "error_count": self.error_count,
            "last_error": self.last_error,
        }

    def reset_stats(self):
        self.last_send_time = None
        self.sent_count = 0
        self.error_count = 0
        self.last_error = ""
