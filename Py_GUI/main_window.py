from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QStackedWidget,
    QPushButton, QHBoxLayout
)

from pages.select_page import SelectPage
from pages.pr_page import PRPage
from pages.pe_page import PEPage
from style import STYLE

from network.udp_receiver import UDPReceiver
from network.usb_receiver import USBReceiver
from network.udp_sender import UDPSender
from network.usb_sender import USBSender

class PCB_GUI(QWidget):

    def __init__(self):

        super().__init__()

        self.setWindowTitle("MEMS Data Acquisition")
        self.setMinimumSize(900, 650)
        self.resize(1280, 760)
        self.setStyleSheet(STYLE)

        layout = QVBoxLayout()

        # Navigation bar for pages
        # Initialize each transport separately; pages will select which pair to use.
        self.udp_receiver = UDPReceiver()
        self.udp_sender = UDPSender()
        self.usb_receiver = USBReceiver()
        self.usb_sender = USBSender(receiver=self.usb_receiver)
        self.receiver = self.udp_receiver  # Default to UDP
        self.sender = self.udp_sender
        nav = QHBoxLayout()
        self.back_btn = QPushButton("← Back")
        nav.addWidget(self.back_btn)
        nav.addStretch()
        layout.addLayout(nav)
        # Stacked pages
        self.pages = QStackedWidget()
        self.select_page = SelectPage()
        self.pe_page = PEPage(self.receiver, self.sender, self.usb_receiver, self.usb_sender)
        self.pr_page = PRPage(self.receiver, self.sender, self.usb_receiver, self.usb_sender)
        self.pages.addWidget(self.select_page)
        self.pages.addWidget(self.pr_page)
        self.pages.addWidget(self.pe_page)

        layout.addWidget(self.pages)

        self.setLayout(layout)

        # Connections
        self.select_page.btn_pr.clicked.connect(self.open_pr)
        self.select_page.btn_pe.clicked.connect(self.open_pe)

        self.back_btn.clicked.connect(self.go_back)

    def set_board_mode(self, mode):
        self.udp_sender.set_board_mode(mode, send_now=False)
        self.usb_sender.set_board_mode(mode, send_now=False)

    def current_daq_page(self):
        current = self.pages.currentWidget()
        if current in (self.pr_page, self.pe_page):
            return current
        return None

    def leave_current_daq_page(self, next_page=None):
        current = self.current_daq_page()
        if current is not None and current is not next_page:
            current.disconnect_connected_transport(reset_outputs=True)

    def open_pr(self):
        self.leave_current_daq_page(next_page=self.pr_page)
        self.set_board_mode("PR")
        self.pr_page.sync_board_transport_mode()
        self.pr_page.sync_actuator_transport_mode()
        self.pages.setCurrentIndex(1)

    def open_pe(self):
        self.leave_current_daq_page(next_page=self.pe_page)
        self.set_board_mode("PE")
        self.pe_page.sync_board_transport_mode()
        self.pe_page.sync_actuator_transport_mode()
        self.pages.setCurrentIndex(2)

    def go_back(self):
        self.leave_current_daq_page()
        self.pages.setCurrentIndex(0)

    def closeEvent(self, event):
        self.leave_current_daq_page()
        self.udp_receiver.stop()
        self.usb_receiver.stop()
        self.udp_sender.close()
        self.usb_sender.close()
        super().closeEvent(event)
