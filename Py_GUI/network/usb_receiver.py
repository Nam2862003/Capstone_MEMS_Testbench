import sys
import threading
import time

import numpy as np
import serial
from serial.tools import list_ports


class USBReceiver:
    """Receive packed ADC samples from the STM32 USB CDC binary stream.

    Frame format from firmware:
      bytes 0..3:  b"ADCB"
      bytes 4..5:  uint16 little-endian sample count
      bytes 6..7:  uint16 little-endian flags/reserved
      payload:     sample_count x uint32 little-endian packed samples

    Packed sample format:
      ADC1 = word & 0xFFFF
      ADC2 = (word >> 16) & 0xFFFF
    """

    MAGIC = b"ADCB"
    HEADER_SIZE = 8

    def __init__(self, port="COM9", baudrate=115200, buffer_size=2000, resolution_bits=12):
        self.port = port
        self.baudrate = int(baudrate)
        self.ser = None

        self.buffer_size = int(buffer_size)
        self.adc1 = np.zeros(self.buffer_size, dtype=np.uint16)
        self.adc2 = np.zeros(self.buffer_size, dtype=np.uint16)

        self.resolution_bits = 12
        self.mask = 0x0FFF
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
        self._rx = bytearray()

    @staticmethod
    def available_ports():
        return [port.device for port in list_ports.comports()]

    def set_resolution(self, resolution):
        if isinstance(resolution, str):
            resolution = resolution.strip().replace("-bit", "")
            resolution = int(resolution)

        if resolution not in (10, 12, 14, 16):
            raise ValueError("resolution must be 10, 12, 14, or 16")

        self.resolution_bits = resolution
        self.mask = (1 << resolution) - 1
        print(f"[USB] Resolution set to {self.resolution_bits}-bit (mask=0x{self.mask:04X})")

    def get_full_scale(self):
        return float((1 << self.resolution_bits) - 1)

    def open(self):
        if self.ser is not None and self.ser.is_open:
            return

        self.ser = serial.Serial(self.port, self.baudrate, timeout=0.05)
        self.ser.reset_input_buffer()
        self.connected = True
        self.last_error = ""
        print(f"[USB] Listening on {self.port}")

    def start(self):
        if self.thread is not None and self.thread.is_alive():
            return

        self.open()
        self.running = True
        self.thread = threading.Thread(target=self.receive_loop, daemon=True)
        self.thread.start()

    def rebind(self, port, baudrate=None):
        was_running = self.running
        self.stop()
        self.port = port
        if baudrate is not None:
            self.baudrate = int(baudrate)
        self._rx.clear()
        if was_running:
            self.start()

    def receive_loop(self):
        while self.running:
            try:
                if self.ser is None or not self.ser.is_open:
                    time.sleep(0.05)
                    continue

                chunk = self.ser.read(65536)
                if not chunk:
                    continue

                self._rx.extend(chunk)
                self.total_bytes += len(chunk)
                self.speed_window_bytes += len(chunk)
                self._update_speed()
                self._parse_frames()

            except serial.SerialException as e:
                self.error_count += 1
                self.last_error = str(e)
                self.connected = False
                print("[USB ERROR]", e)
                break
            except Exception as e:
                self.error_count += 1
                self.last_error = str(e)
                print("[USB ERROR]", e)

    def _update_speed(self):
        elapsed = time.perf_counter() - self.speed_window_start
        if elapsed >= 1.0:
            self.speed_mbps = (self.speed_window_bytes * 8.0) / (elapsed * 1e6)
            self.speed_window_bytes = 0
            self.speed_window_start = time.perf_counter()

    def _parse_frames(self):
        while True:
            magic_index = self._rx.find(self.MAGIC)
            if magic_index < 0:
                keep = len(self.MAGIC) - 1
                if len(self._rx) > keep:
                    del self._rx[:-keep]
                return

            if magic_index > 0:
                del self._rx[:magic_index]

            if len(self._rx) < self.HEADER_SIZE:
                return

            sample_count = int.from_bytes(self._rx[4:6], byteorder="little", signed=False)
            payload_size = sample_count * 4
            frame_size = self.HEADER_SIZE + payload_size

            if sample_count <= 0:
                del self._rx[:len(self.MAGIC)]
                continue

            if len(self._rx) < frame_size:
                return

            payload = bytes(self._rx[self.HEADER_SIZE:frame_size])
            del self._rx[:frame_size]
            self._store_payload(payload)

    def _store_payload(self, payload):
        samples = np.frombuffer(payload, dtype="<u4")
        if len(samples) == 0:
            return

        adc1 = (samples & 0xFFFF).astype(np.uint16) & self.mask
        adc2 = ((samples >> 16) & 0xFFFF).astype(np.uint16) & self.mask
        n = len(samples)

        self.packet_count += 1
        self.total_samples += n
        self.last_packet_time = time.time()

        with self.lock:
            if n >= self.buffer_size:
                self.adc1[:] = adc1[-self.buffer_size:]
                self.adc2[:] = adc2[-self.buffer_size:]
            else:
                self.adc1 = np.roll(self.adc1, -n)
                self.adc2 = np.roll(self.adc2, -n)
                self.adc1[-n:] = adc1
                self.adc2[-n:] = adc2

    def get_data(self):
        with self.lock:
            return self.adc1.copy(), self.adc2.copy()

    def get_data_volts(self, vref=3.3):
        with self.lock:
            full_scale = self.get_full_scale()
            adc1_v = self.adc1.astype(np.float64) / full_scale * vref
            adc2_v = self.adc2.astype(np.float64) / full_scale * vref
            return adc1_v.copy(), adc2_v.copy()

    def get_data_analog(self, vref=3.3):
        return self.get_data_volts(vref=vref)

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

        print(f"[USB] Buffer size set to {self.buffer_size}")

    def get_status(self):
        return {
            "port": self.port,
            "baudrate": self.baudrate,
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

    def stop(self):
        self.running = False

        try:
            if self.ser is not None:
                self.ser.close()
        except Exception:
            pass
        finally:
            self.ser = None
            self.connected = False

        if self.thread is not None and self.thread.is_alive():
            self.thread.join(timeout=1.0)

        print("[USB] Receiver stopped")

def _print_test_loop(port="COM9", baudrate=115200, resolution_bits=12, vref=3.3):
    rx = USBReceiver(port=port, baudrate=baudrate, buffer_size=2000, resolution_bits=resolution_bits)
    print(f"[USB TEST] Available ports: {USBReceiver.available_ports()}")
    print(f"[USB TEST] Opening {port} at {baudrate} baud")
    rx.start()

    try:
        while True:
            raw1, raw2 = rx.get_data()
            adc1_v, adc2_v = rx.get_data_volts(vref=vref)
            status = rx.get_status()

            print(
                f"ADC1={int(raw1[-1]):4d} ({adc1_v[-1]:.4f} V) | "
                f"ADC2={int(raw2[-1]):4d} ({adc2_v[-1]:.4f} V) | "
                f"frames={status['packet_count']} samples={status['total_samples']} "
                f"speed={status['speed_mbps']:.3f} Mbps"
            )
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\n[USB TEST] Stopping")
    finally:
        rx.stop()


if __name__ == "__main__":
    port = sys.argv[1] if len(sys.argv) > 1 else "COM9"
    baudrate = int(sys.argv[2]) if len(sys.argv) > 2 else 115200
    _print_test_loop(port=port, baudrate=baudrate)


