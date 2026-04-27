from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QStackedWidget,
    QPushButton, QHBoxLayout
)

from pages.select_page import SelectPage
from pages.pr_page import PRPage
from pages.pe_page import PEPage
from style import STYLE

from network.udp_receiver import UDPReceiver
from network.udp_sender import UDPSender

class PCB_GUI(QWidget):

    def __init__(self):

        super().__init__()

        self.setWindowTitle("MEMS Data Acquisition")
        self.setMinimumSize(900, 650)
        self.resize(1280, 760)
        self.setStyleSheet(STYLE)

        layout = QVBoxLayout()

        # Navigation bar for pages
        self.receiver = UDPReceiver()
        self.sender = UDPSender()
        nav = QHBoxLayout()
        self.back_btn = QPushButton("← Back")
        nav.addWidget(self.back_btn)
        nav.addStretch()
        layout.addLayout(nav)
        # Stacked pages
        self.pages = QStackedWidget()
        self.select_page = SelectPage()
        self.pe_page = PEPage(self.receiver, self.sender)
        self.pr_page = PRPage(self.receiver, self.sender)
        self.pages.addWidget(self.select_page)
        self.pages.addWidget(self.pr_page)
        self.pages.addWidget(self.pe_page)

        layout.addWidget(self.pages)

        self.setLayout(layout)

        # Connections
        self.select_page.btn_pr.clicked.connect(self.open_pr)
        self.select_page.btn_pe.clicked.connect(self.open_pe)

        self.back_btn.clicked.connect(self.go_back)

    def open_pr(self):
        self.sender.set_board_mode("PR")
        self.pr_page.sync_actuator_transport_mode()
        self.pages.setCurrentIndex(1)

    def open_pe(self):
        self.sender.set_board_mode("PE")
        self.pe_page.sync_actuator_transport_mode()
        self.pages.setCurrentIndex(2)

    def go_back(self):

        self.pages.setCurrentIndex(0)

    def closeEvent(self, event):
        self.receiver.stop()
        self.sender.close()
        super().closeEvent(event)
