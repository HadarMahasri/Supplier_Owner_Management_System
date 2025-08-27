from PySide6.QtWidgets import QWidget, QVBoxLayout, QPushButton, QLabel
import requests
import os

API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")

class TestConnectionWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("בדיקת חיבור לשרת")

        layout = QVBoxLayout()

        self.status_label = QLabel("לחץ על הכפתור כדי לבדוק חיבור")
        layout.addWidget(self.status_label)

        self.check_button = QPushButton("בדיקת חיבור לשרת")
        self.check_button.clicked.connect(self.check_connection)
        layout.addWidget(self.check_button)

        self.setLayout(layout)

    def check_connection(self):
        try:
            r = requests.get(f"{API_BASE_URL}/health", timeout=5)
            if r.status_code == 200:
                data = r.json()
                if data.get("database") == "connected":
                    self.status_label.setText("✅ השרת מחובר למסד נתונים")
                else:
                    self.status_label.setText("⚠️ השרת חי, אבל מסד הנתונים לא מחובר")
            else:
                self.status_label.setText(f"❌ בעיה בחיבור (קוד {r.status_code})")
        except Exception as e:
            self.status_label.setText(f"❌ לא הצליח להתחבר: {e}")
