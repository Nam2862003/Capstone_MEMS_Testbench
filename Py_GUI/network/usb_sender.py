import time

import serial


class USBSender:
    def __init__(self, port="COM9", baudrate=115200, receiver=None):
        self.port = port
        self.baudrate = int(baudrate)
        self.receiver = receiver
        self.ser = None
        self.connected = False
        self.last_send_time = None
        self.sent_count = 0
        self.error_count = 0
        self.last_error = ""
        self.board_mode = "PE"
        self.actuator_mode = "DDS"
        self.pe_gain_index = 0

    def attach_receiver(self, receiver):
        self.receiver = receiver

    def configure(self, port=None, baudrate=None):
        if port is not None:
            self.port = str(port)
        if baudrate is not None:
            self.baudrate = int(baudrate)

        if self.receiver is not None and (
            self.receiver.port != self.port or int(self.receiver.baudrate) != int(self.baudrate)
        ):
            self.receiver.rebind(self.port, baudrate=self.baudrate)

    def _shared_serial(self):
        if self.receiver is None:
            return None
        ser = getattr(self.receiver, "ser", None)
        if ser is not None and ser.is_open:
            return ser
        return None

    def open(self):
        shared = self._shared_serial()
        if shared is not None:
            self.connected = True
            self.last_error = ""
            return

        if self.receiver is not None:
            self.receiver.start()
            self.connected = True
            self.last_error = ""
            return

        if self.ser is not None and self.ser.is_open:
            return

        self.ser = serial.Serial(self.port, self.baudrate, timeout=0.05, write_timeout=0.05)
        self.connected = True
        self.last_error = ""
        print(f"[USB] Sender ready for {self.port}")

    def close(self):
        was_active = self.connected or (self.ser is not None and self.ser.is_open)
        if self.ser is not None:
            try:
                self.ser.close()
            except OSError:
                pass
        self.ser = None
        self.connected = False
        if was_active:
            print("[USB] Sender stopped")

    def send(self, cmd):
        try:
            ser = self._shared_serial()
            if ser is None:
                self.open()
                ser = self._shared_serial() or self.ser

            if ser is None or not ser.is_open:
                raise serial.SerialException("USB serial port is not open")

            payload = (cmd.strip() + "\n").encode("ascii")
            io_lock = getattr(self.receiver, "io_lock", None)
            if io_lock is not None:
                with io_lock:
                    ser.write(payload)
            else:
                ser.write(payload)
            self.last_send_time = time.time()
            self.sent_count += 1
            self.connected = True
            print("USB Sent:", cmd)
            return True
        except Exception as e:
            self.error_count += 1
            self.last_error = str(e)
            self.connected = False
            print("USB error:", e)
            return False

    def get_status(self):
        shared = self._shared_serial()
        connected = self.connected or shared is not None or (self.ser is not None and self.ser.is_open)
        return {
            "port": self.port,
            "baudrate": self.baudrate,
            "connected": connected,
            "last_send_time": self.last_send_time,
            "sent_count": self.sent_count,
            "error_count": self.error_count,
            "last_error": self.last_error,
        }

    def start_aq(self):
        return self.send("START ADC")

    def stop_aq(self):
        return self.send("STOP ADC")

    def set_buffer(self, size):
        return self.send(f"BUF,{size}")

    def set_sampling_rate(self, rate):
        return self.send(f"ADC SAMP,{rate}")

    def set_adc_resolution(self, resolution):
        if isinstance(resolution, str):
            resolution = resolution.strip().replace("-bit", "")
        return self.send(f"ADC RES,{resolution}")

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
