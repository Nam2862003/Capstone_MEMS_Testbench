from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QTabWidget,
    QLabel, QPushButton, QComboBox
)


class PEPage(QWidget):

    def __init__(self):

        super().__init__()

        layout = QVBoxLayout()

        tabs = QTabWidget()

        setup = QWidget()
        acquisition = QWidget()

        tabs.addTab(setup, "Setup")
        tabs.addTab(acquisition, "Acquisition")

        layout.addWidget(tabs)

        self.setLayout(layout)

        # Setup tab
        setup_layout = QVBoxLayout()

        rate = QComboBox()
        rate.addItems(["100 kSPS", "500 kSPS", "1 MSPS", "2 MSPS"])

        start = QPushButton("Start")
        stop = QPushButton("Stop")

        setup_layout.addWidget(QLabel("Sampling Rate"))
        setup_layout.addWidget(rate)
        setup_layout.addWidget(start)
        setup_layout.addWidget(stop)

        setup.setLayout(setup_layout)