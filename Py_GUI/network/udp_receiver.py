import socket
import threading
import numpy as np


class UDPReceiver:

    def __init__(self, port=5005, buffer_size=2000):

        # ---------------- SOCKET ----------------
        self.port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 4 * 1024 * 1024)
        self.sock.bind(("0.0.0.0", self.port))

        print(f"[UDP] Listening on port {self.port}")

        # ---------------- DATA BUFFER ----------------
        self.buffer_size = buffer_size

        self.adc1 = np.zeros(self.buffer_size)
        self.adc2 = np.zeros(self.buffer_size)

        # ---------------- THREAD CONTROL ----------------
        self.running = True
        self.lock = threading.Lock()

        # ---------------- START THREAD ----------------
        self.thread = threading.Thread(target=self.receive_loop, daemon=True)
        self.thread.start()

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

                # Extract ADC values
                adc1 = samples & 0xFFFF
                adc2 = (samples >> 16) & 0xFFFF

                n = len(adc1)

                # Thread-safe update
                with self.lock:

                    # Roll buffer left
                    self.adc1 = np.roll(self.adc1, -n)
                    self.adc2 = np.roll(self.adc2, -n)

                    # Insert new data
                    self.adc1[-n:] = adc1
                    self.adc2[-n:] = adc2

            except Exception as e:
                print("[UDP ERROR]", e)

    # =========================
    # GET DATA (SAFE ACCESS)
    # =========================

    def get_data(self):

        with self.lock:
            return self.adc1.copy(), self.adc2.copy()

    # =========================
    # STOP RECEIVER
    # =========================

    def stop(self):

        self.running = False

        try:
            self.sock.close()
        except:
            pass

        print("[UDP] Receiver stopped")