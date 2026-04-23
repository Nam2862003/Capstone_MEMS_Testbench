from turtle import mode

from PyQt6.QtWidgets import (
    QFormLayout, QLineEdit, QSizePolicy, QSpacerItem, QWidget, QVBoxLayout, QTabWidget,
    QLabel, QPushButton, QComboBox,
    QGroupBox, QGridLayout, QHBoxLayout, QCheckBox
)
from PyQt6.QtCore import Qt

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

        self.cursor_checkbox1 = QCheckBox("Cursors")
        self.cursor_checkbox1.setObjectName("CursorToggle")
        self.cursor_checkbox1.setChecked(True)
        self.cursor_mode1 = QComboBox()
        self.cursor_mode1.addItems(["Vertical", "Horizontal", "Track"])
        row1.addSpacing(20)
        row1.addWidget(self.cursor_checkbox1)
        row1.addWidget(self.cursor_mode1)
        self.cursor_readout1 = QLabel()
        self.cursor_readout1.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        row1.addWidget(self.cursor_readout1, 1)
        row1.addStretch()

        # Graph 1 plot
        self.plot_widget1 = pg.PlotWidget()
        self.curve1 = self.plot_widget1.plot(pen='y')
        self.cursor1 = self.setup_cursor(self.plot_widget1, self.curve1)
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
        self.cursor_checkbox2 = QCheckBox("Cursors")
        self.cursor_checkbox2.setObjectName("CursorToggle")
        self.cursor_checkbox2.setChecked(True)
        self.cursor_mode2 = QComboBox()
        self.cursor_mode2.addItems(["Vertical", "Horizontal", "Track"])
        row2.addSpacing(20)
        row2.addWidget(self.cursor_checkbox2)
        row2.addWidget(self.cursor_mode2)
        self.cursor_readout2 = QLabel()
        self.cursor_readout2.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        row2.addWidget(self.cursor_readout2, 1)
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
        self.cursor_mode1.setFixedWidth(120)
        self.cursor_mode2.setFixedWidth(120)

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
        self.attach_cursor_controls(self.cursor1, self.cursor_checkbox1, self.cursor_mode1, self.cursor_readout1)
        self.attach_cursor_controls(self.cursor2, self.cursor_checkbox2, self.cursor_mode2, self.cursor_readout2)
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
        self.ext_cursor_checkbox1 = QCheckBox("Cursors")
        self.ext_cursor_checkbox1.setObjectName("CursorToggle")
        self.ext_cursor_checkbox1.setChecked(True)
        self.ext_cursor_mode1 = QComboBox()
        self.ext_cursor_mode1.addItems(["Vertical", "Horizontal", "Track"])
        row1.addSpacing(20)
        row1.addWidget(self.ext_cursor_checkbox1)
        row1.addWidget(self.ext_cursor_mode1)
        self.ext_cursor_readout1 = QLabel()
        self.ext_cursor_readout1.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        row1.addWidget(self.ext_cursor_readout1, 1)
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
        self.ext_cursor_checkbox2 = QCheckBox("Cursors")
        self.ext_cursor_checkbox2.setObjectName("CursorToggle")
        self.ext_cursor_checkbox2.setChecked(True)
        self.ext_cursor_mode2 = QComboBox()
        self.ext_cursor_mode2.addItems(["Vertical", "Horizontal", "Track"])
        row2.addSpacing(20)
        row2.addWidget(self.ext_cursor_checkbox2)
        row2.addWidget(self.ext_cursor_mode2)
        self.ext_cursor_readout2 = QLabel()
        self.ext_cursor_readout2.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        row2.addWidget(self.ext_cursor_readout2, 1)
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
        self.ext_cursor_mode1.setFixedWidth(120)
        self.ext_cursor_mode2.setFixedWidth(120)

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
        self.attach_cursor_controls(self.ext_cursor1, self.ext_cursor_checkbox1, self.ext_cursor_mode1, self.ext_cursor_readout1)
        self.attach_cursor_controls(self.ext_cursor2, self.ext_cursor_checkbox2, self.ext_cursor_mode2, self.ext_cursor_readout2)

