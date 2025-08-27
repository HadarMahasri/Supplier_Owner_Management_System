# frontend/views/pages/supplier_home.py

from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QFrame
from PySide6.QtCore import Signal, Qt

from views.widgets.order_list_for_supplier import OrderListForSupplier


class SupplierHome(QWidget):
    logout_requested = Signal()  # נשתמש בזה כדי לחזור ל-LoginPage ב-MainWindow

    def __init__(self, user: dict):
        super().__init__()
        self.user = user

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # === Toolbar ===
        toolbar = QFrame()
        toolbar_layout = QHBoxLayout(toolbar)
        toolbar_layout.setContentsMargins(10, 10, 10, 10)

        lbl_title = QLabel(f"שלום {self.user.get('username', 'ספק')}")
        lbl_title.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        btn_logout = QPushButton("התנתק")
        btn_logout.clicked.connect(self.logout_requested.emit)

        toolbar_layout.addWidget(lbl_title)
        toolbar_layout.addStretch()
        toolbar_layout.addWidget(btn_logout)

        # === Order List ===
        self.order_list = OrderListForSupplier()

        # === Assemble ===
        layout.addWidget(toolbar)
        layout.addWidget(self.order_list)
