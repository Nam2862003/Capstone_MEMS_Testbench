from PyQt6.QtWidgets import (
    QFormLayout, QLineEdit, QSizePolicy, QSpacerItem, QWidget, QVBoxLayout, QTabWidget,
    QLabel, QPushButton, QComboBox, QApplication,
    QGroupBox, QGridLayout, QHBoxLayout, QCheckBox, QMessageBox, QStackedWidget, QToolButton, QMenu, QSlider
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIntValidator, QAction

import time

import pyqtgraph as pg
import numpy as np
from lib.lock_in_amplifier import lock_in_amplifier
from lib.fast_fourier_transform import fft_amplitude_phase
from lib.root_mean_square import compute_rms_amplitude


class BaseDAQPage(QWidget):
    ALL_ADC_RESOLUTIONS = ["10-bit", "12-bit", "14-bit", "16-bit"]
    H7S_ADC_RESOLUTIONS = ["10-bit", "12-bit"]
    DEFAULT_SAMPLING_RATE = "2500000"
    DEFAULT_BUFFER_SIZE = "4096"
    DEFAULT_ADC_RESOLUTION = "16-bit"
    DEFAULT_CONSTANT_FREQ = "1000"
    DEFAULT_EXTERNAL_REF_FREQ = "1000"
    DEFAULT_START_FREQ = "10"
    DEFAULT_STOP_FREQ = "100000"
    DEFAULT_STEP_FREQ = "500"
    DEFAULT_ACTUATOR = "STM32 DAC Output"
    DEFAULT_OUTPUT_MODE = "Frequency Sweep"
    DEFAULT_MEASUREMENT_METHOD = "Root Mean Square (RMS)"

    def __init__(self, receiver, sender, usb_receiver=None, usb_sender=None):

        super().__init__()

        self.udp_receiver = receiver
        self.udp_sender = sender
        self.usb_receiver = usb_receiver
        self.usb_sender = usb_sender
        self.receiver = receiver
        self.sender = sender
        self.connected_transport = None

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
        self.selected_actuator = self.DEFAULT_ACTUATOR
        self.selected_output_mode = self.DEFAULT_OUTPUT_MODE
        self.time_offset_1 = 0
        self.time_offset_2 = 0
        self.adc_running = False
        self.external_freq_tolerance_hz = 50.0
        self.detected_board = None

        self.build_setup_tab()
        self.build_sweep_tab()
        self.build_external_tab()
        # self.receiver.set_resolution(self.resolution.currentText())
        # Update timer
        self.timer = pg.QtCore.QTimer()
        self.timer.timeout.connect(self.update_plot)
        self.timer.start(30)

        self.comm_timer = pg.QtCore.QTimer()
        self.comm_timer.timeout.connect(self.update_comm_status)
        self.comm_timer.start(500)
    # ============================================
    # 1. SETUP TAB
    # ============================================
    def build_setup_tab(self):
        layout = QVBoxLayout()
        # =========================
        # 1.1 ADC SETTINGS
        # =========================

        # Sampling rate
        self.adc_group = QGroupBox("Signal Acquisition (ADC)")
        adc_layout = QFormLayout()
        self.sampling_rate_input = QLineEdit(self.DEFAULT_SAMPLING_RATE)
        adc_layout.addRow("Sampling Rate (Hz):", self.sampling_rate_input)

        # Buffer size
        self.buffer = QComboBox()
        self.buffer.addItems(["512", "1024", "2048", "4096", "8192", "16384"])
        self.buffer.setCurrentText(self.DEFAULT_BUFFER_SIZE)
        adc_layout.addRow("Buffer Size:", self.buffer)

        #Resolution (optional, for display purposes only)
        self.resolution = QComboBox()
        self.resolution.addItems(self.ALL_ADC_RESOLUTIONS)
        self.resolution.setCurrentText(self.DEFAULT_ADC_RESOLUTION)
        adc_layout.addRow("ADC Resolution:", self.resolution)
        

        # Control buttons
        button_layout = QGridLayout()
        self.start_adc=QPushButton("Start ADC")
        self.stop_adc=QPushButton("Stop ADC")
        button_layout.addWidget(self.start_adc, 0, 1)
        button_layout.addWidget(self.stop_adc, 0, 2)
        adc_layout.addRow(button_layout)
        self.adc_group.setLayout(adc_layout)
        self.adc_group.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)
        # =========================
        # 1.2 DAC SETTINGS
        # =========================

        # DAC frequency
        self.dac_group = QGroupBox("Signal Generation (DAC)")
        dac_layout = QFormLayout()
        # self.dac_freq_input = QLineEdit("1000")  # 1 kHz default
        # dac_layout.addRow("Frequency (Hz):", self.dac_freq_input)
        # Frequency inputs
        self.constant_freq = QLineEdit(self.DEFAULT_CONSTANT_FREQ)
        self.external_ref_freq = QLineEdit(self.DEFAULT_EXTERNAL_REF_FREQ)
        self.start_freq = QLineEdit(self.DEFAULT_START_FREQ)
        self.stop_freq = QLineEdit(self.DEFAULT_STOP_FREQ)
        self.step_freq = QLineEdit(self.DEFAULT_STEP_FREQ)

        self.frequency_stack = QStackedWidget()

        constant_page = QWidget()
        constant_layout = QHBoxLayout()
        constant_layout.setContentsMargins(0, 0, 0, 0)
        constant_layout.addWidget(self.constant_freq)
        constant_page.setLayout(constant_layout)
        constant_page.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        external_ref_page = QWidget()
        external_ref_layout = QHBoxLayout()
        external_ref_layout.setContentsMargins(0, 0, 0, 0)
        self.auto_ref_freq_checkbox = QCheckBox("Auto")
        self.auto_ref_freq_checkbox.setChecked(False)
        external_ref_layout.addWidget(self.external_ref_freq)
        external_ref_layout.addWidget(self.auto_ref_freq_checkbox)
        external_ref_page.setLayout(external_ref_layout)
        external_ref_page.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        sweep_page = QWidget()
        sweep_layout = QHBoxLayout()
        sweep_layout.setContentsMargins(0, 0, 0, 0)
        sweep_layout.addWidget(self.start_freq)
        sweep_layout.addWidget(QLabel("to"))
        sweep_layout.addWidget(self.stop_freq)
        sweep_layout.addWidget(QLabel("Step:"))
        sweep_layout.addWidget(self.step_freq)
        sweep_page.setLayout(sweep_layout)
        sweep_page.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        self.frequency_stack.addWidget(constant_page)
        self.frequency_stack.addWidget(external_ref_page)
        self.frequency_stack.addWidget(sweep_page)
        self.frequency_stack.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        dac_layout.addRow("Frequency (Hz):", self.frequency_stack)

        # Actuator / mode menu field
        self.actuator_field = QWidget()
        self.actuator_field.setObjectName("ActuatorField")
        self.actuator_field.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        actuator_field_layout = QHBoxLayout()
        actuator_field_layout.setContentsMargins(0, 0, 0, 0)
        actuator_field_layout.setSpacing(0)
        self.actuator_display = QLabel(self.selected_actuator)
        self.actuator_display.setObjectName("ActuatorDisplay")
        self.actuator_display.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
        self.actuator_arrow = QToolButton()
        self.actuator_arrow.setObjectName("ActuatorArrow")
        self.actuator_arrow.setArrowType(Qt.ArrowType.DownArrow)
        actuator_field_layout.addWidget(self.actuator_display, 1)
        actuator_field_layout.addWidget(self.actuator_arrow, 0)
        self.actuator_field.setLayout(actuator_field_layout)

        self.actuator_menu = QMenu(self.actuator_field)
        self.actuator_field.mousePressEvent = self.show_actuator_menu
        self.actuator_display.mousePressEvent = self.show_actuator_menu
        self.actuator_arrow.clicked.connect(lambda: self.show_actuator_menu(None))
        self.build_actuator_menu()
        dac_layout.addRow("Actuator:", self.actuator_field)

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
        self.dac_group.setLayout(dac_layout)
        self.dac_group.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)

        # =========================
        # 1.3 COMMUNICATION SETTINGS
        # =========================

        comm_group = QGroupBox("Communication Settings")
        comm_layout = QVBoxLayout()

        compact_field_width = 240
        compact_button_width = 140
        comm_label_width = 170

        def make_comm_label(text):
            label = QLabel(text)
            label.setFixedWidth(comm_label_width)
            return label

        self.transport_selector = QComboBox()
        self.transport_selector.addItems(["Ethernet (UDP)", "HS USB"])
        self.transport_selector.setFixedWidth(compact_field_width)
        top_comm_form = QFormLayout()
        top_comm_form.setContentsMargins(0, 0, 0, 0)
        top_comm_form.setHorizontalSpacing(8)
        top_comm_form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

        transport_row = QHBoxLayout()
        transport_row.setContentsMargins(0, 0, 0, 0)
        transport_row.setSpacing(8)
        transport_row.addWidget(self.transport_selector, 0, Qt.AlignmentFlag.AlignLeft)
        transport_row.addStretch()
        top_comm_form.addRow(make_comm_label("Communication Type:"), transport_row)

        board_row = QHBoxLayout()
        board_row.setContentsMargins(0, 0, 0, 0)
        board_row.setSpacing(8)
        self.detected_board_label = QLineEdit("No device detected yet")
        self.detected_board_label.setReadOnly(True)
        self.detected_board_label.setFixedWidth(compact_field_width)
        board_row.addWidget(self.detected_board_label, 0, Qt.AlignmentFlag.AlignLeft)
        self.detect_board_btn = QPushButton("Detect Board")
        self.detect_board_btn.setFixedWidth(compact_button_width)
        board_row.addWidget(self.detect_board_btn, 0, Qt.AlignmentFlag.AlignLeft)
        board_row.addStretch()
        top_comm_form.addRow(make_comm_label("Board:"), board_row)
        comm_layout.addLayout(top_comm_form)

        self.comm_stack = QStackedWidget()

        ethernet_page = QWidget()
        ethernet_layout = QVBoxLayout()
        ethernet_layout.setContentsMargins(0, 0, 0, 0)
        ethernet_layout.setSpacing(8)
        comm_form = QFormLayout()
        comm_form.setContentsMargins(0, 0, 0, 0)
        comm_form.setHorizontalSpacing(8)
        comm_form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

        self.target_ip_input = QLineEdit(self.sender.ip)
        self.target_ip_input.setFixedWidth(compact_field_width)
        comm_form.addRow(make_comm_label("Board IP:"), self.target_ip_input)

        self.local_ip_input = QLineEdit(self.receiver.display_host)
        self.local_ip_input.setFixedWidth(compact_field_width)
        comm_form.addRow(make_comm_label("PC IP:"), self.local_ip_input)

        self.command_port_input = QLineEdit(str(self.sender.port))
        self.command_port_input.setValidator(QIntValidator(1, 65535, self))
        self.command_port_input.setFixedWidth(compact_field_width)
        comm_form.addRow(make_comm_label("Command Port:"), self.command_port_input)

        self.data_port_input = QLineEdit(str(self.receiver.port))
        self.data_port_input.setValidator(QIntValidator(1, 65535, self))
        self.data_port_input.setFixedWidth(compact_field_width)
        comm_form.addRow(make_comm_label("Data Port:"), self.data_port_input)

        self.comm_status_label = QLabel()
        self.comm_status_label.setWordWrap(True)
        comm_form.addRow(make_comm_label("Status:"), self.comm_status_label)

        comm_button_row = QHBoxLayout()
        self.connect_comm_btn = QPushButton("Connect")
        self.disconnect_comm_btn = QPushButton("Disconnect")
        comm_button_row.addWidget(self.connect_comm_btn)
        comm_button_row.addWidget(self.disconnect_comm_btn)

        ethernet_layout.addLayout(comm_form)
        ethernet_layout.addLayout(comm_button_row)
        ethernet_page.setLayout(ethernet_layout)

        usb_page = QWidget()
        usb_layout = QVBoxLayout()
        usb_layout.setContentsMargins(0, 0, 0, 0)
        usb_layout.setSpacing(8)
        usb_form = QFormLayout()
        usb_form.setContentsMargins(0, 0, 0, 0)
        usb_form.setHorizontalSpacing(8)
        usb_form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        
        # USB COM Port selector
        self.usb_port_input = QComboBox()
        self.usb_port_input.addItems(["COM3", "COM4", "COM5", "COM6", "COM7", "COM8", "COM9"])
        self.usb_port_input.setEditable(True)
        self.usb_port_input.setFixedWidth(compact_field_width)
        self.usb_refresh_ports_btn = QPushButton("Refresh Ports")
        self.usb_refresh_ports_btn.setFixedWidth(compact_button_width)
        port_row = QHBoxLayout()
        port_row.setContentsMargins(0, 0, 0, 0)
        port_row.setSpacing(8)
        port_row.addWidget(self.usb_port_input, 0, Qt.AlignmentFlag.AlignLeft)
        port_row.addWidget(self.usb_refresh_ports_btn, 0, Qt.AlignmentFlag.AlignLeft)
        port_row.addStretch()
        usb_form.addRow(make_comm_label("COM Port:"), port_row)
        
        # USB Baudrate
        self.usb_baudrate_input = QLineEdit("115200")
        self.usb_baudrate_input.setFixedWidth(compact_field_width)
        baudrate_row = QHBoxLayout()
        baudrate_row.setContentsMargins(0, 0, 0, 0)
        baudrate_row.setSpacing(8)
        baudrate_row.addWidget(self.usb_baudrate_input, 0, Qt.AlignmentFlag.AlignLeft)
        baudrate_row.addStretch()
        usb_form.addRow(make_comm_label("Baudrate (bps):"), baudrate_row)
        
        # USB Status
        self.usb_status_label = QLabel("Not connected")
        self.usb_status_label.setWordWrap(True)
        usb_form.addRow(make_comm_label("Status:"), self.usb_status_label)
        
        # USB Control buttons
        usb_button_row = QHBoxLayout()
        self.usb_connect_btn = QPushButton("Connect")
        self.usb_disconnect_btn = QPushButton("Disconnect")
        usb_button_row.addWidget(self.usb_connect_btn)
        usb_button_row.addWidget(self.usb_disconnect_btn)
        usb_form.addRow(usb_button_row)
        
        usb_layout.addLayout(usb_form)
        usb_layout.addStretch()
        usb_page.setLayout(usb_layout)

        self.comm_stack.addWidget(ethernet_page)
        self.comm_stack.addWidget(usb_page)
        comm_layout.addWidget(self.comm_stack)

        comm_group.setLayout(comm_layout)
        comm_group.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)

        # =========================
        # 1.4 ADD TO MAIN LAYOUT
        # =========================
        # Horizontal layout for ADC and DAC groups
        # layout.addWidget(adc_group)
        # layout.addWidget(dac_group)
        # self.setup.setLayout(layout)

        # Vertical layout for ADC and DAC groups
        main_row = QHBoxLayout()
        main_row.setAlignment(Qt.AlignmentFlag.AlignTop)
        main_row.addWidget(self.adc_group, 1, alignment=Qt.AlignmentFlag.AlignTop)
        main_row.addWidget(self.dac_group, 1, alignment=Qt.AlignmentFlag.AlignTop)
        layout.addLayout(main_row)
        for extra_group in self.build_setup_extension_groups():
            layout.addWidget(extra_group)

        comm_sidebar_group = self.build_setup_sidebar_group()
        if comm_sidebar_group is not None:
            layout.addSpacing(24)
            bottom_row = QHBoxLayout()
            bottom_row.setAlignment(Qt.AlignmentFlag.AlignTop)
            bottom_row.addWidget(comm_group, 1, alignment=Qt.AlignmentFlag.AlignTop)
            bottom_row.addWidget(comm_sidebar_group, 1, alignment=Qt.AlignmentFlag.AlignTop)
            layout.addLayout(bottom_row)
        else:
            layout.addSpacing(24)
            layout.addWidget(comm_group)
        layout.addStretch()
        self.setup.setLayout(layout)

        # connections
        self.buffer.currentTextChanged.connect(self.set_buffer)
        self.start_adc.clicked.connect(self.start_acquisition)
        self.stop_adc.clicked.connect(self.stop_acquisition)
        self.sampling_rate_input.editingFinished.connect(self.set_sampling_rate)
        self.resolution.currentTextChanged.connect(self.set_resolution)
        self.start_dac.clicked.connect(self.start_generation)
        self.stop_dac.clicked.connect(self.stop_generation)
        self.connect_comm_btn.clicked.connect(self.connect_transport)
        self.disconnect_comm_btn.clicked.connect(self.disconnect_transport)
        self.usb_connect_btn.clicked.connect(self.connect_transport)
        self.usb_disconnect_btn.clicked.connect(self.disconnect_transport)
        self.transport_selector.currentIndexChanged.connect(self.update_transport_panel)
        self.detect_board_btn.clicked.connect(lambda: self.detect_board())
        self.auto_ref_freq_checkbox.toggled.connect(self.update_actuator)
        self.usb_refresh_ports_btn.clicked.connect(self.refresh_usb_ports)
        #Reset sweep data when frequency changes
        # self.dac_freq_input.editingFinished.connect(self.on_freq_changed)
        self.update_actuator()
        self.set_signal_controls_enabled(False)
        self.update_transport_panel()
        self.update_comm_status()

    def build_setup_extension_groups(self):
        return []

    def build_setup_sidebar_group(self):
        return None
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
        self.cursor_checkbox1.setChecked(False)
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
        self.cursor_checkbox2.setChecked(False)
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
        self.ext_cursor_checkbox1.setChecked(False)
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
        self.ext_cursor_checkbox2.setChecked(False)
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

    def validate_comm_settings(self):
        board_ip = self.target_ip_input.text().strip()
        local_ip = self.local_ip_input.text().strip()
        cmd_port_text = self.command_port_input.text().strip()
        data_port_text = self.data_port_input.text().strip()

        if not board_ip:
            raise ValueError("Board IP cannot be empty.")
        if not local_ip:
            raise ValueError("PC IP cannot be empty.")
        if not cmd_port_text or not data_port_text:
            raise ValueError("Command port and data port are required.")

        return board_ip, local_ip, int(cmd_port_text), int(data_port_text)

    def get_parent_receiver(self, transport_type):
        """Get the appropriate receiver from parent window"""
        if transport_type == "udp" and getattr(self, "udp_receiver", None) is not None:
            return self.udp_receiver
        if transport_type == "usb" and getattr(self, "usb_receiver", None) is not None:
            return self.usb_receiver

        parent = self.parent()
        while parent:
            if hasattr(parent, 'udp_receiver') and hasattr(parent, 'usb_receiver'):
                if transport_type == "udp":
                    return parent.udp_receiver
                elif transport_type == "usb":
                    return parent.usb_receiver
            parent = parent.parent()
        raise RuntimeError(f"Could not find parent with {transport_type} receiver")

    def get_parent_sender(self, transport_type):
        """Get the appropriate sender from parent window"""
        if transport_type == "udp" and getattr(self, "udp_sender", None) is not None:
            return self.udp_sender
        if transport_type == "usb" and getattr(self, "usb_sender", None) is not None:
            return self.usb_sender

        parent = self.parent()
        while parent:
            if transport_type == "udp" and hasattr(parent, "udp_sender"):
                return parent.udp_sender
            if transport_type == "usb" and hasattr(parent, "usb_sender"):
                return parent.usb_sender
            parent = parent.parent()
        raise RuntimeError(f"Could not find parent with {transport_type} sender")

    def refresh_usb_ports(self):
        """Refresh available USB COM ports"""
        try:
            from network.usb_receiver import USBReceiver
            available_ports = USBReceiver.available_ports()
            
            current_port = self.usb_port_input.currentText()
            self.usb_port_input.clear()
            
            if available_ports:
                self.usb_port_input.addItems(available_ports)
                if current_port in available_ports:
                    self.usb_port_input.setCurrentText(current_port)
                QMessageBox.information(self, "USB Ports", f"Found {len(available_ports)} COM port(s)")
            else:
                self.usb_port_input.addItem("No ports found")
                QMessageBox.warning(self, "USB Ports", "No COM ports found")
        except Exception as e:
            QMessageBox.warning(self, "USB Port Error", f"Error refreshing ports: {str(e)}")

    def update_transport_panel(self):
        transport_name = self.transport_selector.currentText()
        selected_transport = "usb" if transport_name == "HS USB" else "udp"
        if self.connected_transport is not None and self.connected_transport != selected_transport:
            self.disconnect_connected_transport(reset_outputs=True)

        if transport_name == "Ethernet (UDP)":
            self.receiver = self.get_parent_receiver("udp")
            self.sender = self.get_parent_sender("udp")
            self.comm_stack.setCurrentIndex(0)
        else:
            self.receiver = self.get_parent_receiver("usb")
            self.sender = self.get_parent_sender("usb")
            self.comm_stack.setCurrentIndex(1)

        self.update_comm_status()

    def active_transport_key(self):
        if not hasattr(self, "transport_selector"):
            return "udp"
        if self.transport_selector.currentText() == "HS USB":
            return "usb"
        return "udp"

    def active_transport_is_connected(self):
        return self.connected_transport == self.active_transport_key()

    def set_signal_controls_enabled(self, enabled):
        self.signal_controls_enabled = enabled

        if hasattr(self, "adc_group"):
            self.adc_group.setEnabled(enabled)
        if hasattr(self, "dac_group"):
            self.dac_group.setEnabled(enabled)

        if enabled:
            self.update_actuator()
        else:
            if hasattr(self, "tabs"):
                self.tabs.setTabEnabled(1, False)
                self.tabs.setTabEnabled(2, False)
                if self.tabs.currentIndex() in (1, 2):
                    self.tabs.setCurrentIndex(0)

    def sync_board_transport_mode(self):
        if not hasattr(self, "sender") or not self.active_transport_is_connected():
            return
        self.sender.sync_board_mode()

    def set_combo_text_silently(self, combo, text):
        combo.blockSignals(True)
        combo.setCurrentText(text)
        combo.blockSignals(False)

    def set_checkbox_silently(self, checkbox, checked):
        checkbox.blockSignals(True)
        checkbox.setChecked(checked)
        checkbox.blockSignals(False)

    def reset_transport_stats(self):
        for endpoint in (self.udp_sender, self.usb_sender, self.udp_receiver, self.usb_receiver):
            if endpoint is not None and hasattr(endpoint, "reset_stats"):
                endpoint.reset_stats()

    def reset_status_labels(self):
        if hasattr(self, "comm_status_label"):
            self.comm_status_label.setText("Not connected")
        if hasattr(self, "usb_status_label"):
            self.usb_status_label.setText("Not connected")

    def reset_gui_defaults(self):
        self.detected_board = None
        if hasattr(self, "detected_board_label"):
            self.detected_board_label.setText("No device detected yet")
        if hasattr(self, "transport_selector"):
            self.set_hs_usb_enabled(True)

        self.selected_actuator = self.DEFAULT_ACTUATOR
        self.selected_output_mode = self.DEFAULT_OUTPUT_MODE
        self._refresh_actuator_menu_state()

        if hasattr(self, "sampling_rate_input"):
            self.sampling_rate_input.setText(self.DEFAULT_SAMPLING_RATE)
        if hasattr(self, "buffer"):
            self.set_combo_text_silently(self.buffer, self.DEFAULT_BUFFER_SIZE)
        if hasattr(self, "resolution"):
            self.set_resolution_choices(self.ALL_ADC_RESOLUTIONS, self.DEFAULT_ADC_RESOLUTION)
        if hasattr(self, "mode_selector"):
            self.set_combo_text_silently(self.mode_selector, self.DEFAULT_MEASUREMENT_METHOD)

        if hasattr(self, "constant_freq"):
            self.constant_freq.setText(self.DEFAULT_CONSTANT_FREQ)
        if hasattr(self, "external_ref_freq"):
            self.external_ref_freq.setText(self.DEFAULT_EXTERNAL_REF_FREQ)
        if hasattr(self, "start_freq"):
            self.start_freq.setText(self.DEFAULT_START_FREQ)
        if hasattr(self, "stop_freq"):
            self.stop_freq.setText(self.DEFAULT_STOP_FREQ)
        if hasattr(self, "step_freq"):
            self.step_freq.setText(self.DEFAULT_STEP_FREQ)
        if hasattr(self, "auto_ref_freq_checkbox"):
            self.set_checkbox_silently(self.auto_ref_freq_checkbox, False)

        if hasattr(self, "gain_slider"):
            self.gain_slider.blockSignals(True)
            self.gain_slider.setValue(0)
            self.gain_slider.blockSignals(False)
            self.update_gain_display(0)

        self.current_freq = None
        self.adc_running = False
        self.sweeping = False
        if hasattr(self, "tabs"):
            self.tabs.setCurrentIndex(0)
        if hasattr(self, "reset_sweep") and hasattr(self, "curve1"):
            self.reset_sweep()

        if hasattr(self.receiver, "set_buffer_size"):
            self.receiver.set_buffer_size(int(self.DEFAULT_BUFFER_SIZE))

        self.update_actuator()
        self.set_signal_controls_enabled(False)
        self.reset_transport_stats()
        self.reset_status_labels()

    def reset_sender_defaults(self, send_now=True):
        if send_now and hasattr(self.sender, "reset_outputs_to_default"):
            self.sender.reset_outputs_to_default()

        for sender in (self.udp_sender, self.usb_sender):
            if sender is not None:
                sender.set_board_mode("PE", send_now=False)
                sender.set_actuator_mode("STM32", send_now=False)
                if hasattr(sender, "set_pe_gain"):
                    sender.set_pe_gain(0, send_now=False)

        self.adc_running = False
        self.sweeping = False

    def disconnect_connected_transport(self, reset_outputs=True):
        transport = self.connected_transport
        if transport == "udp":
            self.receiver = self.get_parent_receiver("udp")
            self.sender = self.get_parent_sender("udp")
        elif transport == "usb":
            self.receiver = self.get_parent_receiver("usb")
            self.sender = self.get_parent_sender("usb")
        else:
            self.reset_sender_defaults(send_now=False)
            if reset_outputs:
                self.reset_gui_defaults()
            else:
                self.set_signal_controls_enabled(False)
            return

        if reset_outputs:
            self.reset_sender_defaults(send_now=True)
        else:
            self.adc_running = False
            self.sweeping = False

        self.sender.close()
        self.receiver.stop()
        self.connected_transport = None
        if reset_outputs:
            self.reset_gui_defaults()
        else:
            self.set_signal_controls_enabled(False)

    def set_hs_usb_enabled(self, enabled, reason=""):
        hs_usb_index = self.transport_selector.findText("HS USB")
        if hs_usb_index < 0:
            return

        item = self.transport_selector.model().item(hs_usb_index)
        if item is not None:
            item.setEnabled(enabled)
            item.setToolTip("" if enabled else reason)

        if hasattr(self, "usb_connect_btn"):
            self.usb_connect_btn.setEnabled(enabled)
        if hasattr(self, "usb_refresh_ports_btn"):
            self.usb_refresh_ports_btn.setEnabled(enabled)

        if not enabled and self.transport_selector.currentIndex() == hs_usb_index:
            ethernet_index = self.transport_selector.findText("Ethernet (UDP)")
            if ethernet_index >= 0:
                self.transport_selector.setCurrentIndex(ethernet_index)

    def set_resolution_choices(self, choices, default_resolution):
        current = self.resolution.currentText()
        target = current if current in choices else default_resolution
        existing = [self.resolution.itemText(index) for index in range(self.resolution.count())]

        self.resolution.blockSignals(True)
        if existing != choices:
            self.resolution.clear()
            self.resolution.addItems(choices)
        self.resolution.setCurrentText(target)
        self.resolution.blockSignals(False)

        self.receiver.set_resolution(target)

    def apply_board_detection(self, reply):
        normalized = "".join(reply.strip().upper().split()).replace("-", "_")
        self.detected_board_label.setText(reply.strip())

        if "H723ZG" in normalized:
            self.detected_board = "Nucleo H723ZG"
            self.set_hs_usb_enabled(False, "Nucleo H723ZG does not support HS USB.")
            self.set_resolution_choices(self.ALL_ADC_RESOLUTIONS, "16-bit")
        elif "H7S3L8" in normalized or "H7SL8" in normalized:
            self.detected_board = "Nucleo H7S3L8"
            self.set_hs_usb_enabled(True)
            self.set_resolution_choices(self.H7S_ADC_RESOLUTIONS, "12-bit")
        else:
            self.detected_board = reply.strip()
            self.set_hs_usb_enabled(True)
            self.set_resolution_choices(self.ALL_ADC_RESOLUTIONS, "16-bit")

    def detect_board(self):
        if not hasattr(self, "sender") or not hasattr(self, "receiver"):
            return

        self.detected_board_label.setText("Detecting...")
        QApplication.processEvents()

        if self.transport_selector.currentText() == "Ethernet (UDP)":
            try:
                self.receiver = self.get_parent_receiver("udp")
                self.sender = self.get_parent_sender("udp")
                board_ip, local_ip, cmd_port, data_port = self.validate_comm_settings()
                self.sender.configure(ip=board_ip, port=cmd_port)
                self.receiver.rebind(data_port, host=local_ip)
                self.receiver.start()
                self.sender.open()
            except Exception as exc:
                self.detected_board = None
                self.set_hs_usb_enabled(True)
                self.detected_board_label.setText(f"Detection setup error: {exc}")
                return
        else:
            try:
                was_running = self.adc_running
                usb_port = self.usb_port_input.currentText().strip()
                baudrate = self.usb_baudrate_input.text().strip()
                baudrate_value = int(baudrate)

                if not usb_port:
                    raise ValueError("USB COM port cannot be empty.")
                if not baudrate:
                    raise ValueError("Baudrate cannot be empty.")

                self.receiver = self.get_parent_receiver("usb")
                self.sender = self.get_parent_sender("usb")
                if hasattr(self.sender, "attach_receiver"):
                    self.sender.attach_receiver(self.receiver)

                if (self.receiver.port != usb_port) or (int(self.receiver.baudrate) != baudrate_value):
                    self.receiver.rebind(usb_port, baudrate=baudrate_value)
                self.sender.port = usb_port
                self.sender.baudrate = baudrate_value
                self.receiver.start()
                self.sender.open()

                if hasattr(self.sender, "stop_aq"):
                    self.sender.stop_aq()
                    self.adc_running = False
                    time.sleep(0.05)
            except Exception as exc:
                self.detected_board = None
                self.set_hs_usb_enabled(True)
                self.detected_board_label.setText(f"USB detect error: {exc}")
                return

        if hasattr(self.receiver, "clear_text_messages"):
            self.receiver.clear_text_messages()
        if hasattr(self.receiver, "clear_pending_bytes"):
            self.receiver.clear_pending_bytes()
        elif hasattr(self.receiver, "_rx"):
            self.receiver._rx.clear()

        if not self.sender.send("BOARD?"):
            self.detected_board = None
            self.set_hs_usb_enabled(True)
            self.detected_board_label.setText("No device detected yet")
            if self.transport_selector.currentText() == "HS USB" and 'was_running' in locals() and was_running:
                if not self.adc_running and self.sender.start_aq():
                    self.adc_running = True
            return

        deadline = time.time() + 2.0
        reply = None
        while time.time() < deadline:
            QApplication.processEvents()
            if hasattr(self.receiver, "get_text_message"):
                reply = self.receiver.get_text_message()
            if reply:
                break
            time.sleep(0.03)

        if reply:
            self.apply_board_detection(reply)
        else:
            self.detected_board = None
            self.set_hs_usb_enabled(True)
            self.detected_board_label.setText("No reply to BOARD? Check IP, ports, and flashed firmware.")

        if self.transport_selector.currentText() == "HS USB" and 'was_running' in locals() and was_running:
            if not self.adc_running and self.sender.start_aq():
                self.adc_running = True

    def build_actuator_menu(self):
        actuator_modes = {
            "Direct Digital Synthesis (DDS)": ["Constant Output", "Frequency Sweep"],
            "Function Generator": ["Constant Output", "Frequency Sweep"],
            "STM32 DAC Output": ["Constant Output", "Frequency Sweep"],
        }

        self.actuator_menu.clear()
        self.actuator_actions = {}
        for actuator_name, modes in actuator_modes.items():
            submenu = self.actuator_menu.addMenu(actuator_name)
            for mode_name in modes:
                action = QAction(mode_name, self)
                action.setCheckable(True)
                action.triggered.connect(
                    lambda checked=False, a=actuator_name, m=mode_name: self.select_actuator_mode(a, m)
                )
                submenu.addAction(action)
                self.actuator_actions[(actuator_name, mode_name)] = action

        self._refresh_actuator_menu_state()

    def select_actuator_mode(self, actuator_name, output_mode):
        self.selected_actuator = actuator_name
        self.selected_output_mode = output_mode
        self._refresh_actuator_menu_state()
        self.sync_actuator_transport_mode()
        if hasattr(self, "start_dac"):
            self.update_actuator()


    def _refresh_actuator_menu_state(self):
        if hasattr(self, "actuator_actions"):
            for (actuator_name, mode_name), action in self.actuator_actions.items():
                action.setChecked(
                    actuator_name == self.selected_actuator and mode_name == self.selected_output_mode
                )

        if hasattr(self, "actuator_display"):
            self.actuator_display.setText(self.selected_actuator)

        if hasattr(self, "actuator_field"):
            self.actuator_field.setToolTip(f"{self.selected_actuator} / {self.selected_output_mode}")

    def show_actuator_menu(self, event):
        if hasattr(self, "actuator_menu") and hasattr(self, "actuator_field"):
            self.actuator_menu.popup(self.actuator_field.mapToGlobal(self.actuator_field.rect().bottomLeft()))
        if event is not None:
            event.accept()

    def current_actuator(self):
        return self.selected_actuator

    def current_output_mode(self):
        return self.selected_output_mode

    def current_actuator_transport_mode(self):
        actuator = self.current_actuator()
        if actuator == "Function Generator":
            return "FG"
        if actuator == "STM32 DAC Output":
            return "STM32"
        return "DDS"

    def sync_actuator_transport_mode(self):
        if not hasattr(self, "sender"):
            return

        mode = self.current_actuator_transport_mode()
        for sender in (self.udp_sender, self.usb_sender):
            if sender is not None:
                send_now = sender is self.sender and self.active_transport_is_connected()
                sender.set_actuator_mode(mode, send_now=send_now)

    def connect_transport(self):
        transport_mode = self.transport_selector.currentText()

        if transport_mode == "HS USB" and self.detected_board == "Nucleo H723ZG":
            QMessageBox.warning(self, "HS USB Unavailable", "Nucleo H723ZG does not support HS USB. Use Ethernet (UDP).")
            ethernet_index = self.transport_selector.findText("Ethernet (UDP)")
            if ethernet_index >= 0:
                self.transport_selector.setCurrentIndex(ethernet_index)
            return
        
        if transport_mode == "Ethernet (UDP)":
            try:
                board_ip, local_ip, cmd_port, data_port = self.validate_comm_settings()
                self.receiver = self.get_parent_receiver("udp")
                self.sender = self.get_parent_sender("udp")
                self.sender.configure(ip=board_ip, port=cmd_port)
                self.receiver.rebind(data_port, host=local_ip)
                self.sender.open()
                self.sender.sync_board_mode()
                self.sender.sync_actuator_mode()
                if hasattr(self.sender, "sync_pe_gain"):
                    self.sender.sync_pe_gain()
                self.receiver.start()
                self.adc_running = False
                if self.sender.start_aq():
                    self.adc_running = True
                self.connected_transport = "udp"
                self.set_signal_controls_enabled(True)
                self.update_comm_status()
            except Exception as exc:
                QMessageBox.warning(self, "Connection Error", str(exc))
        
        elif transport_mode == "HS USB":
            try:
                usb_port = self.usb_port_input.currentText().strip()
                baudrate = self.usb_baudrate_input.text().strip()
                baudrate_value = int(baudrate)
                
                if not usb_port:
                    raise ValueError("USB COM port cannot be empty.")
                if not baudrate:
                    raise ValueError("Baudrate cannot be empty.")
                
                # Switch to USB receiver
                self.receiver = self.get_parent_receiver("usb")
                self.sender = self.get_parent_sender("usb")
                if hasattr(self.sender, "attach_receiver"):
                    self.sender.attach_receiver(self.receiver)
                if hasattr(self.sender, "configure"):
                    self.sender.configure(port=usb_port, baudrate=baudrate_value)
                if (self.receiver.port != usb_port) or (int(self.receiver.baudrate) != baudrate_value):
                    self.receiver.rebind(usb_port, baudrate=baudrate_value)
                self.receiver.set_buffer_size(int(self.buffer.currentText()))
                self.receiver.start()
                self.sender.open()
                self.sender.sync_board_mode()
                self.sender.sync_actuator_mode()
                if hasattr(self.sender, "sync_pe_gain"):
                    self.sender.sync_pe_gain()
                self.adc_running = False
                if self.sender.start_aq():
                    self.adc_running = True
                self.connected_transport = "usb"
                self.set_signal_controls_enabled(True)
                self.update_comm_status()
                QMessageBox.information(self, "USB Connected", f"Connected to {usb_port} at {baudrate} bps")
            except Exception as exc:
                QMessageBox.warning(self, "USB Connection Error", str(exc))

    def disconnect_transport(self):
        self.disconnect_connected_transport(reset_outputs=True)
        self.update_comm_status()

    def format_age_seconds(self, timestamp):
        if not timestamp:
            return "never"
        return f"{max(0.0, time.time() - timestamp):.1f}s ago"

    def update_comm_status(self):
        if not hasattr(self, "comm_status_label"):
            return

        if self.connected_transport is None:
            self.reset_status_labels()
            return

        transport_mode = self.transport_selector.currentText() if hasattr(self, "transport_selector") else "Ethernet (UDP)"
        
        if transport_mode == "Ethernet (UDP)":
            sender_status = self.sender.get_status()
            receiver_status = self.receiver.get_status()
            sender_state = "ready" if sender_status["connected"] else "stopped"
            receiver_state = "listening" if receiver_status["connected"] else "stopped"
            bind_text = receiver_status.get("display_host", "N/A")
            if receiver_status.get("host") == "0.0.0.0":
                bind_text = f"{receiver_status.get('display_host', 'N/A')} (all interfaces)"

            self.comm_status_label.setText(
                f"Sender: {sender_state} to {sender_status['ip']}:{sender_status['port']} | "
                f"RX: {receiver_state} on {bind_text}:{receiver_status['port']} | "
                f"Packets: {receiver_status['packet_count']} | "
                f"Speed: {receiver_status['speed_mbps']:.2f} Mbps | "
                f"Sent: {sender_status['sent_count']} | "
                f"Last RX: {self.format_age_seconds(receiver_status['last_packet_time'])} | "
                f"Last TX: {self.format_age_seconds(sender_status['last_send_time'])}"
            )
        
        elif transport_mode == "HS USB":
            sender_status = self.sender.get_status() if hasattr(self.sender, "get_status") else {"sent_count": 0}
            receiver_status = self.receiver.get_status()
            connected = receiver_status.get("connected", False)
            state = "connected" if connected else "disconnected"
            
            self.usb_status_label.setText(
                f"Status: {state} | "
                f"Port: {receiver_status.get('port', 'N/A')} | "
                f"Baudrate: {receiver_status.get('baudrate', 'N/A')} | "
                f"Packets: {receiver_status.get('packet_count', 0)} | "
                f"Samples: {receiver_status.get('total_samples', 0)} | "
                f"Speed: {receiver_status.get('speed_mbps', 0):.2f} Mbps | "
                f"Sent: {sender_status.get('sent_count', 0)} | "
                f"Last RX: {self.format_age_seconds(receiver_status.get('last_packet_time'))}"
            )
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
        if self.adc_running:
            return
        if self.sender.start_aq():
            self.adc_running = True

    def stop_acquisition(self):
        if self.sender.stop_aq():
            self.adc_running = False

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
        if self.current_actuator() == "Function Generator":
            self.sweeping = False
            self.current_freq = float(self.external_ref_freq.text())
            return

        self.sender.start_gen()
        self.reset_sweep()
        if self.current_output_mode() == "Frequency Sweep":
            self.sweeping = True
            self.current_freq = float(self.start_freq.text())
            self.set_dac_freq(self.current_freq)
        else:
            self.sweeping = False
            self.current_freq = float(self.constant_freq.text())
            self.set_dac_freq(self.current_freq)

    def stop_generation(self):
        self.sender.stop_gen()
        self.sweeping = False

    def set_dac_freq(self, value=None):
        if value is not None:
            self.sender.set_dac_freq(value)
            return

        if self.sweeping:
            value = self.current_freq
        else:
            value = float(self.constant_freq.text())
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
        actuator = self.current_actuator()
        output_mode = self.current_output_mode()
        sweep_mode = output_mode == "Frequency Sweep"

        # tab indexes (IMPORTANT: adjust if different)
        SETUP_TAB = 0
        SWEEP_TAB = 1
        EXTERNAL_SIGNAL_TAB  = 2
        if actuator == "Function Generator":
            self.frequency_stack.setCurrentIndex(1)
            # disable Sweep (DDS)
            self.tabs.setTabEnabled(SWEEP_TAB, False)
            self.start_dac.setEnabled(False)
            self.stop_dac.setEnabled(False)
            self.constant_freq.setEnabled(False)
            self.external_ref_freq.setEnabled(not self.auto_ref_freq_checkbox.isChecked())
            self.auto_ref_freq_checkbox.setEnabled(True)
            self.start_freq.setEnabled(False)
            self.stop_freq.setEnabled(False)
            self.step_freq.setEnabled(False)
            self.sweeping = False
            self.tabs.setTabEnabled(EXTERNAL_SIGNAL_TAB, True)
        elif actuator == "Direct Digital Synthesis (DDS)":
            self.frequency_stack.setCurrentIndex(2 if sweep_mode else 0)
            # disable Live Data
            self.tabs.setTabEnabled(SWEEP_TAB, sweep_mode)
            self.start_dac.setEnabled(True)
            self.stop_dac.setEnabled(True)
            self.constant_freq.setEnabled(not sweep_mode)
            self.external_ref_freq.setEnabled(False)
            self.auto_ref_freq_checkbox.setEnabled(False)
            self.start_freq.setEnabled(sweep_mode)
            self.stop_freq.setEnabled(sweep_mode)
            self.step_freq.setEnabled(sweep_mode)
            self.tabs.setTabEnabled(EXTERNAL_SIGNAL_TAB, False)
        elif actuator == "STM32 DAC Output":
            self.frequency_stack.setCurrentIndex(2 if sweep_mode else 0)
            # optional: allow both
            self.tabs.setTabEnabled(SWEEP_TAB, sweep_mode)
            self.start_dac.setEnabled(True)
            self.stop_dac.setEnabled(True)
            self.constant_freq.setEnabled(not sweep_mode)
            self.external_ref_freq.setEnabled(False)
            self.auto_ref_freq_checkbox.setEnabled(False)
            self.start_freq.setEnabled(sweep_mode)
            self.stop_freq.setEnabled(sweep_mode)
            self.step_freq.setEnabled(sweep_mode)
            self.tabs.setTabEnabled(EXTERNAL_SIGNAL_TAB, False)

        if not getattr(self, "signal_controls_enabled", True):
            self.tabs.setTabEnabled(SWEEP_TAB, False)
            self.tabs.setTabEnabled(EXTERNAL_SIGNAL_TAB, False)
            if self.tabs.currentIndex() in (SWEEP_TAB, EXTERNAL_SIGNAL_TAB):
                self.tabs.setCurrentIndex(SETUP_TAB)

    def get_active_plot_widgets(self):
        actuator = self.current_actuator()
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

    def update_frequency_history(self, f_ref, amp, phase_deg):
        actuator = self.current_actuator()

        if actuator == "Function Generator":
            if not self.sweep_freqs:
                self.sweep_freqs.append(f_ref)
                self.sweep_amp.append(amp)
                self.sweep_phase.append(phase_deg)
                self.last_freq = f_ref
                return

            if self.last_freq is None or abs(f_ref - self.last_freq) >= self.external_freq_tolerance_hz:
                self.sweep_freqs.append(f_ref)
                self.sweep_amp.append(amp)
                self.sweep_phase.append(phase_deg)
                self.last_freq = f_ref
            else:
                self.sweep_freqs[-1] = f_ref
                self.sweep_amp[-1] = amp
                self.sweep_phase[-1] = phase_deg
                self.last_freq = f_ref
            return

        if self.last_freq != f_ref:
            self.sweep_freqs.append(f_ref)
            self.sweep_amp.append(amp)
            self.sweep_phase.append(phase_deg)
            self.last_freq = f_ref

    def estimate_signal_frequency(self, signal, fs):
        if signal is None or len(signal) < 8 or fs <= 0:
            return None

        centered = np.asarray(signal, dtype=float) - np.mean(signal)
        if not np.any(centered):
            return None

        windowed = centered * np.hanning(len(centered))
        spectrum = np.fft.rfft(windowed)
        freqs = np.fft.rfftfreq(len(windowed), d=1.0 / fs)

        if len(freqs) < 2:
            return None

        magnitudes = np.abs(spectrum)
        magnitudes[0] = 0.0

        peak_index = int(np.argmax(magnitudes))
        if peak_index <= 0 or magnitudes[peak_index] <= 0:
            return None

        return float(freqs[peak_index])
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
        if self.current_actuator() == "Function Generator":
            if self.auto_ref_freq_checkbox.isChecked():
                detected_freq = self.estimate_signal_frequency(adc1, fs)
                if detected_freq is not None:
                    self.external_ref_freq.setText(f"{detected_freq:.2f}")
                    f_ref = detected_freq
                else:
                    f_ref = float(self.external_ref_freq.text())
            else:
                f_ref = float(self.external_ref_freq.text())
        elif self.sweeping:
            f_ref = self.current_freq
        else:
            f_ref = float(self.constant_freq.text())

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

        self.update_frequency_history(f_ref, amp, np.degrees(phase))

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
