# frontend/views/signup_dialog.py
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QRadioButton,
    QButtonGroup, QFrame, QScrollArea, QWidget
)
from PySide6.QtCore import Qt
from services.auth_service import AuthService
from views.widgets.service_areas_picker import ServiceAreasPicker  # הרכיב החדש לבחירת אזורי שירות


class SignUpDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("הרשמה – ספקים וחנויות")
        self.resize(720, 760)
        self.setMinimumSize(620, 620)

        self.auth = AuthService()
        self.created_username = None
        self.created_password = None

        # נסיון לטעינת גיאוגרפיה; אם נכשל – לא מציגים אזורי שירות
        self.geo_tree = []
        self._geo_ok = True
        try:
            from services.geo_service import fetch_districts_with_cities
            self.geo_tree = fetch_districts_with_cities()  # מחזיר [{district_id, district_name, cities:[{city_id, city_name}]}]
        except Exception:
            self._geo_ok = False

        # --- עיצוב בסיסי ---
        self.setStyleSheet("""
            QDialog { background: #f3f4f6; font-family: 'Segoe UI', Arial, sans-serif; direction: rtl; }
            QFrame#Card { background: #fff; border-radius: 16px; border: 1px solid rgba(0,0,0,0.06); }
            QLabel#Title { font-size: 22px; font-weight: 800; color: #1f2937; }
            QLabel.FieldLabel { font-weight: 600; color: #374151; margin: 12px 0 6px; }
            QLabel#Error { color:#dc2626; font-size:13px; padding:8px; background:#fef2f2; border-radius:8px; }
            QLineEdit { padding: 10px 12px; border: 1px solid #e2e8f0; border-radius: 8px; font-size: 14px; }
            QLineEdit:focus { border-color: #3b82f6; box-shadow: 0 0 0 3px rgba(59,130,246,.15); }
            QRadioButton { font-weight:600; color:#334155; margin: 0 10px; }
            QScrollArea { border: 1px solid #e2e8f0; border-radius: 12px; background: #f9fafb; }
            QPushButton { padding: 12px 16px; border-radius: 10px; font-weight: 700; border: none; }
            QPushButton#Primary { background:#2563eb; color:#fff; }
            QPushButton#Primary:hover { background:#1d4ed8; }
        """)

        # --- מבנה עם גלילה ---
        root = QVBoxLayout(self); root.setContentsMargins(20, 20, 20, 20)
        scroll = QScrollArea(); scroll.setWidgetResizable(True); scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        root.addWidget(scroll)

        host = QWidget(); scroll.setWidget(host)
        host_layout = QVBoxLayout(host)

        card = QFrame(objectName="Card")
        card_layout = QVBoxLayout(card); card_layout.setContentsMargins(24, 24, 24, 24); card_layout.setSpacing(12)
        host_layout.addWidget(card)

        title = QLabel("הרשמה", objectName="Title", alignment=Qt.AlignCenter)
        card_layout.addWidget(title)

        # --- בחירת תפקיד ---
        role_row = QHBoxLayout()
        self.rb_supplier = QRadioButton("ספק")
        self.rb_owner = QRadioButton("בעל חנות")
        self.rb_supplier.setChecked(True)
        self._role_group = QButtonGroup(self)
        self._role_group.addButton(self.rb_supplier)
        self._role_group.addButton(self.rb_owner)
        role_row.addStretch(1)
        role_row.addWidget(self.rb_owner)
        role_row.addWidget(self.rb_supplier)
        role_row.addStretch(1)
        card_layout.addLayout(role_row)

        # helper לשדות + שמירת תוויות לשליטה ב־visible
        self._labels = {}
        def add_field(lbl_txt, widget):
            lbl = QLabel(lbl_txt); lbl.setProperty("class", "FieldLabel"); lbl.setObjectName("FieldLabel")
            lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            card_layout.addWidget(lbl); card_layout.addWidget(widget)
            self._labels[widget] = lbl
            return widget

        # --- שדות משותפים ---
        self.ed_company = add_field("שם החברה (לספק, אופציונלי)", QLineEdit())
        self.ed_contact = add_field("איש קשר *", QLineEdit())
        self.ed_phone   = add_field("טלפון *", QLineEdit())
        self.ed_email   = add_field("אימייל *", QLineEdit("name@example.com"))

        # --- בעל חנות: כתובת/שעות ---
        self.ed_city   = add_field("עיר *", QLineEdit("הקלידי שם עיר..."))
        self.ed_street = add_field("רחוב *", QLineEdit())
        self.ed_house  = add_field("מספר בית *", QLineEdit())

        hours_row = QHBoxLayout()
        self.ed_open  = QLineEdit("HH:MM")
        self.ed_close = QLineEdit("HH:MM")
        c1 = QVBoxLayout(); c1.addWidget(QLabel("שעת פתיחה *", alignment=Qt.AlignRight)); c1.addWidget(self.ed_open)
        c2 = QVBoxLayout(); c2.addWidget(QLabel("שעת סגירה *", alignment=Qt.AlignRight)); c2.addWidget(self.ed_close)
        hours_row.addLayout(c1); hours_row.addLayout(c2)
        card_layout.addLayout(hours_row)
        self._labels[self.ed_open]  = c1.itemAt(0).widget()
        self._labels[self.ed_close] = c2.itemAt(0).widget()

        # --- ספק: אזורי שירות (Picker חדש במקום area_label + area_scroll הישנים) ---
        self.area_title = QLabel("אזורי שירות (בחרי מחוזות שלמים או ערים ספציפיות):")
        self.area_title.setProperty("class", "FieldLabel")
        if self._geo_ok and self.geo_tree:
            card_layout.addWidget(self.area_title)
            self.areas = ServiceAreasPicker(self.geo_tree)  # ← הרכיב החדש
            card_layout.addWidget(self.areas, 1)
        else:
            self.areas = None
            self.area_title.hide()

        # --- שם משתמש/סיסמה ---
        self.ed_user = add_field("שם משתמש *", QLineEdit())
        self.ed_pass = add_field("סיסמה *", QLineEdit()); self.ed_pass.setEchoMode(QLineEdit.Password)

        # --- שגיאה + כפתור ---
        self.lbl_msg = QLabel("", objectName="Error", alignment=Qt.AlignCenter); self.lbl_msg.hide()
        card_layout.addWidget(self.lbl_msg)

        self.btn_save = QPushButton("שמור פרטי ספק", objectName="Primary")
        card_layout.addWidget(self.btn_save)

        # wiring
        self._toggle_role_ui()
        self.rb_supplier.toggled.connect(self._toggle_role_ui)
        self.btn_save.clicked.connect(self._submit)

    # ----- UI helpers -----
    def _toggle_role_ui(self):
        is_supplier = self.rb_supplier.isChecked()
        self.btn_save.setText("שמור פרטי ספק" if is_supplier else "שמור בעל חנות")

        self._set_visible(self.ed_company, is_supplier)
        if self.areas:
            self.area_title.setVisible(is_supplier)
            self.areas.setVisible(is_supplier)

        owner_widgets = [self.ed_city, self.ed_street, self.ed_house, self.ed_open, self.ed_close]
        for w in owner_widgets:
            self._set_visible(w, not is_supplier)

    def _set_visible(self, widget, visible: bool):
        widget.setVisible(visible)
        if widget in self._labels:
            self._labels[widget].setVisible(visible)

    # ----- Submit -----
    def _submit(self):
        import re
        role = "Supplier" if self.rb_supplier.isChecked() else "StoreOwner"
        email = self.ed_email.text().strip()

        # ולידציה בסיסית
        if not self.ed_contact.text().strip() or not self.ed_phone.text().strip() or \
           not self.ed_user.text().strip() or not self.ed_pass.text().strip():
            return self._err("יש למלא את כל שדות החובה")
        if not re.match(r"^[^\s@]+@[^\s@]+\.[^\s@]{2,}$", email):
            return self._err("אימייל לא תקין")

        payload = {
            "username": self.ed_user.text().strip(),
            "email": email,
            "password": self.ed_pass.text().strip(),
            "companyName": self.ed_company.text().strip() if role == "Supplier" else None,
            "contactName": self.ed_contact.text().strip(),
            "phone": self.ed_phone.text().strip(),
            "userType": role,
            "city_id": None, "street": None, "house_number": None,
            "opening_time": None, "closing_time": None,
            "serviceCities": list(self.areas.selected_ids()) if (role == "Supplier" and self.areas) else [],
        }

        if role == "StoreOwner":
            payload.update({
                "city_id": self._resolve_city_id(self.ed_city.text().strip()),
                "street": self.ed_street.text().strip(),
                "house_number": self.ed_house.text().strip(),
                "opening_time": self.ed_open.text().strip(),
                "closing_time": self.ed_close.text().strip(),
            })
            if not payload["city_id"]:
                return self._err("בחרי עיר קיימת")

        ok, user_id, err = self.auth.register_user(payload)
        if ok:
            self.created_username = payload["username"]
            self.created_password = payload["password"]
            self.accept()
        else:
            self._err(err or "שגיאה בהרשמה")

    def _resolve_city_id(self, city_name: str):
        # מאתר city_id מתוך self.geo_tree
        if not (self._geo_ok and self.geo_tree and city_name):
            return None
        for d in self.geo_tree:
            for c in d["cities"]:
                if c["city_name"] == city_name:
                    return c["city_id"]
        return None

    def _err(self, msg: str):
        self.lbl_msg.setText(msg)
        self.lbl_msg.show()
        return False
