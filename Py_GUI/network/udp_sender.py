import socket
import time


class UDPSender:
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
        self.actuator_mode = "DDS"
        self.pe_gain_index = 0
        self.open()

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
            print("Sent:", cmd)
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

    def start_aq(self):
        self.send("START ADC")

    def stop_aq(self):
        self.send("STOP ADC")

    def set_buffer(self, size):
        self.send(f"BUF,{size}")

    def set_sampling_rate(self, rate):
        self.send(f"ADC SAMP,{rate}")

    def set_adc_resolution(self, resolution):
        if resolution == "10-bit":
            self.send("ADC RES,10")
        elif resolution == "12-bit":
            self.send("ADC RES,12")
        elif resolution == "14-bit":
            self.send("ADC RES,14")
        elif resolution == "16-bit":
            self.send("ADC RES,16")

    def start_gen(self):
        self.send("DAC START")

    def stop_gen(self):
        self.send("DAC STOP")

    def set_dac_freq(self, freq):
        self.send(f"DAC FREQ,{freq}")

    def set_board_mode(self, mode, send_now=True):
        normalized = str(mode).strip().upper()
        if normalized not in {"PE", "PR"}:
            raise ValueError(f"Unsupported board mode: {mode}")

        self.board_mode = normalized

        if send_now:
            self.send(f"MODE,{normalized}")

    def sync_board_mode(self):
        self.send(f"MODE,{self.board_mode}")

    def set_actuator_mode(self, mode, send_now=True):
        normalized = str(mode).strip().upper()
        if normalized not in {"DDS", "FG", "STM32"}:
            raise ValueError(f"Unsupported actuator mode: {mode}")

        self.actuator_mode = normalized

        if send_now:
            self.send(f"ACTUATOR,{normalized}")

    def sync_actuator_mode(self):
        self.send(f"ACTUATOR,{self.actuator_mode}")

    def set_pe_gain(self, gain_index):
        index = int(gain_index)
        if index < 0 or index > 3:
            raise ValueError(f"Unsupported PE gain index: {gain_index}")

        self.pe_gain_index = index
        self.send(f"PE GAIN,{index}")

    def sync_pe_gain(self):
        self.send(f"PE GAIN,{self.pe_gain_index}")
