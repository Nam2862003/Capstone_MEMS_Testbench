from PyQt6.QtWidgets import QWidget, QVBoxLayout, QPushButton, QLabel
from PyQt6.QtCore import Qt


class SelectPage(QWidget):

    def __init__(self):

        super().__init__()

        layout = QVBoxLayout()

        title = QLabel("PCB Selection")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-size:28px")

        self.btn_pr = QPushButton("Piezoresistive Board")
        self.btn_pe = QPushButton("Piezoelectric Board")

        self.btn_pr.setFixedSize(200, 60)
        self.btn_pe.setFixedSize(200, 60)

        layout.addStretch()

        layout.addWidget(title, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addSpacing(30)

        layout.addWidget(self.btn_pr, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addSpacing(20)
        layout.addWidget(self.btn_pe, alignment=Qt.AlignmentFlag.AlignCenter)

        layout.addStretch()

        self.setLayout(layout)