from turtle import mode

from PyQt6.QtWidgets import (
    QFormLayout, QLineEdit, QSizePolicy, QSpacerItem, QWidget, QVBoxLayout, QTabWidget,
    QLabel, QPushButton, QComboBox,
    QGroupBox, QGridLayout, QHBoxLayout, QCheckBox
)

import pyqtgraph as pg
import numpy as np
from lib.lock_in_amplifier import lock_in_amplifier
from lib.fast_fourier_transform import fft_amplitude_phase
from lib.root_mean_square import compute_rms_amplitude
class BaseDAQPage(QWidget):
    def __init__(self, receiver, sender):

        super().__init__()

        self.receiver = receiver
        self.sender = sender

        layout = QVBoxLayout()
        self.tabs = QTabWidget()
        self.setup = QWidget()
        self.sweep = QWidget()
        self.ext_sig = QWidget()

        self.tabs.addTab(self.setup, "Setup")
        self.tabs.addTab(self.sweep, " Internal Sweep (DDS)")
        self.tabs.addTab(self.ext_sig, "External Signal Input (Function Generator)")

        layout.addWidget(self.tabs)
        self.setLayout(layout)

        self.sweep_freqs = []
        self.sweep_amp = []
        self.sweep_phase = []
        self.last_freq = None
        self.sweeping = False
        self.current_freq = None
        self.time_offset_1 = 0
        self.time_offset_2 = 0
        self.adc_running = False

        self.build_setup_tab()
        self.build_sweep_tab()
        self.build_external_tab()
        # self.receiver.set_resolution(self.resolution.currentText())
        # Update timer
        self.timer = pg.QtCore.QTimer()
        self.timer.timeout.connect(self.update_plot)
        self.timer.start(30)
    # ============================================
    # 1. SETUP TAB
    # ============================================
    def build_setup_tab(self):
        layout = QVBoxLayout()
        # =========================
        # 1.1 ADC SETTINGS
        # =========================

        # Sampling rate
        adc_group = QGroupBox("Signal Acquisition (ADC)")
        adc_layout = QFormLayout()
        self.sampling_rate_input = QLineEdit("2500000") 
        adc_layout.addRow("Sampling Rate (Hz):", self.sampling_rate_input)

        # Buffer size
        self.buffer = QComboBox()
        self.buffer.addItems(["512", "1024", "2048", "4096", "8192", "16384"])
        self.buffer.setCurrentText("4096")
        adc_layout.addRow("Buffer Size:", self.buffer)

        #Resolution (optional, for display purposes only)
        self.resolution = QComboBox()
        self.resolution.addItems(["10-bit", "12-bit", "14-bit", "16-bit"])
        self.resolution.setCurrentText("16-bit")
        adc_layout.addRow("ADC Resolution:", self.resolution)
        

        # Control buttons
        button_layout = QGridLayout()
        self.start_adc=QPushButton("Start ADC")
        self.stop_adc=QPushButton("Stop ADC")
        button_layout.addWidget(self.start_adc, 0, 1)
        button_layout.addWidget(self.stop_adc, 0, 2)
        adc_layout.addRow(button_layout)
        adc_group.setLayout(adc_layout)
        # =========================
        # 1.2 DAC SETTINGS
        # =========================

        # DAC frequency
        dac_group = QGroupBox("Signal Generation (DAC)")
        dac_layout = QFormLayout()
        # self.dac_freq_input = QLineEdit("1000")  # 1 kHz default
        # dac_layout.addRow("Frequency (Hz):", self.dac_freq_input)
        # Frequency sweep inputs
        self.start_freq = QLineEdit("10")
        self.stop_freq = QLineEdit("100000")
        self.step_freq = QLineEdit("500")

        freq_layout = QHBoxLayout()
        freq_layout.addWidget(self.start_freq)
        freq_layout.addWidget(QLabel("to"))
        freq_layout.addWidget(self.stop_freq)
        freq_layout.addWidget(QLabel("Step:"))
        freq_layout.addWidget(self.step_freq)

        dac_layout.addRow("Frequency (Hz):", freq_layout)
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
        self.start_dac = QPushButton("Start DAC")
        self.stop_dac = QPushButton("Stop DAC")
        button_layout.addWidget(self.start_dac, 0, 0)
        button_layout.addWidget(self.stop_dac, 0, 1)
        dac_layout.addRow(button_layout)
        dac_group.setLayout(dac_layout)

        # =========================
        # 1.3 COMMUNICATION SETTINGS
        # =========================

        comm_group = QGroupBox("Communication Settings")
        comm_layout = QVBoxLayout()

        self.eth_checkbox = QCheckBox("Ethernet")
        self.usb_checkbox = QCheckBox("USB HS")

        # default (optional)
        self.eth_checkbox.setChecked(True)

        comm_layout.addWidget(self.eth_checkbox)
        comm_layout.addWidget(self.usb_checkbox)

        comm_group.setLayout(comm_layout)

        # =========================
        # 1.4 ADD TO MAIN LAYOUT
        # =========================
        # Horizontal layout for ADC and DAC groups
        # layout.addWidget(adc_group)
        # layout.addWidget(dac_group)
        # self.setup.setLayout(layout)

        # Vertical layout for ADC and DAC groups
        main_row = QHBoxLayout()
        main_row.addWidget(adc_group)
        main_row.addWidget(dac_group)
        layout.addLayout(main_row)
        layout.addWidget(comm_group)
        self.setup.setLayout(layout)

        # connections
        self.buffer.currentTextChanged.connect(self.set_buffer)
        self.start_adc.clicked.connect(self.start_acquisition)
        self.stop_adc.clicked.connect(self.stop_acquisition)
        self.sampling_rate_input.editingFinished.connect(self.set_sampling_rate)
        self.resolution.currentTextChanged.connect(self.set_resolution)
        self.start_dac.clicked.connect(self.start_generation)
        self.stop_dac.clicked.connect(self.stop_generation)
        #Reset sweep data when frequency changes
        # self.dac_freq_input.editingFinished.connect(self.on_freq_changed)
        # Update mode tabs when actuator changes
        self.actuator_selector.currentTextChanged.connect(self.update_actuator)
        self.update_actuator()
    # =========================
    # 2. SwEEP TAB
    # =========================
    def build_sweep_tab(self):

        layout = QVBoxLayout()

        # =========================================================
        # Graph 1 controls
        # =========================================================
        self.y_selector1 = QComboBox()
        self.y_selector1.addItems(["Raw ADC1 (V)", "Amplitude (dB)", "Phase (deg)"])

        self.x_selector1 = QComboBox()
        self.x_selector1.addItems(["Sample Index", "Frequency (Hz)"])

        row1 = QHBoxLayout()
        row1.addWidget(QLabel("Graph 1 Y:"))
        row1.addWidget(self.y_selector1)
        row1.addSpacing(20)
        row1.addWidget(QLabel("X:"))
        row1.addWidget(self.x_selector1)

        self.cursor_checkbox = QCheckBox("Cursor")
        self.cursor_checkbox.setChecked(True)
        row1.addSpacing(20)
        row1.addWidget(self.cursor_checkbox)
        row1.addStretch()

        # Graph 1 plot
        self.plot_widget1 = pg.PlotWidget()
        self.curve1 = self.plot_widget1.plot(pen='y')
        self.cursor1 = self.setup_cursor(self.plot_widget1, self.curve1)
        self.cursor_checkbox.toggled.connect(self.toggle_sweep_cursor)
        # =========================================================
        # Graph 2 controls
        # =========================================================
        self.y_selector2 = QComboBox()
        self.y_selector2.addItems(["Raw ADC2 (V)", "Amplitude (dB)", "Phase (deg)"])

        self.x_selector2 = QComboBox()
        self.x_selector2.addItems(["Sample Index", "Frequency (Hz)"])

        row2 = QHBoxLayout()
        row2.addWidget(QLabel("Graph 2 Y:"))
        row2.addWidget(self.y_selector2)
        row2.addSpacing(20)
        row2.addWidget(QLabel("X:"))
        row2.addWidget(self.x_selector2)
        row2.addStretch()

        # Graph 2 plot
        self.plot_widget2 = pg.PlotWidget()
        self.curve2 = self.plot_widget2.plot(pen='r')
        self.cursor2 = self.setup_cursor(self.plot_widget2, self.curve2)

        # Optional: make combo boxes a bit cleaner
        self.y_selector1.setFixedWidth(140)
        self.x_selector1.setFixedWidth(140)
        self.y_selector2.setFixedWidth(140)
        self.x_selector2.setFixedWidth(140)

        # Link x axis
        self.plot_widget2.setXLink(self.plot_widget1)

        # Disable automatic SI scaling like (x0.001)
        self.plot_widget1.getAxis("bottom").enableAutoSIPrefix(False)
        self.plot_widget1.getAxis("left").enableAutoSIPrefix(False)
        self.plot_widget2.getAxis("bottom").enableAutoSIPrefix(False)
        self.plot_widget2.getAxis("left").enableAutoSIPrefix(False)

        # Force same left axis width
        self.plot_widget1.getAxis("left").setWidth(60)
        self.plot_widget2.getAxis("left").setWidth(60)

        # Add in the order you want
        layout.addLayout(row1)
        layout.addWidget(self.plot_widget1, 1)
        layout.addLayout(row2)
        layout.addWidget(self.plot_widget2, 1)

        self.sweep.setLayout(layout)

        # Connect axis selector signals
        self.y_selector1.currentTextChanged.connect(self.update_axis_constraints)
        self.x_selector1.currentTextChanged.connect(self.update_axis_constraints)
        self.y_selector2.currentTextChanged.connect(self.update_axis_constraints)
        self.x_selector2.currentTextChanged.connect(self.update_axis_constraints)

        self.y_selector1.currentTextChanged.connect(self.update_plot_labels)
        self.x_selector1.currentTextChanged.connect(self.update_plot_labels)
        self.y_selector2.currentTextChanged.connect(self.update_plot_labels)
        self.x_selector2.currentTextChanged.connect(self.update_plot_labels)

        self.y_selector1.currentTextChanged.connect(self.reset_time_axis)
        self.y_selector2.currentTextChanged.connect(self.reset_time_axis)

        # Set default labels immediately when GUI opens
        self.update_axis_constraints()
        self.update_plot_labels()
    # =========================
    # 3. External TAB (enable Function generator selection)
    # =========================
    def build_external_tab(self):
        layout = QVBoxLayout()
        # =========================================================
        # Graph 1 controls
        # =========================================================
        self.ext_y_selector1 = QComboBox()
        self.ext_y_selector1.addItems(["Raw ADC1 (V)", "Amplitude (dB)", "Phase (deg)"])

        self.ext_x_selector1 = QComboBox()
        self.ext_x_selector1.addItems(["Sample Index", "Frequency (Hz)"])

        row1 = QHBoxLayout()
        row1.addWidget(QLabel("Graph 1 Y:"))
        row1.addWidget(self.ext_y_selector1)
        row1.addSpacing(20)
        row1.addWidget(QLabel("X:"))
        row1.addWidget(self.ext_x_selector1)
        row1.addStretch()

        # Graph 1 plot
        self.ext_plot_widget1 = pg.PlotWidget()
        self.ext_curve1 = self.ext_plot_widget1.plot(pen='y')
        self.ext_cursor1 = self.setup_cursor(self.ext_plot_widget1, self.ext_curve1)
        # =========================================================
        # Graph 2 controls
        # =========================================================
        self.ext_y_selector2 = QComboBox()
        self.ext_y_selector2.addItems(["Raw ADC2 (V)", "Amplitude (dB)", "Phase (deg)"])

        self.ext_x_selector2 = QComboBox()
        self.ext_x_selector2.addItems(["Sample Index", "Frequency (Hz)"])

        row2 = QHBoxLayout()
        row2.addWidget(QLabel("Graph 2 Y:"))
        row2.addWidget(self.ext_y_selector2)
        row2.addSpacing(20)
        row2.addWidget(QLabel("X:"))
        row2.addWidget(self.ext_x_selector2)
        row2.addStretch()

        # Graph 2 plot
        self.ext_plot_widget2 = pg.PlotWidget()
        self.ext_curve2 = self.ext_plot_widget2.plot(pen='r')
        self.ext_cursor2 = self.setup_cursor(self.ext_plot_widget2, self.ext_curve2)
        # Optional: make combo boxes a bit cleaner
        self.ext_y_selector1.setFixedWidth(140)
        self.ext_x_selector1.setFixedWidth(140)
        self.ext_y_selector2.setFixedWidth(140)
        self.ext_x_selector2.setFixedWidth(140)

        # Link x axis
        self.ext_plot_widget2.setXLink(self.ext_plot_widget1)

        # Disable automatic SI scaling like (x0.001)
        self.ext_plot_widget1.getAxis("bottom").enableAutoSIPrefix(False)
        self.ext_plot_widget1.getAxis("left").enableAutoSIPrefix(False)
        self.ext_plot_widget2.getAxis("bottom").enableAutoSIPrefix(False)
        self.ext_plot_widget2.getAxis("left").enableAutoSIPrefix(False)

        # Force same left axis width
        self.ext_plot_widget1.getAxis("left").setWidth(60)
        self.ext_plot_widget2.getAxis("left").setWidth(60)

        # Add in the order you want
        layout.addLayout(row1)
        layout.addWidget(self.ext_plot_widget1, 1)
        layout.addLayout(row2)
        layout.addWidget(self.ext_plot_widget2, 1)

        self.ext_sig.setLayout(layout)

        # Connect axis selector signals
        self.ext_y_selector1.currentTextChanged.connect(self.update_axis_constraints)
        self.ext_x_selector1.currentTextChanged.connect(self.update_axis_constraints)
        self.ext_y_selector2.currentTextChanged.connect(self.update_axis_constraints)
        self.ext_x_selector2.currentTextChanged.connect(self.update_axis_constraints)

        self.ext_y_selector1.currentTextChanged.connect(self.update_plot_labels)
        self.ext_x_selector1.currentTextChanged.connect(self.update_plot_labels)
        self.ext_y_selector2.currentTextChanged.connect(self.update_plot_labels)
        self.ext_x_selector2.currentTextChanged.connect(self.update_plot_labels)

        self.ext_y_selector1.currentTextChanged.connect(self.reset_time_axis)
        self.ext_y_selector2.currentTextChanged.connect(self.reset_time_axis)

        # Set default labels immediately when GUI opens
        self.update_axis_constraints()
        self.update_plot_labels()

