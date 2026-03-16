import sys
from PyQt6.QtWidgets import QApplication
from main_window import PCB_GUI

if __name__ == "__main__":

    app = QApplication(sys.argv)

    window = PCB_GUI()
    window.show()

    sys.exit(app.exec())