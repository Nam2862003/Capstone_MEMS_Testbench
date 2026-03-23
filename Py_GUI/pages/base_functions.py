from PyQt6.QtWidgets import (
    QFormLayout, QLineEdit, QWidget, QVBoxLayout, QTabWidget,
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
        self.sweep = QWidget()

        self.tabs.addTab(self.setup, "Setup")
        self.tabs.addTab(self.sweep, "Sweep Plot")

        layout.addWidget(self.tabs)
        self.setLayout(layout)

        self.build_setup_tab()
        self.build_sweep_tab()

    # =========================
    # SETUP TAB
    # =========================

    def build_setup_tab(self):

        layout = QVBoxLayout()

        # =========================
        # ADC SETTINGS
        # =========================
        # Sampling rate
        adc_group = QGroupBox("Acquisition (ADC)")
        adc_layout = QFormLayout()
        self.sampling_rate_input = QLineEdit("50000")
        adc_layout.addRow("Sampling Rate (Hz):", self.sampling_rate_input)

        # Buffer size
        self.buffer = QComboBox()
        self.buffer.addItems(["512", "1024", "2048", "4096", "8192", "16384"])
        adc_layout.addRow("Buffer Size:", self.buffer)
        adc_group.setLayout(adc_layout)
        # Control buttons
        button_layout = QGridLayout()
        self.start=QPushButton("Start Acquisition")
        self.stop=QPushButton("Stop Acquisition")
        button_layout.addWidget(self.start, 0, 0)
        button_layout.addWidget(self.stop, 0, 1)
        adc_layout.addRow(button_layout)

        # =========================
        # DAC SETTINGS
        # =========================
        dac_group = QGroupBox("Signal Generation (DAC)")
        dac_layout = QFormLayout()

        self.dac_freq_input = QLineEdit("1000")  # 1 kHz default

        self.enable_dac_btn = QPushButton("Enable DAC")
        self.disable_dac_btn = QPushButton("Disable DAC")

        dac_layout.addRow("Frequency (Hz):", self.dac_freq_input)
        dac_layout.addRow(self.enable_dac_btn, self.disable_dac_btn)

        dac_group.setLayout(dac_layout)

        # =========================
        # ADD TO MAIN LAYOUT
        # =========================
        layout.addWidget(adc_group)
        layout.addWidget(dac_group)
        self.setup.setLayout(layout)

        # connections
        self.buffer.currentTextChanged.connect(self.set_buffer)
        self.start.clicked.connect(self.start_acquisition)
        self.stop.clicked.connect(self.stop_acquisition)
        self.sampling_rate_input.editingFinished.connect(self.set_sampling_rate)
        self.enable_dac_btn.clicked.connect(self.enable_dac)
        self.disable_dac_btn.clicked.connect(self.disable_dac)

    # =========================
    # ACQUISITION TAB
    # =========================

    def build_sweep_tab(self):

        layout = QVBoxLayout()

        self.plot_widget = pg.PlotWidget()

        self.curve1 = self.plot_widget.plot(pen='y', name="ADC1")
        self.curve2 = self.plot_widget.plot(pen='r', name="ADC2")

        layout.addWidget(self.plot_widget)

        self.sweep.setLayout(layout)

        # update timer
        self.timer = pg.QtCore.QTimer()
        self.timer.timeout.connect(self.update_plot)
        self.timer.start(30)

    # =========================
    # ADC & DAC CONTROL
    # =========================
    def set_sampling_rate(self, value=None):
        if value is None:
            value = self.sampling_rate_input.text()
        self.sender.set_sampling_rate(value)

    def enable_dac(self):
        freq = self.dac_freq_input.text()
        self.sender.send(f"DAC:{freq}")

    def disable_dac(self):
        self.sender.send("DAC:OFF")
    # =========================
    # UDP COMMANDS
    # =========================

    def set_buffer(self, value):
        self.sender.set_buffer(value)

    def start_acquisition(self):
        self.sender.start_aq()

    def stop_acquisition(self):
        self.sender.stop_aq()

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