from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QLineEdit, QPushButton, QFrame,
    QHBoxLayout, QRadioButton, QButtonGroup, QSpacerItem, QSizePolicy
)
from PySide6.QtCore import Qt, Signal
from services.auth_service import AuthService

class LoginPage(QWidget):
    request_signup = Signal()
    login_success  = Signal(dict)

    def __init__(self):
        super().__init__()
        self.auth = AuthService()

        # פריסה מרכזית – הכרטיס ממורכז גדול ופרופורציונלי
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 24)

        root.addItem(QSpacerItem(0, 0, QSizePolicy.Minimum, QSizePolicy.Expanding))

        card = QFrame()
        card.setObjectName("Card")
        card.setMinimumWidth(420)
        card.setMaximumWidth(520)
        v = QVBoxLayout(card)
        v.setContentsMargins(28, 28, 28, 28)
        v.setSpacing(12)

        card.setStyleSheet("""
            QFrame#Card { background:#ffffff; border:1px solid #e5e7eb; border-radius:16px; }
            QLabel#Title { font-size: 32px; font-weight: 900; color:#111827; }
            QLineEdit { padding:14px; font-size:16px; border:1px solid #d1d5db; border-radius:10px; background:#eef2ff; }
            QPushButton { padding:14px; border-radius:12px; font-weight:800; border:none; }
            QPushButton#Primary { background:#2563eb; color:#fff; }
            QPushButton#Primary:hover { background:#1d4ed8; }
            QLabel#Msg { color:#dc2626; }
        """)

        title = QLabel("התחברות", objectName="Title", alignment=Qt.AlignCenter)
        v.addWidget(title)

        # בחירת תפקיד
        role_row = QHBoxLayout()
        self.rb_supplier = QRadioButton("ספק")
        self.rb_owner    = QRadioButton("בעל חנות")
        self.rb_supplier.setChecked(True)
        grp = QButtonGroup(self); grp.addButton(self.rb_supplier); grp.addButton(self.rb_owner)
        role_row.addStretch(1); role_row.addWidget(self.rb_owner); role_row.addWidget(self.rb_supplier); role_row.addStretch(1)
        v.addLayout(role_row)

        self.ed_user = QLineEdit(placeholderText="שם משתמש")
        self.ed_pass = QLineEdit(placeholderText="סיסמה"); self.ed_pass.setEchoMode(QLineEdit.Password)
        v.addWidget(self.ed_user)
        v.addWidget(self.ed_pass)

        self.lbl_msg = QLabel("", objectName="Msg", alignment=Qt.AlignCenter)
        v.addWidget(self.lbl_msg)

        btn_login = QPushButton("כניסה", objectName="Primary")
        v.addWidget(btn_login)

        btn_signup = QPushButton("רישום למערכת")
        btn_signup.setFlat(True)
        btn_signup.setStyleSheet("color:#2563eb; text-decoration: underline; font-weight:700;")
        v.addWidget(btn_signup, 0, Qt.AlignCenter)

        # מרכז הכרטיס במסך
        root.addWidget(card, 0, Qt.AlignCenter)
        root.addItem(QSpacerItem(0, 0, QSizePolicy.Minimum, QSizePolicy.Expanding))

        # חיווט
        btn_login.clicked.connect(self._do_login)
        btn_signup.clicked.connect(self.request_signup.emit)

    def _do_login(self):
        role = "Supplier" if self.rb_supplier.isChecked() else "StoreOwner"
        ok, user, err = self.auth.verify_login(self.ed_user.text().strip(), self.ed_pass.text().strip(), role)
        if ok:
            self.lbl_msg.setText("")
            self.login_success.emit(user)
        else:
            self.lbl_msg.setText(err or "שם המשתמש או הסיסמה שגויים")

    def prefill(self, u, p):
        self.ed_user.setText(u or "")
        self.ed_pass.setText(p or "")
