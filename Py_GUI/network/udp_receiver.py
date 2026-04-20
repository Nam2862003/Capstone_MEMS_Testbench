import socket
import threading
import numpy as np


class UDPReceiver:
    def __init__(self, port=5005, buffer_size=2000, resolution_bits=16):
        # ---------------- SOCKET ----------------
        self.port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 4 * 1024 * 1024)
        self.sock.bind(("0.0.0.0", self.port))

        print(f"[UDP] Listening on port {self.port}")

        # ---------------- DATA BUFFER ----------------
        self.buffer_size = buffer_size
        self.adc1 = np.zeros(self.buffer_size, dtype=np.uint16)
        self.adc2 = np.zeros(self.buffer_size, dtype=np.uint16)

        # ---------------- RESOLUTION ----------------
        self.resolution_bits = 16
        self.mask = 0xFFFF
        self.set_resolution(resolution_bits)

        # ---------------- THREAD CONTROL ----------------
        self.running = True
        self.lock = threading.Lock()

        # ---------------- START THREAD ----------------
        self.thread = threading.Thread(target=self.receive_loop, daemon=True)
        self.thread.start()

    # =========================
    # RESOLUTION CONTROL
    # =========================
    def set_resolution(self, resolution):
        """
        Accepts:
            10, 12, 14, 16
            or "10-bit", "12-bit", "14-bit", "16-bit"
        """
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

    # =========================
    # RECEIVE LOOP
    # =========================
    def receive_loop(self):
        while self.running:
            try:
                data, addr = self.sock.recvfrom(65535)

                # Convert raw bytes → uint32 array
                samples = np.frombuffer(data, dtype=np.uint32)

                if len(samples) == 0:
                    continue

                # Extract two 16-bit lanes
                adc1 = (samples & 0xFFFF).astype(np.uint16)
                adc2 = ((samples >> 16) & 0xFFFF).astype(np.uint16)

                # Apply resolution mask
                adc1 = adc1 & self.mask
                adc2 = adc2 & self.mask

                n = len(adc1)

                with self.lock:
                    # If received packet is larger than display buffer, keep newest samples only
                    if n >= self.buffer_size:
                        self.adc1[:] = adc1[-self.buffer_size:]
                        self.adc2[:] = adc2[-self.buffer_size:]
                    else:
                        # Roll buffer left
                        self.adc1 = np.roll(self.adc1, -n)
                        self.adc2 = np.roll(self.adc2, -n)

                        # Insert new data
                        self.adc1[-n:] = adc1
                        self.adc2[-n:] = adc2

            except OSError:
                # Happens normally when socket is closed during stop()
                break
            except Exception as e:
                print("[UDP ERROR]", e)

    # =========================
    # GET DATA (RAW COUNTS)
    # =========================
    def get_data(self):
        with self.lock:
            return self.adc1.copy(), self.adc2.copy()

    # =========================
    # GET DATA IN VOLTS
    # =========================
    def get_data_volts(self, vref=3.3):
        with self.lock:
            full_scale = self.get_full_scale()
            adc1_v = self.adc1.astype(np.float64) / full_scale * vref
            adc2_v = self.adc2.astype(np.float64) / full_scale * vref
            return adc1_v.copy(), adc2_v.copy()

    # =========================
    # OPTIONAL: CHANGE DISPLAY BUFFER SIZE
    # =========================
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

    # =========================
    # STOP RECEIVER
    # =========================
    def stop(self):
        self.running = False

        try:
            self.sock.close()
        except Exception:
            pass

        print("[UDP] Receiver stopped")