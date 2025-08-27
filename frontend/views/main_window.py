# frontend/views/main_window.py

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QLabel, QVBoxLayout, QStackedWidget, QFrame, QHBoxLayout
)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QPixmap
from pathlib import Path

from views.pages.login_page import LoginPage
from views.pages.signup_page import SignUpPage


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ספקים וחנויות – חלון יחיד")
        self.resize(1180, 760)

        # ==== רקע (QLabel ברקע) ====
        self.background_label = QLabel(self)
        self.background_label.setScaledContents(True)  # מאפשר שינוי גודל
        self.background_label.lower()  # מעביר לשכבת רקע

        background_path = Path(__file__).parent.parent / "resources" / "background_blur.jpg"
        if background_path.exists():
            self.background_pixmap = QPixmap(str(background_path))
        else:
            self.background_pixmap = None

        # ==== תוכן ראשי ====
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)
        central_layout = QVBoxLayout(central_widget)
        central_layout.setContentsMargins(0, 0, 0, 0)
        central_layout.setSpacing(0)

        # ==== אזור כותרת (עם לוגו וטקסט) ====
        header = QFrame(objectName="Header")
        header.setFixedHeight(96)
        hlayout = QHBoxLayout(header)
        hlayout.setContentsMargins(24, 16, 24, 16)
        hlayout.setSpacing(12)

        title = QLabel("ספקים וחנויות", objectName="Title")
        title.setAlignment(Qt.AlignCenter)

        logo = QLabel()
        logo.setAlignment(Qt.AlignCenter)
        logo_path = Path(__file__).parent.parent / "resources" / "logo_store.png"
        if logo_path.exists():
            logo.setPixmap(QPixmap(str(logo_path)).scaled(QSize(56, 56), Qt.KeepAspectRatio, Qt.SmoothTransformation))

        hlayout.addStretch()
        hlayout.addWidget(title)
        hlayout.addWidget(logo)
        hlayout.addStretch()

        # ==== עמודים (Login/Signup וכו') ====
        self.stack = QStackedWidget(objectName="ContentStack")
        self.page_login = LoginPage()
        self.page_signup = SignUpPage()

        self.stack.addWidget(self.page_login)
        self.stack.addWidget(self.page_signup)

        central_layout.addWidget(header)
        central_layout.addWidget(self.stack)

        # ==== סגנון עיצוב כללי ====
        self.setStyleSheet("""
            QLabel#Title {
                font-size: 32px;
                font-weight: bold;
                color: #111;
            }
            QFrame#Header {
                background: rgba(255, 255, 255, 210);
                border-bottom: 1px solid #ddd;
            }
            QStackedWidget#ContentStack {
                background: rgba(255, 255, 255, 230);
                border-radius: 12px;
                margin: 24px;
                padding: 12px;
            }
        """)

        # ==== אירועים בין עמודים ====
        self.page_login.request_signup.connect(lambda: self.stack.setCurrentWidget(self.page_signup))
        self.page_login.login_success.connect(self._on_login_ok)
        self.page_signup.back_to_login.connect(lambda: self.stack.setCurrentWidget(self.page_login))
        self.page_signup.signup_success.connect(self._on_signup_ok)

        self.stack.setCurrentWidget(self.page_login)

    def resizeEvent(self, event):
        """ עדכון רקע בעת שינוי גודל החלון """
        if self.background_pixmap:
            scaled = self.background_pixmap.scaled(self.size(), Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
            self.background_label.setPixmap(scaled)
            self.background_label.resize(self.size())
        super().resizeEvent(event)

    def _on_login_ok(self, user: dict):
        self.statusBar().showMessage(f"שלום {user.get('username')}", 5000)

    def _on_signup_ok(self, username: str, password: str):
        self.page_login.prefill(username, password)
        self.stack.setCurrentWidget(self.page_login)
        self.statusBar().showMessage("נרשמת בהצלחה!", 5000)