# =========================
# 4. Cursor control
# =========================
    def setup_cursor(self, plot_widget, curve):
        cursor_a_pen = pg.mkPen(color=(0, 255, 120), width=1.5)
        cursor_b_pen = pg.mkPen(color=(255, 190, 0), width=1.5)
        track_pen = pg.mkPen(color=(80, 170, 255), width=1.2)

        v_line_a = pg.InfiniteLine(angle=90, movable=True, pen=cursor_a_pen)
        v_line_b = pg.InfiniteLine(angle=90, movable=True, pen=cursor_b_pen)
        h_line_a = pg.InfiniteLine(angle=0, movable=True, pen=cursor_a_pen)
        h_line_b = pg.InfiniteLine(angle=0, movable=True, pen=cursor_b_pen)
        track_v = pg.InfiniteLine(angle=90, movable=False, pen=track_pen)
        track_h = pg.InfiniteLine(angle=0, movable=False, pen=track_pen)

        for item in (v_line_a, v_line_b, h_line_a, h_line_b, track_v, track_h):
            plot_widget.addItem(item, ignoreBounds=True)

        marker_a = pg.ScatterPlotItem(size=9, brush=pg.mkBrush(0, 255, 120), pen=cursor_a_pen)
        marker_b = pg.ScatterPlotItem(size=9, brush=pg.mkBrush(255, 190, 0), pen=cursor_b_pen)
        track_marker = pg.ScatterPlotItem(size=9, brush=pg.mkBrush(80, 170, 255), pen=track_pen)
        plot_widget.addItem(marker_a, ignoreBounds=True)
        plot_widget.addItem(marker_b, ignoreBounds=True)
        plot_widget.addItem(track_marker, ignoreBounds=True)

        delta_label = pg.TextItem(anchor=(1, 0), color=(230, 230, 230))
        track_label = pg.TextItem(anchor=(0, 1), color=(80, 170, 255))
        plot_widget.addItem(delta_label, ignoreBounds=True)
        plot_widget.addItem(track_label, ignoreBounds=True)

        cursor_dict = {
            "v_line_a": v_line_a,
            "v_line_b": v_line_b,
            "h_line_a": h_line_a,
            "h_line_b": h_line_b,
            "track_v": track_v,
            "track_h": track_h,
            "marker_a": marker_a,
            "marker_b": marker_b,
            "track_marker": track_marker,
            "delta_label": delta_label,
            "track_label": track_label,
            "curve": curve,
            "plot_widget": plot_widget,
            "readout_label": None,
            "checkbox": None,
            "mode_combo": None,
            "mode": "Vertical",
            "enabled": False,
            "track_point": None,
        }

        v_line_a.sigPositionChanged.connect(lambda: self.sync_cursor_to_data(cursor_dict, "vertical_a"))
        v_line_b.sigPositionChanged.connect(lambda: self.sync_cursor_to_data(cursor_dict, "vertical_b"))
        h_line_a.sigPositionChanged.connect(lambda: self.sync_cursor_to_data(cursor_dict, "horizontal_a"))
        h_line_b.sigPositionChanged.connect(lambda: self.sync_cursor_to_data(cursor_dict, "horizontal_b"))

        proxy = pg.SignalProxy(
            plot_widget.scene().sigMouseMoved,
            rateLimit=60,
            slot=lambda evt: self.update_track_cursor(cursor_dict, evt)
        )
        cursor_dict["proxy"] = proxy

        self.set_cursor_visible(cursor_dict, False)
        return cursor_dict

    def attach_cursor_controls(self, cursor_dict, checkbox, mode_combo, readout_label):
        cursor_dict["checkbox"] = checkbox
        cursor_dict["mode_combo"] = mode_combo
        cursor_dict["readout_label"] = readout_label

        checkbox.toggled.connect(lambda checked: self.set_cursor_visible(cursor_dict, checked))
        mode_combo.currentTextChanged.connect(lambda _: self.on_cursor_mode_changed(cursor_dict))

        self.set_cursor_visible(cursor_dict, checkbox.isChecked())
        self.on_cursor_mode_changed(cursor_dict)

    def get_valid_curve_data(self, curve):
        x_data, y_data = curve.getData()

        if x_data is None or y_data is None:
            return None, None
        if len(x_data) == 0 or len(y_data) == 0:
            return None, None

        x_arr = np.asarray(x_data)
        y_arr = np.asarray(y_data)
        valid = np.isfinite(x_arr) & np.isfinite(y_arr)

        if not np.any(valid):
            return None, None

        return x_arr[valid], y_arr[valid]

    def format_cursor_value(self, value):
        if value == 0:
            return "0"

        abs_value = abs(value)
        if 1e-3 <= abs_value < 1e4:
            return f"{value:.4f}".rstrip("0").rstrip(".")

        exponent = int(np.floor(np.log10(abs_value)))
        mantissa = value / (10 ** exponent)
        superscript_map = str.maketrans("0123456789-", "⁰¹²³⁴⁵⁶⁷⁸⁹⁻")
        exponent_text = str(exponent).translate(superscript_map)
        mantissa_text = f"{mantissa:.4f}".rstrip("0").rstrip(".")
        return f"{mantissa_text}×10{exponent_text}"

    def get_vertical_measurements(self, cursor_dict):
        x_arr, y_arr = self.get_valid_curve_data(cursor_dict["curve"])
        if x_arr is None:
            return None

        idx_a = int(np.argmin(np.abs(x_arr - cursor_dict["v_line_a"].value())))
        idx_b = int(np.argmin(np.abs(x_arr - cursor_dict["v_line_b"].value())))

        x1 = float(x_arr[idx_a])
        y1 = float(y_arr[idx_a])
        x2 = float(x_arr[idx_b])
        y2 = float(y_arr[idx_b])

        return {
            "x1": x1,
            "y1": y1,
            "x2": x2,
            "y2": y2,
            "dx": x2 - x1,
            "dy": y2 - y1,
        }

    def get_horizontal_measurements(self, cursor_dict):
        x_arr, y_arr = self.get_valid_curve_data(cursor_dict["curve"])
        if x_arr is None:
            return None

        y1 = float(cursor_dict["h_line_a"].value())
        y2 = float(cursor_dict["h_line_b"].value())
        x_center = float(x_arr[len(x_arr) // 2])

        return {
            "x": x_center,
            "y1": y1,
            "y2": y2,
            "dy": y2 - y1,
        }

    def get_track_measurement(self, cursor_dict):
        return cursor_dict.get("track_point")

    def on_cursor_mode_changed(self, cursor_dict):
        mode_combo = cursor_dict.get("mode_combo")
        cursor_dict["mode"] = mode_combo.currentText() if mode_combo is not None else "Vertical"
        if cursor_dict["enabled"]:
            self.reset_cursor_positions(cursor_dict)
        self.refresh_cursor_readout(cursor_dict)

    def reset_cursor_positions(self, cursor_dict):
        x_arr, y_arr = self.get_valid_curve_data(cursor_dict["curve"])
        if x_arr is None:
            cursor_dict["track_point"] = None
            return

        mode = cursor_dict["mode"]
        quarter_idx = len(x_arr) // 4
        three_quarter_idx = (len(x_arr) * 3) // 4

        if mode == "Vertical":
            cursor_dict["v_line_a"].blockSignals(True)
            cursor_dict["v_line_b"].blockSignals(True)
            cursor_dict["v_line_a"].setPos(float(x_arr[quarter_idx]))
            cursor_dict["v_line_b"].setPos(float(x_arr[three_quarter_idx]))
            cursor_dict["v_line_a"].blockSignals(False)
            cursor_dict["v_line_b"].blockSignals(False)
        elif mode == "Horizontal":
            y_min = float(np.min(y_arr))
            y_max = float(np.max(y_arr))
            y_span = y_max - y_min
            if y_span <= 0:
                y_span = max(abs(y_max), 1.0)
            y_a = y_min + 0.35 * y_span
            y_b = y_min + 0.65 * y_span
            cursor_dict["h_line_a"].blockSignals(True)
            cursor_dict["h_line_b"].blockSignals(True)
            cursor_dict["h_line_a"].setPos(y_a)
            cursor_dict["h_line_b"].setPos(y_b)
            cursor_dict["h_line_a"].blockSignals(False)
            cursor_dict["h_line_b"].blockSignals(False)
        else:
            mid_idx = len(x_arr) // 2
            cursor_dict["track_point"] = {
                "x": float(x_arr[mid_idx]),
                "y": float(y_arr[mid_idx]),
            }

    def sync_cursor_to_data(self, cursor_dict, cursor_name):
        mode = cursor_dict["mode"]
        if mode == "Vertical":
            measurements = self.get_vertical_measurements(cursor_dict)
            if measurements is None:
                return

            line_key = "v_line_a" if cursor_name == "vertical_a" else "v_line_b"
            snap_key = "x1" if cursor_name == "vertical_a" else "x2"
            line = cursor_dict[line_key]
            line.blockSignals(True)
            line.setPos(measurements[snap_key])
            line.blockSignals(False)
        elif mode == "Horizontal":
            line_key = "h_line_a" if cursor_name == "horizontal_a" else "h_line_b"
            line = cursor_dict[line_key]
            line.blockSignals(True)
            line.setPos(float(line.value()))
            line.blockSignals(False)

        self.refresh_cursor_readout(cursor_dict)

    def update_track_cursor(self, cursor_dict, evt):
        if not cursor_dict["enabled"] or cursor_dict["mode"] != "Track":
            return

        pos = evt[0]
        plot_widget = cursor_dict["plot_widget"]
        if not plot_widget.sceneBoundingRect().contains(pos):
            return

        x_arr, y_arr = self.get_valid_curve_data(cursor_dict["curve"])
        if x_arr is None:
            cursor_dict["track_point"] = None
            self.refresh_cursor_readout(cursor_dict)
            return

        mouse_point = plot_widget.plotItem.vb.mapSceneToView(pos)
        idx = int(np.argmin(np.abs(x_arr - mouse_point.x())))
        cursor_dict["track_point"] = {
            "x": float(x_arr[idx]),
            "y": float(y_arr[idx]),
        }
        self.refresh_cursor_readout(cursor_dict)

    def refresh_cursor_readout(self, cursor_dict, label_widget=None):
        if label_widget is not None:
            cursor_dict["readout_label"] = label_widget
        else:
            label_widget = cursor_dict.get("readout_label")

        visible = cursor_dict["enabled"]
        mode = cursor_dict["mode"]

        for item_name in (
            "v_line_a", "v_line_b", "h_line_a", "h_line_b",
            "track_v", "track_h", "delta_label", "track_label"
        ):
            cursor_dict[item_name].setVisible(False)
        for marker_name in ("marker_a", "marker_b", "track_marker"):
            cursor_dict[marker_name].setVisible(False)

        if label_widget is not None:
            label_widget.setVisible(visible)

        if not visible:
            if label_widget is not None:
                label_widget.setText("")
            return

        x_arr, y_arr = self.get_valid_curve_data(cursor_dict["curve"])
        if x_arr is None:
            if label_widget is not None:
                label_widget.setText("Cursor: waiting for data")
            return

        if mode == "Vertical":
            measurements = self.get_vertical_measurements(cursor_dict)
            if measurements is None:
                return

            x1 = measurements["x1"]
            y1 = measurements["y1"]
            x2 = measurements["x2"]
            y2 = measurements["y2"]
            dx = measurements["dx"]
            dy = measurements["dy"]

            cursor_dict["v_line_a"].setVisible(True)
            cursor_dict["v_line_b"].setVisible(True)
            cursor_dict["marker_a"].setVisible(True)
            cursor_dict["marker_b"].setVisible(True)
            cursor_dict["marker_a"].setData([x1], [y1])
            cursor_dict["marker_b"].setData([x2], [y2])
            cursor_dict["delta_label"].setVisible(True)
            cursor_dict["delta_label"].setPos(max(x1, x2), max(y1, y2))
            cursor_dict["delta_label"].setText(
                f"A: ({self.format_cursor_value(x1)}, {self.format_cursor_value(y1)})\n"
                f"B: ({self.format_cursor_value(x2)}, {self.format_cursor_value(y2)})\n"
                f"dX={self.format_cursor_value(dx)}  dY={self.format_cursor_value(dy)}"
            )

            if label_widget is not None:
                inv_dx_text = ""
                if abs(dx) > 1e-12:
                    inv_dx_text = f"  1/dX={self.format_cursor_value(1.0 / dx)}"
                label_widget.setText(
                    "Vertical A "
                    f"({self.format_cursor_value(x1)}, {self.format_cursor_value(y1)})   "
                    "Vertical B "
                    f"({self.format_cursor_value(x2)}, {self.format_cursor_value(y2)})   "
                    f"dX={self.format_cursor_value(dx)}{inv_dx_text}   "
                    f"dY={self.format_cursor_value(dy)}"
                )
        elif mode == "Horizontal":
            measurements = self.get_horizontal_measurements(cursor_dict)
            if measurements is None:
                return

            y1 = measurements["y1"]
            y2 = measurements["y2"]
            dy = measurements["dy"]
            x_pos = measurements["x"]

            cursor_dict["h_line_a"].setVisible(True)
            cursor_dict["h_line_b"].setVisible(True)
            cursor_dict["delta_label"].setVisible(True)
            cursor_dict["delta_label"].setPos(x_pos, max(y1, y2))
            cursor_dict["delta_label"].setText(
                f"A: y={self.format_cursor_value(y1)}\n"
                f"B: y={self.format_cursor_value(y2)}\n"
                f"dY={self.format_cursor_value(dy)}"
            )

            if label_widget is not None:
                label_widget.setText(
                    f"Horizontal A y={self.format_cursor_value(y1)}   "
                    f"Horizontal B y={self.format_cursor_value(y2)}   "
                    f"dY={self.format_cursor_value(dy)}"
                )
        else:
            track = self.get_track_measurement(cursor_dict)
            if track is None:
                self.reset_cursor_positions(cursor_dict)
                track = self.get_track_measurement(cursor_dict)
                if track is None:
                    if label_widget is not None:
                        label_widget.setText("Track: waiting for data")
                    return

            x = track["x"]
            y = track["y"]
            cursor_dict["track_v"].setVisible(True)
            cursor_dict["track_h"].setVisible(True)
            cursor_dict["track_v"].setPos(x)
            cursor_dict["track_h"].setPos(y)
            cursor_dict["track_marker"].setVisible(True)
            cursor_dict["track_marker"].setData([x], [y])
            cursor_dict["track_label"].setVisible(True)
            cursor_dict["track_label"].setPos(x, y)
            cursor_dict["track_label"].setText(
                f"x={self.format_cursor_value(x)}\ny={self.format_cursor_value(y)}"
            )

            if label_widget is not None:
                label_widget.setText(
                    f"Track x={self.format_cursor_value(x)}   y={self.format_cursor_value(y)}"
                )

    def set_cursor_visible(self, cursor_dict, visible):
        if cursor_dict is None:
            return

        cursor_dict["enabled"] = visible
        if visible:
            self.reset_cursor_positions(cursor_dict)
        self.refresh_cursor_readout(cursor_dict)

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
        self.refresh_cursor_readout(self.cursor1)
        self.refresh_cursor_readout(self.cursor2)
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
                "cursor1": self.ext_cursor1,
                "cursor2": self.ext_cursor2,
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
                "cursor1": self.cursor1,
                "cursor2": self.cursor2,
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
        cursor1 = w["cursor1"]
        cursor2 = w["cursor2"]

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
        self.refresh_cursor_readout(cursor1)

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
        self.refresh_cursor_readout(cursor2)

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
