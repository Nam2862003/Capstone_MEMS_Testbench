from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QGroupBox, QHBoxLayout, QLabel, QSlider, QVBoxLayout, QWidget, QSizePolicy

from pages.base_functions import BaseDAQPage


class PEPage(BaseDAQPage):
    GAIN_OPTIONS = [
        ("1x gain", "00"),
        ("7.5x gain", "01"),
        ("10x gain", "10"),
        ("20x gain", "11"),
    ]
    GAIN_MARKS = ["1x", "7.5x", "10x", "20x"]

    def __init__(self, receiver, sender, usb_receiver=None, usb_sender=None):
        super().__init__(receiver, sender, usb_receiver, usb_sender)

    def build_setup_sidebar_group(self):
        gain_group = QGroupBox("Gain Selection (PE)")
        gain_layout = QVBoxLayout()

        header_row = QHBoxLayout()
        self.gain_value_label = QLabel()
        self.gain_code_label = QLabel()
        self.gain_code_label.setObjectName("MutedLabel")
        header_row.addWidget(self.gain_value_label)
        header_row.addStretch()
        header_row.addWidget(self.gain_code_label)

        self.gain_slider = QSlider(Qt.Orientation.Horizontal)
        self.gain_slider.setObjectName("DiscreteSlider")
        self.gain_slider.setMinimum(0)
        self.gain_slider.setMaximum(len(self.GAIN_OPTIONS) - 1)
        self.gain_slider.setSingleStep(1)
        self.gain_slider.setPageStep(1)
        self.gain_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.gain_slider.setTickInterval(1)
        self.gain_slider.setValue(0)

        track_widget = QWidget()
        track_layout = QVBoxLayout()
        track_layout.setContentsMargins(12, 0, 12, 0)
        track_layout.setSpacing(6)

        marks_row = QHBoxLayout()
        marks_row.setContentsMargins(4, 0, 4, 0)
        for label_text in self.GAIN_MARKS:
            mark = QLabel(label_text)
            mark.setAlignment(Qt.AlignmentFlag.AlignCenter)
            mark.setObjectName("MutedLabel")
            marks_row.addWidget(mark, 1)

        track_layout.addWidget(self.gain_slider)
        track_layout.addLayout(marks_row)
        track_widget.setLayout(track_layout)
        track_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        track_widget.setMinimumWidth(520)

        gain_layout.addLayout(header_row)
        gain_layout.addWidget(track_widget)
        gain_group.setLayout(gain_layout)
        gain_group.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)

        self.gain_slider.valueChanged.connect(self.update_gain_display)
        self.gain_slider.sliderReleased.connect(self.apply_gain_selection)
        self.update_gain_display(self.gain_slider.value())

        return gain_group

    def update_gain_display(self, index):
        gain_text, gain_code = self.GAIN_OPTIONS[int(index)]
        self.gain_value_label.setText(gain_text)
        self.gain_code_label.setText(f"GPIO: {gain_code}")

    def apply_gain_selection(self):
        gain_index = self.gain_slider.value()
        for sender in (self.udp_sender, self.usb_sender):
            if sender is not None:
                send_now = sender is self.sender and self.active_transport_is_connected()
                sender.set_pe_gain(gain_index, send_now=send_now)
