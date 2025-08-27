# frontend/views/login_dialog.py
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QRadioButton, QButtonGroup, QFrame
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
import os
from services.auth_service import AuthService

class LoginDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("כניסה – ספקים וחנויות")
        self.resize(1060, 720)          # חלון גדול כמו בדוגמה
        self.setMinimumSize(820, 580)   # לא לרדת מתחת לסביר
                # טיפוגרפיה פרופורציונלית
        base_px = max(self.width(), self.height())
        title_px = int(base_px * 0.038)    # בערך 28–36px
        body_px  = int(base_px * 0.018)    # 13–16px

        self.setStyleSheet(f"""
            QDialog {{ background: #f3f4f6; font-family: 'Segoe UI', Arial, sans-serif; }}
            QFrame#Card {{ background: rgba(255,255,255,0.96); border-radius: 14px; padding: 32px; }}
            QLabel#Title {{ font-size: {title_px}px; font-weight: 800; color: #111827; }}
            QLabel#Sub {{ color:#6b7280; font-size: {max(12, body_px)}px; margin: 8px 0 24px; }}
            QLineEdit {{ padding: 14px; font-size: {max(12, body_px)}px; border:1px solid #d1d5db; border-radius:8px; background:#eef2ff; }}
            QPushButton {{ padding: 12px 16px; border-radius:10px; font-weight:600; }}
            QPushButton#Primary {{ background:#2563eb; color:#fff; }}
            QPushButton#Primary:hover {{ background:#1d4ed8; }}
            QPushButton#Ghost {{ background:transparent; color:#2563eb; text-decoration: underline; }}
            QLabel#Error {{ color:#dc2626; font-size:{max(12, body_px)}px; padding:8px; background:#fef2f2; border-radius:8px; }}
        """)
        def resizeEvent(self, ev):
            # עדכון גדלי גופנים דינמי (אותו חישוב כמו למעלה)
            base_px = max(self.width(), self.height())
            title_px = int(base_px * 0.038)
            body_px  = int(base_px * 0.018)
            self.findChild(QLabel, "Title").setStyleSheet(f"font-size:{title_px}px; font-weight:800; color:#111827;")
            self.findChild(QLabel, "Sub").setStyleSheet(f"color:#6b7280; font-size:{max(12, body_px)}px; margin: 8px 0 24px;")
            return super().resizeEvent(ev)

        self.auth = AuthService()
        self.user = None

        # עיצוב מבוסס על Login.module.css
        self.setStyleSheet("""
            QDialog { 
                background: #f3f4f6; 
                font-family: 'Arial', 'Segoe UI', sans-serif;
            }
            
            QFrame#Card { 
                background-color: rgba(255, 255, 255, 0.95);
                border-radius: 8px;
                border: none;
                padding: 32px;
            }
            
            QPushButton { 
                font-size: 16px;
                font-weight: 600;
                border: none;
                border-radius: 4px;
                transition: background-color 0.3s ease;
            }
            
            QPushButton#Primary { 
                background-color: #007bff;
                color: white;
                padding: 16px;
                font-size: 17px;
            }
            
            QPushButton#Primary:hover { 
                background-color: #0056b3;
            }
            
            QPushButton#Primary:pressed {
                background-color: #004494;
            }
            
            QPushButton#Ghost { 
                background-color: transparent;
                color: #007bff;
                padding: 8px;
                font-size: 14px;
                text-decoration: underline;
            }
            
            QPushButton#Ghost:hover { 
                color: #0056b3;
                text-decoration: underline;
            }
            
            QLineEdit { 
                padding: 16px;
                border: 1px solid #ddd;
                border-radius: 4px;
                font-size: 16px;
                background-color: white;
            }
            
            QLineEdit:focus { 
                border-color: #007bff;
                outline: none;
            }
            
            QLabel#Title { 
                font-size: 40px;
                font-weight: bold;
                color: #333;
                margin: 0;
                padding: 0;
            }
            
            QLabel#Sub { 
                color: #666;
                font-size: 14px;
                margin-top: 8px;
                margin-bottom: 24px;
            }
            
            QRadioButton {
                font-size: 14px;
                color: #333;
                spacing: 8px;
            }
            
            QRadioButton::indicator {
                width: 16px;
                height: 16px;
            }
            
            QLabel#Error {
                color: #dc2626;
                font-size: 14px;
                padding: 8px;
                background-color: #fef2f2;
                border-radius: 4px;
                margin: 4px 0;
            }
        """)

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 20)
        
        card = QFrame(objectName="Card")
        v = QVBoxLayout(card)
        v.setSpacing(20)

        # לוגו
        logo = QLabel()
        logo_path = os.path.join(os.path.dirname(__file__), "../../assets/logo.png")
        if os.path.exists(logo_path):
            logo.setPixmap(QPixmap(logo_path).scaled(80, 80, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        logo.setAlignment(Qt.AlignCenter)
        v.addWidget(logo)

        title = QLabel("התחברות", objectName="Title", alignment=Qt.AlignCenter)
        sub = QLabel("אנא בחרי תפקיד והתחברי למערכת", objectName="Sub", alignment=Qt.AlignCenter)
        v.addWidget(title)
        v.addWidget(sub)

        # בחירת תפקיד
        row = QHBoxLayout()
        row.setSpacing(24)
        self.rb_owner = QRadioButton("בעל חנות")
        self.rb_supplier = QRadioButton("ספק")
        self.rb_supplier.setChecked(True)
        self._group = QButtonGroup(self)
        self._group.addButton(self.rb_owner)
        self._group.addButton(self.rb_supplier)
        row.addStretch(1)
        row.addWidget(self.rb_owner)
        row.addWidget(self.rb_supplier)
        row.addStretch(1)
        v.addLayout(row)

        # טופס
        self.edt_user = QLineEdit(placeholderText="הכנס שם משתמש")
        self.edt_pass = QLineEdit(placeholderText="הכנס סיסמה")
        self.edt_pass.setEchoMode(QLineEdit.Password)
        v.addWidget(self.edt_user)
        v.addWidget(self.edt_pass)

        self.lbl_msg = QLabel("", alignment=Qt.AlignCenter, objectName="Error")
        self.lbl_msg.hide()
        v.addWidget(self.lbl_msg)

        # כפתורים
        btn_login = QPushButton("התחבר", objectName="Primary")
        v.addWidget(btn_login)
        
        btn_signup = QPushButton("רישום למערכת", objectName="Ghost")
        v.addWidget(btn_signup)

        root.addStretch(1)
        root.addWidget(card, alignment=Qt.AlignCenter)
        root.addStretch(1)

        # חיבור אירועים
        btn_signup.clicked.connect(self._open_signup)
      # או פתיחת דיאלוג הרשמה
        btn_login.clicked.connect(self._do_login)
        self.edt_pass.returnPressed.connect(self._do_login)
    def _open_signup(self):
        try:
            from .signup_dialog import SignUpDialog
            dlg = SignUpDialog(self)
            if dlg.exec():
                # אם נרשמו בהצלחה – למלא אוטומטית לכניסה
                self.edt_user.setText(dlg.created_username or "")
                self.edt_pass.setText(dlg.created_password or "")
                self.lbl_msg.hide()
        except Exception as e:
            self.lbl_msg.setText(f"שגיאה בפתיחת מסך הרשמה: {e}")
            self.lbl_msg.show()

    def _do_login(self):
        username = self.edt_user.text().strip()
        password = self.edt_pass.text().strip()
        
        if not username or not password:
            self.lbl_msg.setText("יש למלא שם משתמש וסיסמה")
            self.lbl_msg.show()
            return
            
        role = "Supplier" if self.rb_supplier.isChecked() else "StoreOwner"
        ok, user, err = self.auth.verify_login(username, password, role)
        if ok:
            self.user = user
            self.accept()
        else:
            self.lbl_msg.setText(err or "שם משתמש או סיסמה שגויים")
            self.lbl_msg.show()