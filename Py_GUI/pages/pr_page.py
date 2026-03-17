from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel
from pages.base_functions import BaseDAQPage


class PRPage(BaseDAQPage):

    def __init__(self, receiver, sender):

        super().__init__(receiver, sender)

        self.calibration = QWidget()

        layout = QVBoxLayout()
        layout.addWidget(QLabel("Calibration Tools"))

        self.calibration.setLayout(layout)

        self.tabs.insertTab(1, self.calibration, "Calibration")