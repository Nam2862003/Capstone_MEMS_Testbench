from turtle import mode

from PyQt6.QtWidgets import (
    QFormLayout, QLineEdit, QWidget, QVBoxLayout, QTabWidget,
    QLabel, QPushButton, QComboBox,
    QGroupBox, QGridLayout
)

import pyqtgraph as pg
import numpy as np
from lib.lock_in_amplifier import lock_in_amplifier
from lib.fast_fourier_transform import fft_amplitude_phase
from lib.root_mean_square import compute_rms_amplitude, rms_amplitude
class BaseDAQPage(QWidget):
    def __init__(self, receiver, sender):

        super().__init__()

        self.receiver = receiver
        self.sender = sender

        layout = QVBoxLayout()
        self.tabs = QTabWidget()
        self.setup = QWidget()
        self.sweep = QWidget()
        self.live_data = QWidget()

        self.tabs.addTab(self.setup, "Setup")
        self.tabs.addTab(self.sweep, "Sweep (DDS)")
        self.tabs.addTab(self.live_data, "Live Data (Function Generator)")

        layout.addWidget(self.tabs)
        self.setLayout(layout)

        self.sweep_freqs = []
        self.sweep_amp = []
        self.sweep_phase = []
        self.last_freq = None
        self.sweeping = False
        self.current_freq = None
        self.time_offset = 0

        self.build_setup_tab()
        self.build_sweep_tab()
        self.update_actuator()
    # ============================================
    # 1. SETUP TAB
    # ============================================
    def build_setup_tab(self):
        layout = QVBoxLayout()
        # =========================
        # 1.1 ADC SETTINGS
        # =========================
        # Sampling rate
        adc_group = QGroupBox("Acquisition (ADC)")
        adc_layout = QFormLayout()
        self.sampling_rate_input = QLineEdit("1000000")
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
        # 1.2 DAC SETTINGS
        # =========================
        # DAC frequency
        dac_group = QGroupBox("Signal Generation (DAC)")
        dac_layout = QFormLayout()
        self.dac_freq_input = QLineEdit("1000")  # 1 kHz default
        dac_layout.addRow("Frequency (Hz):", self.dac_freq_input)
        dac_group.setLayout(dac_layout)
        # Actuator Selector
        self.actuator_selector = QComboBox()
        self.actuator_selector.addItems([
            "Direct Digital Synthesis (DDS)",
            "Function Generator",
            "STM32 DAC Output"
        ])
        dac_layout.addRow("Actuator:", self.actuator_selector)
        # Mode selector
        self.mode_selector = QComboBox()
        self.mode_selector.addItems([
            "Root Mean Square (RMS)",
            "Fast Fourier Transform (FFT)",
            "Lock-in Amplifier",
        ])
        dac_layout.addRow("Measurement Method:", self.mode_selector)
        # DAC control buttons
        button_layout = QGridLayout()
        self.enable_dac_btn = QPushButton("Enable DAC")
        self.disable_dac_btn = QPushButton("Disable DAC")
        button_layout.addWidget(self.enable_dac_btn, 0, 0)
        button_layout.addWidget(self.disable_dac_btn, 0, 1)
        dac_layout.addRow(button_layout)
        #Reset sweep data when frequency changes
        self.dac_freq_input.editingFinished.connect(self.on_freq_changed)
        # Update mode tabs when actuator changes
        self.actuator_selector.currentTextChanged.connect(self.update_actuator)

        # =========================
        # 1.3 ADD TO MAIN LAYOUT
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
    # 2. SwEEP TAB
    # =========================
    def build_sweep_tab(self):

        layout = QVBoxLayout()

        # -------- SWEEP SETTINGS (CLEAN INSTRUMENT STYLE) --------
        sweep_layout = QGridLayout()
        self.start_freq = QLineEdit("10")
        self.stop_freq = QLineEdit("100000")
        self.step_freq = QLineEdit("500")

        # ===== Row 0: Labels =====
        sweep_layout.addWidget(QLabel("Start Freq (Hz)"), 0, 0)
        sweep_layout.addWidget(QLabel("Stop Freq (Hz)"), 0, 1)
        sweep_layout.addWidget(QLabel("Step (Hz)"), 0, 2)

        # ===== Row 1: Inputs =====
        sweep_layout.addWidget(self.start_freq, 1, 0)
        sweep_layout.addWidget(self.stop_freq, 1, 1)
        sweep_layout.addWidget(self.step_freq, 1, 2)

        # ===== Row 2: Buttons =====
        button_layout = QGridLayout()
        # ===== CREATE BUTTONS FIRST (FIX) =====
        self.sweep_start_btn = QPushButton("Start Sweep")
        self.sweep_stop_btn = QPushButton("Stop Sweep")
        # -------- BUTTON ROW (EQUAL SIZE) --------
        button_layout.addWidget(self.sweep_start_btn, 2, 0)
        button_layout.addWidget(self.sweep_stop_btn, 2, 1)

        # Make both buttons SAME width
        button_layout.setColumnStretch(0, 1)
        button_layout.setColumnStretch(1, 1)

        # ===== Layout tuning =====
        self.sweep_start_btn.setMinimumHeight(35)
        self.sweep_stop_btn.setMinimumHeight(35)

        # ===== CONNECT SIGNALS =====
        self.sweep_start_btn.clicked.connect(self.start_sweep)
        self.sweep_stop_btn.clicked.connect(self.stop_sweep)

        layout.addLayout(sweep_layout)
        layout.addLayout(button_layout)
        # -------- ----------------------AXIS SELECTORS ----------------------------------------------------------
        axis_layout = QGridLayout()
        # ------------------------ X-Y selectors--------------------------
        self.y_selector = QComboBox()
        self.y_selector.addItems([
            "Raw ADC1 and ADC2 (V)",
            "Amplitude (dB)",
            "Phase (deg)",
        ])

        self.x_selector = QComboBox()
        self.x_selector.addItems([
            "Time",
            "Frequency"
        ])

        axis_layout.addWidget(QLabel("Y-Axis:"), 0, 0)
        axis_layout.addWidget(self.y_selector, 0, 1)
        axis_layout.addWidget(QLabel("X-Axis:"), 0, 2)
        axis_layout.addWidget(self.x_selector, 0, 3)
        self.y_selector.setMinimumWidth(140)
        self.x_selector.setMinimumWidth(140)
 

        layout.addLayout(axis_layout)
        # -------- AXIS CONSTRAINTS for changing unit and scale --------
        self.y_selector.currentTextChanged.connect(self.update_axis_constraints)
        self.x_selector.currentTextChanged.connect(self.update_axis_constraints)
        # -------- PLOT AREA --------
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
    # ADC & DAC CONTROL (USB COMMUNICATION/UDP COMMANDS)
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

    def set_buffer(self, value):
        self.sender.set_buffer(value)

    def start_acquisition(self):
        self.sender.start_aq()

    def stop_acquisition(self):
        self.sender.stop_aq()

    def start_sweep(self):
        self.reset_sweep()
        self.sweeping = True
        self.current_freq = float(self.start_freq.text())
        self.sender.send(f"DAC:{int(self.current_freq)}")
    def stop_sweep(self):
        self.sweeping = False

    # =========================
    # MODE Controll (Enable/Disable tabs based on actuator)
    # =========================
    def update_actuator(self):
        actuator = self.actuator_selector.currentText()
        # tab indexes (IMPORTANT: adjust if different)
        SETUP_TAB = 0
        SWEEP_TAB = 1
        LIVE_TAB  = 2
        if actuator == "Function Generator":
            # disable Sweep (DDS)
            self.tabs.setTabEnabled(SWEEP_TAB, False)
            self.tabs.setTabEnabled(LIVE_TAB, True)
        elif actuator == "Direct Digital Synthesis (DDS)":
            # disable Live Data
            self.tabs.setTabEnabled(SWEEP_TAB, True)
            self.tabs.setTabEnabled(LIVE_TAB, False)
        elif actuator == "STM32 DAC Output":
            # optional: allow both
            self.tabs.setTabEnabled(SWEEP_TAB, True)
            self.tabs.setTabEnabled(LIVE_TAB, True)
    # Update axis options based on measurement method (e.g. disable Frequency x-axis for RMS)
    def update_axis_constraints(self):
        y_mode = self.y_selector.currentText()
        # get model of x_selector
        model = self.x_selector.model()
        for i in range(self.x_selector.count()):
            text = self.x_selector.itemText(i)
            if y_mode == "Raw ADC1 and ADC2 (V)":
                # disable Frequency
                if text == "Frequency":
                    model.item(i).setEnabled(False)
                    # if currently selected → force switch
                    if self.x_selector.currentText() == "Frequency":
                        self.x_selector.setCurrentText("Time")
            elif y_mode in ["Amplitude (dB)", "Phase (deg)"]:
                # disable Time
                 if text == "Time":
                    model.item(i).setEnabled(False)
                    # if currently selected → force switch
                    if self.x_selector.currentText() == "Time":
                        self.x_selector.setCurrentText("Frequency")
            else:
                # enable everything
                model.item(i).setEnabled(True)
    # ========================================================
    # PLOTTING
    # ========================================================
    def reset_sweep(self):
        self.sweep_freqs.clear()
        self.sweep_amp.clear()
        self.sweep_phase.clear()
        self.last_freq = None
        # CLEAR PLOT
        self.curve1.clear()

    def on_freq_changed(self):
        self.reset_sweep()
        freq = self.dac_freq_input.text()
        self.sender.send(f"DAC:{freq}")
        
    def update_plot(self):
        adc1, adc2 = self.receiver.get_data() # Code is on udp_receiver.py
        fs = float(self.sampling_rate_input.text())
        if self.sweeping == True:
            f_ref = self.current_freq
        else:
            f_ref = float(self.dac_freq_input.text())
        # -------- ADC → VOLTAGE --------
        adc1 = adc1 / 65535 * 3.3
        adc2 = adc2 / 65535 * 3.3
        N = len(adc2)
        # -------- Selection of measurement method and create plotting --------
        mode = self.mode_selector.currentText()
        if mode == "Lock-in Amplifier":
            amp, phase, _, _ = lock_in_amplifier(
                reference_signal=adc1,
                input_signal=adc2,
                freq=f_ref,
                fs=fs,
                use_generated=False,
                use_filter=False
            )
        elif mode == "Root Mean Square (RMS)":
            amp, v_sig, v_ref = compute_rms_amplitude(adc1, adc2)
            phase = 0                  # RMS has NO phase
        elif mode == "Fast Fourier Transform (FFT)":
            amp, phase, _, _ = fft_amplitude_phase(adc1, adc2, fs, f_ref)

        # -------- AXIS SELECTION --------
        y_axis = self.y_selector.currentText()
        x_axis = self.x_selector.currentText()
        # ===============================
        # Setting 1: FREQUENCY on x-axis 
        # ===============================
        if x_axis == "Frequency":
            # store only if frequency changed
            if self.last_freq != f_ref:
                self.sweep_freqs.append(f_ref)
                self.sweep_amp.append(amp)
                self.sweep_phase.append(np.degrees(phase))
                self.last_freq = f_ref
            freqs = np.array(self.sweep_freqs)
            amps = np.array(self.sweep_amp)
            phases = np.array(self.sweep_phase)
            if len(freqs) == 0:
                return
            # sort
            idx = np.argsort(freqs)
            freqs = freqs[idx]
            amps = amps[idx]
            phases = phases[idx]
            # select Y
            if y_axis == "Amplitude (dB)":
                y_sweep = amps
            elif y_axis == "Phase (deg)":
                y_sweep = phases
            else:
                return  # prevent Voltage vs Frequency bug
            self.curve1.clear()
            self.curve2.clear()
            self.plot_widget.enableAutoRange(axis='y', enable=True)
            self.curve1.setData(freqs, y_sweep)
        # ===============================
        # Setting 2: TIME on x-axis
        # ===============================
        else:   
                self.curve1.clear()
                self.curve2.clear()
                self.plot_widget.enableAutoRange(axis='y', enable=False)
                self.plot_widget.setYRange(0, 1)   # or tighter range
                time = np.arange(len(adc2)) / fs + self.time_offset
                self.time_offset = time[-1]  # update for next frame
                self.curve1.setData(time, adc1)
                self.curve2.setData(time, adc2)
        # ===============================
        # SWEEP STEP LOGIC
        # ===============================
        if self.sweeping:
            step = float(self.step_freq.text())
            stop = float(self.stop_freq.text())
            # move to next frequency
            self.current_freq += step
            if self.current_freq > stop:
                print("Sweep finished")
                self.sweeping = False
            else:
                # send to DDS / STM32
                self.sender.send(f"DAC:{int(self.current_freq)}")