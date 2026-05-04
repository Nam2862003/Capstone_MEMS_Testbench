import socket
import threading
import time
from collections import deque

import numpy as np


def detect_local_ip(default="127.0.0.1"):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # No packets are sent; this asks the OS which local interface it would use.
        sock.connect(("8.8.8.8", 80))
        return sock.getsockname()[0]
    except OSError:
        return default
    finally:
        sock.close()


class UDPReceiver:
    TEXT_PREFIXES = ("BOARD", "CAPS", "FW")

    def __init__(self, port=5005, buffer_size=2000, resolution_bits=16, host="0.0.0.0"):
        self.port = int(port)
        self.host = host
        self.display_host = detect_local_ip() if host == "0.0.0.0" else host
        self.sock = None

        self.buffer_size = buffer_size
        self.adc1 = np.zeros(self.buffer_size, dtype=np.uint16)
        self.adc2 = np.zeros(self.buffer_size, dtype=np.uint16)

        self.resolution_bits = 16
        self.mask = 0xFFFF
        self.set_resolution(resolution_bits)

        self.lock = threading.Lock()
        self.running = False
        self.thread = None
        self.connected = False
        self.packet_count = 0
        self.total_samples = 0
        self.total_bytes = 0
        self.last_packet_time = None
        self.last_error = ""
        self.error_count = 0
        self.speed_mbps = 0.0
        self.speed_window_bytes = 0
        self.speed_window_start = time.perf_counter()
        self.text_messages = deque(maxlen=16)

        self.start()

    def _store_text_message(self, data):
        try:
            text = data.decode("ascii").strip()
        except UnicodeDecodeError:
            return False

        if not text.startswith(self.TEXT_PREFIXES):
            return False

        with self.lock:
            self.text_messages.append(text)
        return True

    def clear_text_messages(self):
        with self.lock:
            self.text_messages.clear()

    def get_text_message(self):
        with self.lock:
            if self.text_messages:
                return self.text_messages.popleft()
        return None

    def set_resolution(self, resolution):
        if isinstance(resolution, str):
            resolution = resolution.strip().replace("-bit", "")
            resolution = int(resolution)

        if resolution not in (10, 12, 14, 16):
            raise ValueError("resolution must be 10, 12, 14, or 16")

        self.resolution_bits = resolution

        if resolution == 10:
            self.mask = 0x03FF
        elif resolution == 12:
            self.mask = 0x0FFF
        elif resolution == 14:
            self.mask = 0x3FFF
        else:
            self.mask = 0xFFFF

        print(f"[UDP] Resolution set to {self.resolution_bits}-bit (mask=0x{self.mask:04X})")

    def get_full_scale(self):
        return float((1 << self.resolution_bits) - 1)

    def open_socket(self):
        if self.sock is not None:
            return

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 4 * 1024 * 1024)
        self.sock.settimeout(0.5)
        self.sock.bind((self.host, self.port))
        self.connected = True
        self.last_error = ""
        print(f"[UDP] Listening on port {self.port}")

    def start(self):
        if self.thread is not None and self.thread.is_alive():
            return

        self.open_socket()
        self.running = True
        self.thread = threading.Thread(target=self.receive_loop, daemon=True)
        self.thread.start()

    def rebind(self, port, host=None):
        port = int(port)
        was_running = self.running
        self.stop()
        if host is not None:
            self.host = host
            self.display_host = detect_local_ip() if host == "0.0.0.0" else host
        self.port = port

        if was_running:
            self.start()

    def receive_loop(self):
        while self.running:
            try:
                if self.sock is None:
                    time.sleep(0.05)
                    continue

                data, _addr = self.sock.recvfrom(65535)
                if self._store_text_message(data):
                    continue

                self.last_packet_time = time.time()
                self.packet_count += 1
                self.total_bytes += len(data)
                self.speed_window_bytes += len(data)

                elapsed = time.perf_counter() - self.speed_window_start
                if elapsed >= 1.0:
                    self.speed_mbps = (self.speed_window_bytes * 8.0) / (elapsed * 1e6)
                    self.speed_window_bytes = 0
                    self.speed_window_start = time.perf_counter()

                samples = np.frombuffer(data, dtype=np.uint32)
                if len(samples) == 0:
                    continue

                adc1 = (samples & 0xFFFF).astype(np.uint16)
                adc2 = ((samples >> 16) & 0xFFFF).astype(np.uint16)

                adc1 = adc1 & self.mask
                adc2 = adc2 & self.mask

                n = len(adc1)
                self.total_samples += n

                with self.lock:
                    if n >= self.buffer_size:
                        self.adc1[:] = adc1[-self.buffer_size:]
                        self.adc2[:] = adc2[-self.buffer_size:]
                    else:
                        self.adc1 = np.roll(self.adc1, -n)
                        self.adc2 = np.roll(self.adc2, -n)
                        self.adc1[-n:] = adc1
                        self.adc2[-n:] = adc2

            except socket.timeout:
                continue
            except OSError:
                break
            except Exception as e:
                self.error_count += 1
                self.last_error = str(e)
                print("[UDP ERROR]", e)

    def get_data(self):
        with self.lock:
            return self.adc1.copy(), self.adc2.copy()

    def get_data_volts(self, vref=3.3):
        with self.lock:
            full_scale = self.get_full_scale()
            adc1_v = self.adc1.astype(np.float64) / full_scale * vref
            adc2_v = self.adc2.astype(np.float64) / full_scale * vref
            return adc1_v.copy(), adc2_v.copy()

    def set_buffer_size(self, new_size):
        new_size = int(new_size)
        if new_size <= 0:
            raise ValueError("buffer_size must be > 0")

        with self.lock:
            old_adc1 = self.adc1.copy()
            old_adc2 = self.adc2.copy()

            self.buffer_size = new_size
            self.adc1 = np.zeros(self.buffer_size, dtype=np.uint16)
            self.adc2 = np.zeros(self.buffer_size, dtype=np.uint16)

            keep = min(len(old_adc1), self.buffer_size)
            self.adc1[-keep:] = old_adc1[-keep:]
            self.adc2[-keep:] = old_adc2[-keep:]

        print(f"[UDP] Buffer size set to {self.buffer_size}")

    def get_status(self):
        return {
            "host": self.host,
            "display_host": self.display_host,
            "port": self.port,
            "connected": self.connected,
            "packet_count": self.packet_count,
            "total_samples": self.total_samples,
            "total_bytes": self.total_bytes,
            "last_packet_time": self.last_packet_time,
            "error_count": self.error_count,
            "last_error": self.last_error,
            "buffer_size": self.buffer_size,
            "speed_mbps": self.speed_mbps,
        }

    def reset_stats(self):
        with self.lock:
            self.adc1.fill(0)
            self.adc2.fill(0)
            self.text_messages.clear()

        self.packet_count = 0
        self.total_samples = 0
        self.total_bytes = 0
        self.last_packet_time = None
        self.error_count = 0
        self.last_error = ""
        self.speed_mbps = 0.0
        self.speed_window_bytes = 0
        self.speed_window_start = time.perf_counter()

    def stop(self):
        self.running = False

        try:
            if self.sock is not None:
                self.sock.close()
        except Exception:
            pass
        finally:
            self.sock = None
            self.connected = False

        if self.thread is not None and self.thread.is_alive():
            self.thread.join(timeout=1.0)

        print("[UDP] Receiver stopped")
