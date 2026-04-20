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
    # ADC control
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
    # DAC control
    def start_gen(self):
        self.send("DAC START")
    def stop_gen(self):
        self.send("DAC STOP")
    def set_dac_freq(self, freq):
        self.send(f"DAC FREQ,{freq}")