# =========================
# 4. Cursor control
# =========================
    def setup_cursor(self, plot_widget, curve):
        green = (0, 255, 120)

        green_pen = pg.mkPen(color=green, width=1.5)

        v_line = pg.InfiniteLine(angle=90, movable=False, pen=green_pen)
        h_line = pg.InfiniteLine(angle=0, movable=False, pen=green_pen)

        plot_widget.addItem(v_line, ignoreBounds=True)
        plot_widget.addItem(h_line, ignoreBounds=True)

        label = pg.TextItem(anchor=(0, 1), color=green)
        plot_widget.addItem(label, ignoreBounds=True)

        point_marker = pg.ScatterPlotItem(
            size=8,
            brush=pg.mkBrush(green),
            pen=pg.mkPen(green)
        )
        plot_widget.addItem(point_marker, ignoreBounds=True)

        def mouse_moved(evt):
            pos = evt[0]   # SignalProxy sends a tuple

            if not plot_widget.sceneBoundingRect().contains(pos):
                return

            mouse_point = plot_widget.plotItem.vb.mapSceneToView(pos)
            mouse_x = mouse_point.x()

            x_data, y_data = curve.getData()

            if x_data is None or y_data is None:
                return
            if len(x_data) == 0 or len(y_data) == 0:
                return

            x_arr = np.asarray(x_data)
            y_arr = np.asarray(y_data)

            valid = np.isfinite(x_arr) & np.isfinite(y_arr)
            if not np.any(valid):
                return

            x_arr = x_arr[valid]
            y_arr = y_arr[valid]

            idx = np.argmin(np.abs(x_arr - mouse_x))
            x = x_arr[idx]
            y = y_arr[idx]

            v_line.setPos(x)
            h_line.setPos(y)
            point_marker.setData([x], [y])

            label.setPos(x, y)
            label.setText(f"x = {x:.2f}\ny = {y:.4f}")

        proxy = pg.SignalProxy(
            plot_widget.scene().sigMouseMoved,
            rateLimit=60,
            slot=mouse_moved
        )

        return {
            "v_line": v_line,
            "h_line": h_line,
            "label": label,
            "point_marker": point_marker,
            "proxy": proxy,
        }
    
    def set_cursor_visible(self, cursor_dict, visible):
        if cursor_dict is None:
            return

        cursor_dict["v_line"].setVisible(visible)
        cursor_dict["h_line"].setVisible(visible)
        cursor_dict["label"].setVisible(visible)
        cursor_dict["point_marker"].setVisible(visible)

    def toggle_sweep_cursor(self, checked):
        self.set_cursor_visible(self.cursor1, checked)
        self.set_cursor_visible(self.cursor2, checked)

    def toggle_external_cursor(self, checked):
        self.set_cursor_visible(self.ext_cursor1, checked)
        self.set_cursor_visible(self.ext_cursor2, checked)
    # =========================
    # ADC & DAC CONTROL (USB COMMUNICATION/UDP COMMANDS)
    # =========================
    # ADC control
    def set_buffer(self, value):
        if self.adc_running:
            self.sender.stop_aq()
            self.adc_running = False
        self.sender.set_buffer(value)
        self.receiver.set_buffer_size(int(value))
    def start_acquisition(self):
        self.sender.start_aq()
        self.adc_running= True

    def stop_acquisition(self):
        self.sender.stop_aq()
        self.adc_running=False

    def set_sampling_rate(self, value=None):
        if value is None:
            value = self.sampling_rate_input.text()

        if self.adc_running:
            self.sender.stop_aq()
            self.adc_running = False

        self.sender.set_sampling_rate(value)

    def set_resolution(self, value):
        if self.adc_running:
            self.sender.stop_aq()
            self.adc_running = False
        self.sender.set_adc_resolution(value)
        self.receiver.set_resolution(value)

    # DAC control
    def start_generation(self):
        self.sender.start_gen()
        self.reset_sweep()
        self.sweeping = True
        self.current_freq = float(self.start_freq.text())
        # send FIRST frequency
        self.set_dac_freq(self.current_freq)

    def stop_generation(self):
        self.sender.stop_gen()
        self.sweeping = False

    def set_dac_freq(self, value=None):
        # self.sender.send(f"DAC:{float(value
        if self.sweeping == True:
            value = self.current_freq
        else:
            value = float(self.start_freq.text())
        self.sender.set_dac_freq(value)

    def reset_sweep(self):
        self.sweep_freqs.clear()
        self.sweep_amp.clear()
        self.sweep_phase.clear()
        self.last_freq = None
        # CLEAR PLOT
        self.curve1.clear()
        self.curve2.clear()
        self.plot_widget1.enableAutoRange(axis='y', enable=True)
        self.plot_widget2.enableAutoRange(axis='y', enable=True)
    # =========================
    # MODE Controll (Enable/Disable tabs based on actuator)
    # =========================
    def update_actuator(self):
        actuator = self.actuator_selector.currentText()
        # tab indexes (IMPORTANT: adjust if different)
        SETUP_TAB = 0
        SWEEP_TAB = 1
        EXTERNAL_SIGNAL_TAB  = 2
        if actuator == "Function Generator":
            # disable Sweep (DDS)
            self.tabs.setTabEnabled(SWEEP_TAB, False)
            self.start_dac.setEnabled(False)
            self.stop_dac.setEnabled(False)
            self.start_freq.setEnabled(False)
            self.stop_freq.setEnabled(False)
            self.step_freq.setEnabled(False)
            self.sweeping = False
            self.tabs.setTabEnabled(EXTERNAL_SIGNAL_TAB, True)
        elif actuator == "Direct Digital Synthesis (DDS)":
            # disable Live Data
            self.tabs.setTabEnabled(SWEEP_TAB, True)
            self.start_dac.setEnabled(True)
            self.stop_dac.setEnabled(True)
            self.start_freq.setEnabled(True)
            self.stop_freq.setEnabled(True)
            self.step_freq.setEnabled(True)
            self.tabs.setTabEnabled(EXTERNAL_SIGNAL_TAB, False)
        elif actuator == "STM32 DAC Output":
            # optional: allow both
            self.tabs.setTabEnabled(SWEEP_TAB, True)
            self.start_dac.setEnabled(True)
            self.stop_dac.setEnabled(True)
            self.start_freq.setEnabled(True)
            self.stop_freq.setEnabled(True)
            self.step_freq.setEnabled(True)
            self.tabs.setTabEnabled(EXTERNAL_SIGNAL_TAB, False)

    def get_active_plot_widgets(self):
        actuator = self.actuator_selector.currentText()
        if actuator == "Function Generator":
            return {
                "y1": self.ext_y_selector1,
                "x1": self.ext_x_selector1,
                "y2": self.ext_y_selector2,
                "x2": self.ext_x_selector2,
                "plot1": self.ext_plot_widget1,
                "plot2": self.ext_plot_widget2,
                "curve1": self.ext_curve1,
                "curve2": self.ext_curve2,
            }
        else:
            return {
                "y1": self.y_selector1,
                "x1": self.x_selector1,
                "y2": self.y_selector2,
                "x2": self.x_selector2,
                "plot1": self.plot_widget1,
                "plot2": self.plot_widget2,
                "curve1": self.curve1,
                "curve2": self.curve2,
            }
    # Update axis options based on measurement method (e.g. disable Frequency x-axis for RMS)
    def update_axis_constraints(self):
        w = self.get_active_plot_widgets()

        y1_box = w["y1"]
        x1_box = w["x1"]
        y2_box = w["y2"]
        x2_box = w["x2"]

        # -------- GRAPH 1 --------
        y1 = y1_box.currentText()
        model1 = x1_box.model()

        for i in range(x1_box.count()):
            text = x1_box.itemText(i)

            if y1 == "Raw ADC1 (V)":
                if text == "Frequency (Hz)":
                    model1.item(i).setEnabled(False)
                    if x1_box.currentText() == "Frequency (Hz)":
                        x1_box.setCurrentText("Sample Index")
                else:
                    model1.item(i).setEnabled(True)

            elif y1 in ["Amplitude (dB)", "Phase (deg)"]:
                if text == "Sample Index":
                    model1.item(i).setEnabled(False)
                    if x1_box.currentText() == "Sample Index":
                        x1_box.setCurrentText("Frequency (Hz)")
                else:
                    model1.item(i).setEnabled(True)

            else:
                model1.item(i).setEnabled(True)

        # -------- GRAPH 2 --------
        y2 = y2_box.currentText()
        model2 = x2_box.model()

        for i in range(x2_box.count()):
            text = x2_box.itemText(i)

            if y2 == "Raw ADC2 (V)":
                if text == "Frequency (Hz)":
                    model2.item(i).setEnabled(False)
                    if x2_box.currentText() == "Frequency (Hz)":
                        x2_box.setCurrentText("Sample Index")
                else:
                    model2.item(i).setEnabled(True)

            elif y2 in ["Amplitude (dB)", "Phase (deg)"]:
                if text == "Sample Index":
                    model2.item(i).setEnabled(False)
                    if x2_box.currentText() == "Sample Index":
                        x2_box.setCurrentText("Frequency (Hz)")
                else:
                    model2.item(i).setEnabled(True)

            else:
                model2.item(i).setEnabled(True)
    def update_plot_labels(self):
        w = self.get_active_plot_widgets()

        y1_box = w["y1"]
        x1_box = w["x1"]
        y2_box = w["y2"]
        x2_box = w["x2"]
        plot1 = w["plot1"]
        plot2 = w["plot2"]

        # -------- Graph 1 --------
        x1 = x1_box.currentText()
        y1 = y1_box.currentText()

        plot1.setTitle(f"{y1} vs {x1}")
        plot1.setLabel("bottom", x1)
        plot1.setLabel("left", y1)

        # -------- Graph 2 --------
        x2 = x2_box.currentText()
        y2 = y2_box.currentText()

        plot2.setTitle(f"{y2} vs {x2}")
        plot2.setLabel("bottom", x2)
        plot2.setLabel("left", y2)

    def reset_time_axis(self):
        self.time_offset_1 = 0
        self.time_offset_2 = 0
    # ========================================================
    # PLOTTING
    # ========================================================
    def update_plot(self):
        w = self.get_active_plot_widgets()

        y1_box = w["y1"]
        x1_box = w["x1"]
        y2_box = w["y2"]
        x2_box = w["x2"]
        plot1 = w["plot1"]
        plot2 = w["plot2"]
        curve1 = w["curve1"]
        curve2 = w["curve2"]

        # raw1, raw2 = self.receiver.get_data()
        adc1, adc2 = self.receiver.get_data_volts(vref=3.3)
        # print("RAW ADC1 min/max:", np.min(raw1), np.max(raw1))
        # print("RAW ADC2 min/max:", np.min(raw2), np.max(raw2))
        # print("VOLT ADC1 min/max:", np.min(adc1), np.max(adc1))
        # print("VOLT ADC2 min/max:", np.min(adc2), np.max(adc2))
        # print("Resolution:", self.resolution.currentText())

        fs = float(self.sampling_rate_input.text())
        if self.sweeping:
            f_ref = self.current_freq
        else:
            f_ref = float(self.start_freq.text())

        mode = self.mode_selector.currentText()
        if mode == "Lock-in Amplifier":
            amp, phase, _, _ = lock_in_amplifier(
                reference_signal=adc1,
                input_signal=adc2,
                freq=f_ref,
                fs=fs,
                use_generated=False,
                use_filter=True
            )
        elif mode == "Root Mean Square (RMS)":
            amp, v_sig, v_ref = compute_rms_amplitude(adc1, adc2)
            phase = 0
        elif mode == "Fast Fourier Transform (FFT)":
            amp, phase, _, _ = fft_amplitude_phase(adc1, adc2, fs, f_ref)

        y1 = y1_box.currentText()
        x1 = x1_box.currentText()
        y2 = y2_box.currentText()
        x2 = x2_box.currentText()

        if self.last_freq != f_ref:
            self.sweep_freqs.append(f_ref)
            self.sweep_amp.append(amp)
            self.sweep_phase.append(np.degrees(phase))
            self.last_freq = f_ref

        freqs = np.array(self.sweep_freqs)
        amps = np.array(self.sweep_amp)
        phases = np.array(self.sweep_phase)

        # only require sweep data if one graph is using frequency
        need_freq_data = (x1 == "Frequency (Hz)") or (x2 == "Frequency (Hz)")

        if need_freq_data and len(freqs) == 0:
            return

        if len(freqs) > 0:
            idx = np.argsort(freqs)
            freqs = freqs[idx]
            amps = amps[idx]
            phases = phases[idx]

        # X-link control
        if x1 == x2:
            plot2.setXLink(plot1)
        else:
            plot1.setXLink(None)
            plot2.setXLink(None)

        # -------- GRAPH 1 --------
        if x1 == "Frequency (Hz)":
            if y1 == "Amplitude (dB)":
                curve1.setData(freqs, amps)
            elif y1 == "Phase (deg)":
                curve1.setData(freqs, phases)
            plot1.enableAutoRange(axis='y', enable=True)
        else:
            x = np.arange(len(adc1))
            curve1.setData(x, adc1)
            plot1.enableAutoRange(axis='y', enable=False)

            if self.adc_running:
                self.time_offset_1 += len(adc1) / fs

        # -------- GRAPH 2 --------
        if x2 == "Frequency (Hz)":
            if y2 == "Amplitude (dB)":
                curve2.setData(freqs, amps)
            elif y2 == "Phase (deg)":
                curve2.setData(freqs, phases)
            plot2.enableAutoRange(axis='y', enable=True)
        else:
            x = np.arange(len(adc2))
            curve2.setData(x, adc2)
            plot2.enableAutoRange(axis='y', enable=False)

            if self.adc_running:
                self.time_offset_2 += len(adc2) / fs

        # Sweep stepping only for DDS / internal sweep
        if self.sweeping:
            step = float(self.step_freq.text())
            stop = float(self.stop_freq.text())

            self.current_freq += step
            if self.current_freq > stop:
                print("Sweep finished")
                self.sweeping = False
            else:
                self.set_dac_freq(self.current_freq)