# frontend/views/signup_dialog.py
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QRadioButton,
    QButtonGroup, QFrame, QScrollArea, QWidget, QCheckBox
)
from PySide6.QtCore import Qt
from services.auth_service import AuthService


class SignUpDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("הרשמה – ספקים וחנויות")
        self.resize(720, 760)
        self.setMinimumSize(620, 620)

        self.auth = AuthService()
        self.created_username = None
        self.created_password = None

        # --- נסיון לטעון גיאוגרפיה; אם נכשל – לא קורסים ---
        self.geo_tree = []
        self._geo_ok = True
        try:
            from services.geo_service import fetch_districts_with_cities
            self.geo_tree = fetch_districts_with_cities()
        except Exception:
            self._geo_ok = False
        self.selected_city_ids = set()

        # --- עיצוב ---
        self.setStyleSheet("""
            QDialog {
                background: #f3f4f6;
                font-family: 'Segoe UI', Arial, sans-serif;
                direction: rtl;
            }
            QFrame#Card {
                background: #fff;
                border-radius: 16px;
                border: 1px solid rgba(0,0,0,0.06);
            }
            QLabel#Title { font-size: 22px; font-weight: 800; color: #1f2937; }
            QLabel.FieldLabel { font-weight: 600; color: #374151; margin: 12px 0 6px; }
            QLabel#Error { color:#dc2626; font-size:13px; padding:8px; background:#fef2f2; border-radius:8px; }
            QLineEdit {
                padding: 10px 12px; border: 1px solid #e2e8f0; border-radius: 8px; font-size: 14px;
            }
            QLineEdit:focus {
                border-color: #3b82f6; box-shadow: 0 0 0 3px rgba(59,130,246,.15);
            }
            QRadioButton { font-weight:600; color:#334155; margin: 0 10px; }
            QScrollArea { border: 1px solid #e2e8f0; border-radius: 12px; background: #f9fafb; }
            QPushButton { padding: 12px 16px; border-radius: 10px; font-weight: 700; border: none; }
            QPushButton#Primary { background:#2563eb; color:#fff; }
            QPushButton#Primary:hover { background:#1d4ed8; }
        """)

        # --- מבנה כללי עם גלילה ---
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 20)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        root.addWidget(scroll)

        host = QWidget()
        scroll.setWidget(host)
        host_layout = QVBoxLayout(host)

        card = QFrame(objectName="Card")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(24, 24, 24, 24)
        card_layout.setSpacing(12)
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

        # --- בנאי שדות: שומר גם את התוויות כדי להסתיר/להציג נכון ---
        self._labels = {}
        def add_field(container_layout, label_text, widget):
            lbl = QLabel(label_text); lbl.setProperty("class", "FieldLabel"); lbl.setObjectName("FieldLabel")
            lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            container_layout.addWidget(lbl)
            container_layout.addWidget(widget)
            self._labels[widget] = lbl
            return widget

        # --- שדות משותפים ---
        self.ed_company = add_field(card_layout, "שם החברה (לספק, אופציונלי)", QLineEdit())
        self.ed_contact = add_field(card_layout, "איש קשר *", QLineEdit())
        self.ed_phone   = add_field(card_layout, "טלפון *", QLineEdit())
        self.ed_email   = add_field(card_layout, "אימייל *", QLineEdit("name@example.com"))

        # --- שדות בעל חנות ---
        self.ed_city   = add_field(card_layout, "עיר *", QLineEdit("הקלידי שם עיר..."))
        self.ed_street = add_field(card_layout, "רחוב *", QLineEdit())
        self.ed_house  = add_field(card_layout, "מספר בית *", QLineEdit())

        hours_row = QHBoxLayout()
        self.ed_open = QLineEdit("HH:MM")
        self.ed_close = QLineEdit("HH:MM")
        hours_col1 = QVBoxLayout(); hours_col1.addWidget(QLabel("שעת פתיחה *", alignment=Qt.AlignRight)); hours_col1.addWidget(self.ed_open)
        hours_col2 = QVBoxLayout(); hours_col2.addWidget(QLabel("שעת סגירה *", alignment=Qt.AlignRight)); hours_col2.addWidget(self.ed_close)
        hours_row.addLayout(hours_col1); hours_row.addLayout(hours_col2)
        card_layout.addLayout(hours_row)
        # נשמור גם את תוויות השעות במפה כדי לשלוט בהצגה
        self._labels[self.ed_open]  = hours_col1.itemAt(0).widget()
        self._labels[self.ed_close] = hours_col2.itemAt(0).widget()

        # --- אזורי שירות לספק (אם נטענו) ---
        self.area_label = QLabel("אזורי שירות (לספק): בחרי ערים"); self.area_label.setProperty("class", "FieldLabel")
        if self._geo_ok and self.geo_tree:
            card_layout.addWidget(self.area_label)
            self.area_scroll = QScrollArea(); self.area_scroll.setWidgetResizable(True); self.area_scroll.setMaximumHeight(260)
            area = QWidget(); area_layout = QVBoxLayout(area); area_layout.setContentsMargins(12, 8, 12, 8)
            self._city_checkboxes = []
            for d in self.geo_tree:
                hdr = QLabel(f"— {d['district_name']} —"); hdr.setStyleSheet("font-weight:600; color:#374151; margin:6px 0;")
                area_layout.addWidget(hdr)
                for c in d["cities"]:
                    cb = QCheckBox(c["city_name"])
                    cb.stateChanged.connect(lambda st, cid=c["city_id"]: self._toggle_city(cid, st))
                    self._city_checkboxes.append(cb)
                    area_layout.addWidget(cb)
            self.area_scroll.setWidget(area)
            card_layout.addWidget(self.area_scroll)
        else:
            # פלייסהולדר אם אין גיאוגרפיה – שלא נקרוס
            self.area_scroll = QWidget()
            self.area_label.hide()
            self.area_scroll.hide()

        # --- שם משתמש וסיסמה ---
        self.ed_user = add_field(card_layout, "שם משתמש *", QLineEdit())
        self.ed_pass = add_field(card_layout, "סיסמה *", QLineEdit())
        self.ed_pass.setEchoMode(QLineEdit.Password)

        # --- הודעת שגיאה ---
        self.lbl_msg = QLabel("", objectName="Error", alignment=Qt.AlignCenter)
        self.lbl_msg.hide()
        card_layout.addWidget(self.lbl_msg)

        # --- כפתור שמירה ---
        self.btn_save = QPushButton("שמור פרטי ספק", objectName="Primary")
        card_layout.addWidget(self.btn_save)

        # --- חיבורים ---
        self._toggle_role_ui()
        self.rb_supplier.toggled.connect(self._toggle_role_ui)
        self.btn_save.clicked.connect(self._submit)

    # ----- UI helpers -----
    def _toggle_role_ui(self):
        is_supplier = self.rb_supplier.isChecked()

        # כפתור
        self.btn_save.setText("שמור פרטי ספק" if is_supplier else "שמור בעל חנות")

        # ספק: מציגים שם חברה + אזורי שירות, מסתירים פרטי חנות
        self._set_visible(self.ed_company, is_supplier)
        self.area_label.setVisible(is_supplier and self._geo_ok)
        self.area_scroll.setVisible(is_supplier and self._geo_ok)

        owner_widgets = [self.ed_city, self.ed_street, self.ed_house, self.ed_open, self.ed_close]
        for w in owner_widgets:
            self._set_visible(w, not is_supplier)

    def _set_visible(self, widget, visible: bool):
        widget.setVisible(visible)
        if widget in self._labels:
            self._labels[widget].setVisible(visible)

    def _toggle_city(self, cid: int, state: int):
        if state:
            self.selected_city_ids.add(cid)
        else:
            self.selected_city_ids.discard(cid)

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
            "serviceCities": list(self.selected_city_ids) if role == "Supplier" else [],
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
            # כדי שה-Login ימלא אוטומטית
            self.created_username = payload["username"]
            self.created_password = payload["password"]
            self.accept()
        else:
            self._err(err or "שגיאה בהרשמה")

    def _resolve_city_id(self, city_name: str):
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
