from PySide6.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QWidget, QMessageBox
from PySide6.QtCore import Signal

class SideMenu(QFrame):
    """תפריט צידי לבעל חנות"""
    page_requested = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("sideMenu")
        self.setFixedWidth(280)
        self.setup_ui()
        self.setup_styles()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        header = QFrame(objectName="menuHeader")
        header.setFixedHeight(60)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(24, 16, 24, 16)

        title = QLabel("תפריט בעל חנות", objectName="menuTitle")
        close_btn = QPushButton("✕", objectName="closeBtn")
        close_btn.setFixedSize(32, 32)
        close_btn.clicked.connect(self.hide)

        header_layout.addWidget(title)
        header_layout.addWidget(close_btn)
        layout.addWidget(header)

        menu_items = [
            ("orders", "רשימת הזמנות"),
            ("new_order", "יצירת הזמנה חדשה"),
            ("suppliers", "רשימת ספקים"),
            ("ai_chat", "שיחה עם העוזר הדיגיטלי")
        ]

        menu_container = QWidget()
        menu_layout = QVBoxLayout(menu_container)
        menu_layout.setContentsMargins(16, 24, 16, 24)
        menu_layout.setSpacing(8)

        for action, text in menu_items:
            btn = QPushButton(text, objectName="menuItem")
            btn.clicked.connect(lambda _=False, a=action: self.on_menu_click(a))
            menu_layout.addWidget(btn)

        menu_layout.addStretch()
        layout.addWidget(menu_container)

    def on_menu_click(self, action: str):
        if action in ["orders", "new_order", "suppliers", "ai_chat"]:
             self.page_requested.emit(action)
             self.hide()
        else:
             QMessageBox.information(self, "בקרוב", f"תכונה '{action}' תהיה זמינה בקרוב")

    def setup_styles(self):
        self.setStyleSheet("""
            QFrame#sideMenu { background:#fff; border:1px solid #e5e7eb; border-radius:0 8px 8px 0; }
            QFrame#menuHeader { background:#eff6ff; border-bottom:1px solid #bfdbfe; border-radius:0 8px 0 0; }
            QLabel#menuTitle { font-size:18px; font-weight:700; color:#1e40af; }
            QPushButton#closeBtn { background:transparent; border:1px solid #e5e7eb; border-radius:16px; color:#6b7280; font-size:14px; }
            QPushButton#closeBtn:hover { background:#f3f4f6; color:#374151; }
            QPushButton#menuItem {
                background:transparent; border:none; border-radius:8px; padding:14px 16px;
                text-align:left; font-size:14px; font-weight:500; color:#374151; min-height:20px;
            }
            QPushButton#menuItem:hover { background:#dbeafe; color:#1d4ed8; }
            QPushButton#menuItem:pressed { background:#bfdbfe; }
        """)


