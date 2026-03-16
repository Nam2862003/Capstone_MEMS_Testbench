from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QTabWidget,
    QLabel, QPushButton, QComboBox,
    QGroupBox, QGridLayout
)

import socket

class BaseDAQPage(QWidget):

    def __init__(self):

        super().__init__()

        # ---------------- UDP ----------------
        self.STM32_IP = "192.168.1.141"
        self.STM32_PORT = 5006
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        layout = QVBoxLayout()

        self.tabs = QTabWidget()

        self.setup = QWidget()
        self.acquisition = QWidget()

        self.tabs.addTab(self.setup, "Setup")
        self.tabs.addTab(self.acquisition, "Acquisition")

        layout.addWidget(self.tabs)

        self.setLayout(layout)

        self.build_setup_tab()

    # ---------------- SETUP TAB ----------------

    def build_setup_tab(self):

        setup_layout = QVBoxLayout()

        settings_box = QGroupBox("Acquisition Settings")

        grid = QGridLayout()

        # Sampling rate
        rate_label = QLabel("Sampling Rate")

        self.rate = QComboBox()
        self.rate.addItems([
            "100 kSPS",
            "500 kSPS",
            "1 MSPS",
            "2 MSPS"
        ])

        # Buffer
        buffer_label = QLabel("Buffer Size")

        self.buffer = QComboBox()
        self.buffer.addItems([
            "512",
            "1024",
            "2048",
            "4096",
            "8192",
            "16384"
        ])

        # Mode
        mode_label = QLabel("Mode")

        self.mode = QComboBox()
        self.mode.addItems([
            "Continuous",
            "Triggered"
        ])

        # Buttons
        self.start = QPushButton("Start")
        self.stop = QPushButton("Stop")

        grid.addWidget(rate_label, 0, 0)
        grid.addWidget(self.rate, 0, 1)

        grid.addWidget(buffer_label, 1, 0)
        grid.addWidget(self.buffer, 1, 1)

        grid.addWidget(mode_label, 2, 0)
        grid.addWidget(self.mode, 2, 1)

        grid.addWidget(self.start, 3, 0)
        grid.addWidget(self.stop, 3, 1)

        settings_box.setLayout(grid)

        setup_layout.addWidget(settings_box)

        self.setup.setLayout(setup_layout)

        # connections
        self.buffer.currentTextChanged.connect(self.set_buffer)
        self.start.clicked.connect(self.start_acquisition)
        self.stop.clicked.connect(self.stop_acquisition)

    # ---------------- UDP FUNCTIONS ----------------

    def send_cmd(self, cmd):

        try:
            self.sock.sendto(cmd.encode(), (self.STM32_IP, self.STM32_PORT))
            print("Sent:", cmd)

        except Exception as e:
            print("UDP error:", e)

    def set_buffer(self, value):

        self.send_cmd(f"BUF,{value}")

    def start_acquisition(self):

        self.send_cmd("START")

    def stop_acquisition(self):

        self.send_cmd("STOP")