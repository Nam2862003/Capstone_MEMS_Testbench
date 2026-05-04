from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel
from pages.base_functions import BaseDAQPage


class PRPage(BaseDAQPage):

    def __init__(self, receiver, sender, usb_receiver=None, usb_sender=None):

        super().__init__(receiver, sender, usb_receiver, usb_sender)

        # self.calibration = QWidget()

        # layout = QVBoxLayout()
        # layout.addWidget(QLabel("Calibration Tools"))

        # self.calibration.setLayout(layout)

        # self.tabs.insertTab(1, self.calibration, "Calibration")
