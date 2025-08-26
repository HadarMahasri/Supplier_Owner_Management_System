# frontend/views/signup_dialog.py
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QRadioButton,
    QButtonGroup, QFrame, QListWidget, QListWidgetItem, QCheckBox, QScrollArea, QWidget
)
from PySide6.QtCore import Qt
from services.auth_service import AuthService
from services.geo_service import fetch_districts_with_cities

class SignUpDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("הרשמה – ספקים וחנויות")
        self.setFixedSize(720, 750)
        self.auth = AuthService()
        self.geo_tree = fetch_districts_with_cities()
        self.selected_city_ids = set()

        # עיצוב מבוסס על SignUp.module.css
        self.setStyleSheet("""
            QDialog { 
                background: #f3f4f6;
                font-family: 'Segoe UI', Arial, sans-serif;
                direction: rtl;
            }
            
            QFrame#Card { 
                background: #fff;
                border-radius: 16px;
                box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);
                padding: 32px;
            }
            
            QLineEdit { 
                width: 100%;
                padding: 10px 12px;
                border: 1px solid #e2e8f0;
                border-radius: 10px;
                font-size: 14px;
                background-color: white;
            }
            
            QLineEdit:focus { 
                border-color: #3b82f6;
                box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.15);
                outline: none;
            }
            
            QPushButton { 
                width: 100%;
                padding: 12px 16px;
                border: none;
                border-radius: 12px;
                font-weight: 600;
                font-size: 15px;
                cursor: pointer;
            }
            
            QPushButton#Primary { 
                background: #2563eb;
                color: #fff;
                margin-top: 20px;
            }
            
            QPushButton#Primary:hover { 
                background: #1d4ed8;
            }
            
            QLabel#Title { 
                font-size: 24px;
                font-weight: 700;
                color: #1e293b;
                text-align: center;
                margin-bottom: 20px;
            }
            
            QLabel#FieldLabel {
                display: block;
                font-weight: 600;
                margin: 12px 0 6px;
                color: #374151;
                font-size: 14px;
            }
            
            QLabel#Required {
                color: #dc2626;
                font-size: 14px;
            }
            
            QLabel#Error {
                color: #dc2626;
                font-size: 13px;
                padding: 8px;
                background-color: #fef2f2;
                border-radius: 8px;
                margin-top: 8px;
            }
            
            QRadioButton {
                font-weight: 600;
                font-size: 14px;
                color: #334155;
                margin: 0 12px;
            }
            
            QScrollArea {
                border: 1px solid #e2e8f0;
                border-radius: 12px;
                background: #f9fafb;
                max-height: 280px;
            }
            
            QCheckBox {
                font-size: 14px;
                color: #334155;
                padding: 4px;
            }
            
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
                border-radius: 4px;
            }
            
            QLabel#DistrictHeader {
                font-weight: 600;
                color: #374151;
                margin: 8px 0;
            }
        """)

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 20)
        
        # ScrollArea ראשי
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        
        card = QFrame(objectName="Card")
        v = QVBoxLayout(card)
        v.setSpacing(12)

        v.addWidget(QLabel("הרשמה", objectName="Title", alignment=Qt.AlignCenter))

        # בחירת תפקיד
        role_row = QHBoxLayout()
        role_row.setSpacing(24)
        self.rb_supplier = QRadioButton("ספק")
        self.rb_owner = QRadioButton("בעל מכולת")
        self.rb_supplier.setChecked(True)
        self._role_group = QButtonGroup(self)
        self._role_group.addButton(self.rb_supplier)
        self._role_group.addButton(self.rb_owner)
        role_row.addStretch(1)
        role_row.addWidget(self.rb_supplier)
        role_row.addWidget(self.rb_owner)
        role_row.addStretch(1)
        v.addLayout(role_row)

        # שדות משותפים
        self.ed_company = QLineEdit(placeholderText="שם חברה")
        self._add_field(v, "שם החברה", self.ed_company)
        self.ed_contact = QLineEdit(placeholderText="שם איש קשר")
        self._add_field(v, "איש קשר *", self.ed_contact, required=True)
        self.ed_phone = QLineEdit(placeholderText="טלפון")
        self._add_field(v, "טלפון *", self.ed_phone, required=True)
        self.ed_email = QLineEdit(placeholderText="name@example.com")
        self._add_field(v, "אימייל *", self.ed_email, required=True)

        # שדות בעל חנות
        self.ed_city = QLineEdit(placeholderText="הקלידי שם עיר...")
        self._add_field(v, "עיר *", self.ed_city, required=True)
        self.ed_street = QLineEdit(placeholderText="רחוב")
        self._add_field(v, "רחוב *", self.ed_street, required=True)
        self.ed_house = QLineEdit(placeholderText="מספר בית")
        self._add_field(v, "מספר בית *", self.ed_house, required=True)
        
        # שעות פעילות בשורה אחת
        hours_layout = QHBoxLayout()
        hours_layout.setSpacing(16)
        
        open_box = QVBoxLayout()
        self.ed_open = QLineEdit(placeholderText="HH:MM")
        self._add_field(open_box, "שעת פתיחה *", self.ed_open, required=True)
        
        close_box = QVBoxLayout()
        self.ed_close = QLineEdit(placeholderText="HH:MM")
        self._add_field(close_box, "שעת סגירה *", self.ed_close, required=True)
        
        hours_layout.addLayout(open_box)
        hours_layout.addLayout(close_box)
        v.addLayout(hours_layout)

        # אזורי שירות לספק
        self.area_label = QLabel("אזורי שירות (בחרי מחוזות שלמים או ערים ספציפיות):")
        self.area_label.setObjectName("FieldLabel")
        self.area_label.setStyleSheet("font-weight: 700; color: #1f2937; margin-top: 20px;")
        v.addWidget(self.area_label)
        
        self.area_scroll = QScrollArea()
        self.area_scroll.setWidgetResizable(True)
        self.area_scroll.setMaximumHeight(280)
        area = QWidget()
        area_layout = QVBoxLayout(area)
        area_layout.setSpacing(12)
        
        self._city_checkboxes = []
        for d in self.geo_tree:
            # כותרת מחוז
            district_label = QLabel(f"🏢 {d['district_name']} ({len(d['cities'])} ערים)")
            district_label.setObjectName("DistrictHeader")
            area_layout.addWidget(district_label)
            
            # ערים במחוז
            cities_layout = QVBoxLayout()
            cities_layout.setContentsMargins(20, 0, 0, 0)
            for c in d["cities"]:
                cb = QCheckBox(c["city_name"])
                cb.stateChanged.connect(lambda state, cid=c["city_id"]: self._toggle_city(cid, state))
                self._city_checkboxes.append(cb)
                cities_layout.addWidget(cb)
            area_layout.addLayout(cities_layout)
        
        self.area_scroll.setWidget(area)
        v.addWidget(self.area_scroll)

        # שם משתמש וסיסמה
        self.ed_user = QLineEdit(placeholderText="בחרי שם משתמש")
        self._add_field(v, "שם משתמש *", self.ed_user, required=True)
        self.ed_pass = QLineEdit(placeholderText="בחרי סיסמה")
        self.ed_pass.setEchoMode(QLineEdit.Password)
        self._add_field(v, "סיסמה *", self.ed_pass, required=True)

        # הודעת שגיאה
        self.lbl_msg = QLabel("", alignment=Qt.AlignCenter, objectName="Error")
        self.lbl_msg.hide()
        v.addWidget(self.lbl_msg)

        # כפתור שמירה
        btn = QPushButton("שמור פרטי ספק", objectName="Primary")
        v.addWidget(btn)
        
        scroll_layout.addWidget(card)
        scroll.setWidget(scroll_widget)
        root.addWidget(scroll)

        # התאמת שדות לפי תפקיד
        self._toggle_role_ui()
        self.rb_supplier.toggled.connect(self._toggle_role_ui)
        btn.clicked.connect(self._submit)

    def _add_field(self, layout, label_text, widget, required=False):
        """פונקציה עזר להוספת שדה עם תווית"""
        label = QLabel(label_text)
        label.setObjectName("FieldLabel")
        if required and "*" not in label_text:
            label.setText(label_text + " *")
        layout.addWidget(label)
        layout.addWidget(widget)
        return widget

    def _toggle_role_ui(self):
        is_supplier = self.rb_supplier.isChecked()
        
        # עדכון טקסט כפתור
        btn = self.findChild(QPushButton, "Primary")
        if btn:
            btn.setText("שמור פרטי ספק" if is_supplier else "שמור בעל חנות")
        
        # הצג/הסתר שדות רלוונטיים
        self.ed_company.setVisible(is_supplier)
        self.ed_company.previousInFocusChain().setVisible(is_supplier)  # התווית
        
        # שדות בעל חנות
        owner_widgets = [
            self.ed_city, self.ed_street, self.ed_house, 
            self.ed_open, self.ed_close
        ]
        for w in owner_widgets:
            w.setVisible(not is_supplier)
            if w.previousInFocusChain():
                w.previousInFocusChain().setVisible(not is_supplier)
        
        # אזורי שירות
        self.area_label.setVisible(is_supplier)
        self.area_scroll.setVisible(is_supplier)

    def _toggle_city(self, cid: int, state: int):
        if state:
            self.selected_city_ids.add(cid)
        else:
            self.selected_city_ids.discard(cid)

    def _submit(self):
        role = "Supplier" if self.rb_supplier.isChecked() else "StoreOwner"
        email = self.ed_email.text().strip()
        import re
        
        # בדיקות תקינות
        if not self.ed_contact.text().strip() or not self.ed_phone.text().strip() or \
           not self.ed_user.text().strip() or not self.ed_pass.text().strip():
            self.lbl_msg.setText("יש למלא את כל שדות החובה")
            self.lbl_msg.show()
            return
            
        if not re.match(r"^[^\s@]+@[^\s@]+\.[^\s@]{2,}$", email):
            self.lbl_msg.setText("אימייל לא תקין")
            self.lbl_msg.show()
            return

        payload = {
            "username": self.ed_user.text().strip(),
            "email": email,
            "password": self.ed_pass.text().strip(),
            "companyName": self.ed_company.text().strip() if self.rb_supplier.isChecked() else None,
            "contactName": self.ed_contact.text().strip(),
            "phone": self.ed_phone.text().strip(),
            "userType": role,
            "city_id": None,
            "street": None,
            "house_number": None,
            "opening_time": None,
            "closing_time": None,
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
                self.lbl_msg.setText("בחרי עיר קיימת")
                self.lbl_msg.show()
                return

        ok, user_id, err = self.auth.register_user(payload)
        if ok:
            self.accept()
        else:
            self.lbl_msg.setText(err or "שגיאה בהרשמה")
            self.lbl_msg.show()

    def _resolve_city_id(self, city_name: str):
        for d in self.geo_tree:
            for c in d["cities"]:
                if c["city_name"] == city_name:
                    return c["city_id"]
        return None