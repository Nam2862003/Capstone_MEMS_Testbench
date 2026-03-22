from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QTabWidget,
    QLabel, QPushButton, QComboBox,
    QGroupBox, QGridLayout
)

import pyqtgraph as pg


class BaseDAQPage(QWidget):

    def __init__(self, receiver, sender):

        super().__init__()

        self.receiver = receiver
        self.sender = sender

        layout = QVBoxLayout()

        self.tabs = QTabWidget()

        self.setup = QWidget()
        self.acquisition = QWidget()

        self.tabs.addTab(self.setup, "Setup")
        self.tabs.addTab(self.acquisition, "Acquisition")

        layout.addWidget(self.tabs)
        self.setLayout(layout)

        self.build_setup_tab()
        self.build_acquisition_tab()

    # =========================
    # SETUP TAB
    # =========================

    def build_setup_tab(self):

        setup_layout = QVBoxLayout()

        settings_box = QGroupBox("Acquisition Settings")
        grid = QGridLayout()

        self.rate = QComboBox()
        self.rate.addItems(["100 kSPS", "500 kSPS", "1 MSPS", "2 MSPS"])

        self.buffer = QComboBox()
        self.buffer.addItems(["512", "1024", "2048", "4096", "8192", "16384"])

        self.mode = QComboBox()
        self.mode.addItems(["Continuous", "Triggered"])

        self.start = QPushButton("Start")
        self.stop = QPushButton("Stop")

        grid.addWidget(QLabel("Sampling Rate"), 0, 0)
        grid.addWidget(self.rate, 0, 1)

        grid.addWidget(QLabel("Buffer Size"), 1, 0)
        grid.addWidget(self.buffer, 1, 1)

        grid.addWidget(QLabel("Mode"), 2, 0)
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

    # =========================
    # ACQUISITION TAB
    # =========================

    def build_acquisition_tab(self):

        layout = QVBoxLayout()

        self.plot_widget = pg.PlotWidget()

        self.curve1 = self.plot_widget.plot(pen='y', name="ADC1")
        self.curve2 = self.plot_widget.plot(pen='r', name="ADC2")

        layout.addWidget(self.plot_widget)

        self.acquisition.setLayout(layout)

        # update timer
        self.timer = pg.QtCore.QTimer()
        self.timer.timeout.connect(self.update_plot)
        self.timer.start(30)

    # =========================
    # UDP COMMANDS
    # =========================

    def set_buffer(self, value):
        self.sender.set_buffer(value)

    def start_acquisition(self):
        self.sender.start()

    def stop_acquisition(self):
        self.sender.stop()

    # =========================
    # PLOTTING
    # =========================

def update_plot(self):

    adc1, adc2 = self.receiver.get_data()

    # Optional: downsample for speed
    adc1 = adc1[::10]
    adc2 = adc2[::10]

    self.curve1.setData(adc1)
    self.curve2.setData(adc2)