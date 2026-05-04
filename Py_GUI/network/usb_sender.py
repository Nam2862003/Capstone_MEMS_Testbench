import time

import serial

from network.command_sender import CommandSenderMixin


class USBSender(CommandSenderMixin):
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
        self.actuator_mode = "STM32"
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

        self.ser = serial.Serial(self.port, self.baudrate, timeout=0.05, write_timeout=1.0)
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
                    ser.flush()
            else:
                ser.write(payload)
                ser.flush()
            self.last_send_time = time.time()
            self.sent_count += 1
            self.connected = True
            print("USB Sent:", cmd)
            return True
        except Exception as e:
            self.error_count += 1
            self.last_error = str(e)
            self.connected = False
            print(f"USB error sending {cmd!r}:", e)
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

    def reset_stats(self):
        self.last_send_time = None
        self.sent_count = 0
        self.error_count = 0
        self.last_error = ""
