# frontend/test_connection_main.py
import sys
from PySide6.QtWidgets import QApplication
from views.test_connection import TestConnectionWidget

if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = TestConnectionWidget()
    w.show()
    sys.exit(app.exec())
