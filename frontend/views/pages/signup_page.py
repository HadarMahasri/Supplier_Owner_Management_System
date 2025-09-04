# frontend/views/pages/signup_page.py
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QRadioButton, QButtonGroup, QFrame, QScrollArea, QSizePolicy, QSpacerItem,
    QGridLayout
)
from PySide6.QtCore import Qt, Signal
from services.auth_service import AuthService
from views.widgets.service_areas_picker import ServiceAreasPicker


class SignUpPage(QWidget):
    back_to_login = Signal()
    signup_success = Signal(str, str)  # username, password

    def __init__(self):
        super().__init__()
        self.auth = AuthService()
        self._geo_ok, self.geo_tree = self._load_geo()

        self.setLayoutDirection(Qt.RightToLeft)
        self.setup_ui()
        self.setup_signals()

    def setup_ui(self):
        # ========== MAIN LAYOUT ==========
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(0)

        # ========== SCROLL AREA ==========
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setFrameShape(QFrame.NoFrame)

        # ========== CONTENT WIDGET ==========
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        # מרווח עליון
        content_layout.addItem(QSpacerItem(0, 20, QSizePolicy.Minimum, QSizePolicy.Fixed))

        # ========== CARD ==========
        card = QFrame()
        card.setObjectName("MainCard")
        card.setMinimumWidth(750)
        card.setMaximumWidth(750)
        card.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Preferred)

        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(40, 30, 40, 30)
        card_layout.setSpacing(20)

        # ========== STYLES ==========
        self.setStyleSheet("""
            QWidget {
                font-family: 'Segoe UI', 'Arial Hebrew', sans-serif;
                font-size: 14px;
                background: transparent;
            }
            
            QFrame#MainCard {
                background-color: white;
                border: 1px solid #ddd;
                border-radius: 12px;
            }
            
            QLabel#MainTitle {
                font-size: 24px;
                font-weight: bold;
                color: #333;
                margin-bottom: 10px;
            }
            
            QLabel#SectionTitle {
                font-size: 16px;
                font-weight: bold;
                color: #444;
                margin: 15px 0 8px 0;
                padding-bottom: 5px;
                border-bottom: 2px solid #e0e0e0;
            }
            
            QLabel#FieldLabel {
                font-size: 13px;
                font-weight: 600;
                color: #555;
                margin: 5px 0 3px 0;
                text-align: right;
            }
            
            QLineEdit {
                padding: 10px 12px;
                border: 1px solid #ccc;
                border-radius: 6px;
                font-size: 14px;
                background-color: white;
                margin-bottom: 8px;
            }
            
            QLineEdit:focus {
                border-color: #4285f4;
                background-color: #fafbff;
            }
            
            QRadioButton {
                font-size: 14px;
                font-weight: 600;
                padding: 8px;
                margin: 5px 10px;
            }
            
            QPushButton {
                padding: 12px 24px;
                border: none;
                border-radius: 6px;
                font-size: 14px;
                font-weight: 600;
            }
            
            QPushButton#PrimaryButton {
                background-color: #4285f4;
                color: white;
            }
            
            QPushButton#PrimaryButton:hover {
                background-color: #3367d6;
            }
            
            QPushButton#SecondaryButton {
                background-color: transparent;
                color: #4285f4;
                text-decoration: underline;
            }
            
            QPushButton#SecondaryButton:hover {
                background-color: #f0f4ff;
            }
            
            QLabel#ErrorLabel {
                color: #d93025;
                background-color: #fce8e6;
                border: 1px solid #f5c6cb;
                border-radius: 6px;
                padding: 10px;
                margin: 8px 0;
            }
            
            QFrame#ServiceFrame {
                background-color: #f8f9fa;
                border: 1px solid #e0e0e0;
                border-radius: 8px;
                padding: 10px;
                margin: 8px 0;
            }
            
            QScrollArea {
                border: none;
                background-color: transparent;
            }
            
            /* יישור ימני לכל האלמנטים בתוך אזור השירות */
            QFrame#ServiceFrame * {
                text-align: right;
            }
        """)

        # ========== TITLE ==========
        title = QLabel("רישום למערכת")
        title.setObjectName("MainTitle")
        title.setAlignment(Qt.AlignCenter)
        card_layout.addWidget(title)

        # ========== ROLE SELECTION ==========
        role_section = QLabel("בחר סוג משתמש")
        role_section.setObjectName("SectionTitle")
        card_layout.addWidget(role_section)

        role_layout = QHBoxLayout()
        role_layout.addStretch()
        
        self.rb_supplier = QRadioButton("ספק")
        self.rb_owner = QRadioButton("בעל חנות")
        self.rb_supplier.setChecked(True)
        
        role_group = QButtonGroup(self)
        role_group.addButton(self.rb_supplier)
        role_group.addButton(self.rb_owner)
        
        role_layout.addWidget(self.rb_owner)
        role_layout.addWidget(self.rb_supplier)
        role_layout.addStretch()
        card_layout.addLayout(role_layout)

        # ========== GENERAL INFO ==========
        general_section = QLabel("מידע כללי")
        general_section.setObjectName("SectionTitle")
        card_layout.addWidget(general_section)

        # שימוש ב-Grid Layout לשדות (2 עמודות)
        general_grid = QGridLayout()
        general_grid.setSpacing(15)
        general_grid.setColumnStretch(0, 1)
        general_grid.setColumnStretch(1, 1)

        # יצירת שדות בשתי עמודות
        self.create_field_in_grid(general_grid, 0, 0, "איש קשר *", "ed_contact")
        self.create_field_in_grid(general_grid, 0, 1, "טלפון *", "ed_phone")
        self.create_field_in_grid(general_grid, 1, 0, "אימייל *", "ed_email")
        self.create_field_in_grid(general_grid, 1, 1, "שם החברה (אופציונלי)", "ed_company")

        card_layout.addLayout(general_grid)

        # ========== STORE INFO (FOR OWNERS) ==========
        self.store_section = QLabel("פרטי החנות")
        self.store_section.setObjectName("SectionTitle")
        card_layout.addWidget(self.store_section)

        self.store_grid = QGridLayout()
        self.store_grid.setSpacing(15)
        self.store_grid.setColumnStretch(0, 1)
        self.store_grid.setColumnStretch(1, 1)

        self.create_field_in_grid(self.store_grid, 0, 0, "עיר *", "ed_city")
        self.create_field_in_grid(self.store_grid, 0, 1, "רחוב *", "ed_street")
        self.create_field_in_grid(self.store_grid, 1, 0, "מספר בית *", "ed_house")

        # שעות פתיחה בשורה אחת
        hours_widget = QWidget()
        hours_layout = QHBoxLayout(hours_widget)
        hours_layout.setContentsMargins(0, 0, 0, 0)

        # שעת פתיחה
        open_layout = QVBoxLayout()
        open_label = QLabel("שעת פתיחה *")
        open_label.setObjectName("FieldLabel")
        self.ed_open = QLineEdit("08:00")
        open_layout.addWidget(open_label)
        open_layout.addWidget(self.ed_open)

        # שעת סגירה
        close_layout = QVBoxLayout()
        close_label = QLabel("שעת סגירה *")
        close_label.setObjectName("FieldLabel")
        self.ed_close = QLineEdit("20:00")
        close_layout.addWidget(close_label)
        close_layout.addWidget(self.ed_close)

        hours_layout.addLayout(open_layout)
        hours_layout.addLayout(close_layout)
        hours_layout.addStretch()

        self.store_grid.addWidget(hours_widget, 1, 1, 1, 1)
        card_layout.addLayout(self.store_grid)

        # ========== SERVICE AREAS (FOR SUPPLIERS) ==========
        self.service_section = QLabel("אזורי שירות")
        self.service_section.setObjectName("SectionTitle")
        card_layout.addWidget(self.service_section)

        self.service_frame = QFrame()
        self.service_frame.setObjectName("ServiceFrame")
        service_layout = QVBoxLayout(self.service_frame)

        service_desc = QLabel("בחר את האזורים בהם תספק שירותים:")
        service_desc.setStyleSheet("color: #666; font-size: 13px; text-align: right;")
        service_desc.setAlignment(Qt.AlignRight)
        service_layout.addWidget(service_desc)

        self.area_scroll = QScrollArea()
        self.area_scroll.setWidgetResizable(True)
        self.area_scroll.setMinimumHeight(200)
        self.area_scroll.setMaximumHeight(300)
        self.area_scroll.setLayoutDirection(Qt.RightToLeft)  # חשוב: גלילה RTL כדי להצמיד לימין

        if self._geo_ok and self.geo_tree:
            self.areas = ServiceAreasPicker(self.geo_tree)
            # יישור ימני לכל תוכן הווידג'ט
            self.areas.setLayoutDirection(Qt.RightToLeft)
            self.area_scroll.setWidget(self.areas)
        else:
            self.areas = None
            self.service_section.hide()
            self.service_frame.hide()

        service_layout.addWidget(self.area_scroll)
        card_layout.addWidget(self.service_frame)

        # ========== LOGIN INFO ==========
        login_section = QLabel("פרטי התחברות")
        login_section.setObjectName("SectionTitle")
        card_layout.addWidget(login_section)

        login_grid = QGridLayout()
        login_grid.setSpacing(15)
        login_grid.setColumnStretch(0, 1)
        login_grid.setColumnStretch(1, 1)

        self.create_field_in_grid(login_grid, 0, 0, "שם משתמש *", "ed_user")
        self.create_field_in_grid(login_grid, 0, 1, "סיסמה *", "ed_pass", is_password=True)

        card_layout.addLayout(login_grid)

        # ========== ERROR MESSAGE ==========
        self.lbl_err = QLabel()
        self.lbl_err.setObjectName("ErrorLabel")
        self.lbl_err.hide()
        card_layout.addWidget(self.lbl_err)

        # ========== BUTTONS ==========
        button_layout = QHBoxLayout()
        
        self.btn_cancel = QPushButton("ביטול")
        self.btn_cancel.setObjectName("SecondaryButton")
        
        button_layout.addWidget(self.btn_cancel)
        button_layout.addStretch()
        
        self.btn_submit = QPushButton("יצירת חשבון")
        self.btn_submit.setObjectName("PrimaryButton")
        
        button_layout.addWidget(self.btn_submit)
        card_layout.addLayout(button_layout)

        # ========== FINAL LAYOUT ==========
        content_layout.addWidget(card, 0, Qt.AlignCenter)
        content_layout.addItem(QSpacerItem(0, 20, QSizePolicy.Minimum, QSizePolicy.Expanding))

        scroll.setWidget(content_widget)
        main_layout.addWidget(scroll)

    def create_field_in_grid(self, grid_layout, row, col, label_text, field_name, is_password=False):
        container = QWidget()
        container_layout = QHBoxLayout(container)  # שינוי מ-QVBoxLayout ל-QHBoxLayout
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(8)
        container.setLayoutDirection(Qt.RightToLeft)

        label = QLabel(label_text)
        label.setObjectName("FieldLabel")
        label.setAlignment(Qt.AlignRight)
        label.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Preferred)  # רוחב קבוע לתווית
        label.setMinimumWidth(120)  # רוחב מינימום לתווית

        field = QLineEdit()
        if is_password:
            field.setEchoMode(QLineEdit.Password)
        field.setAlignment(Qt.AlignRight)
        field.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)  # השדה יתרחב

        # הוספת התווית והשדה לפריסה אופקית
        container_layout.addWidget(label)
        container_layout.addWidget(field)

        setattr(self, field_name, field)
        grid_layout.addWidget(container, row, col)

    def create_field(self, grid_layout, row, label_text, field_name, is_password=False):
        """יוצר שדה עם תווית בגריד"""
        label = QLabel(label_text)
        label.setObjectName("FieldLabel")
        
        field = QLineEdit()
        if is_password:
            field.setEchoMode(QLineEdit.Password)
        
        # שמירת הפניה לשדה
        setattr(self, field_name, field)
        
        grid_layout.addWidget(label, row * 2, 0)
        grid_layout.addWidget(field, row * 2 + 1, 0)

    def setup_signals(self):
        """הגדרת אירועים"""
        self.rb_supplier.toggled.connect(self._toggle_role_ui)
        self._toggle_role_ui()  # הפעלה ראשונית
        
        self.btn_cancel.clicked.connect(self.back_to_login.emit)
        self.btn_submit.clicked.connect(self._submit)

    def _load_geo(self):
        try:
            from services.geo_service import fetch_districts_with_cities
            return True, fetch_districts_with_cities()
        except Exception:
            return False, []

    def _toggle_role_ui(self):
        """החלפת תצוגה לפי סוג המשתמש"""
        is_supplier = self.rb_supplier.isChecked()
        
        # הצגה/הסתרה של אזורי שירות לספקים
        self.service_section.setVisible(is_supplier and self.areas is not None)
        self.service_frame.setVisible(is_supplier and self.areas is not None)
        
        # הצגה/הסתרה של פרטי חנות לבעלי חנויות
        is_owner = not is_supplier
        self.store_section.setVisible(is_owner)
        
        # הסתרת כל הווידג'טים בגריד
        for i in range(self.store_grid.count()):
            item = self.store_grid.itemAt(i)
            if item and item.widget():
                item.widget().setVisible(is_owner)
        
        # הצגה/הסתרה של שם חברה
        self.ed_company.setVisible(is_supplier)
        # מציאת התווית של שם החברה
        for i in range(self.sender().parent().layout().count() if self.sender() else 10):
            try:
                item = self.layout().itemAt(i)
                if hasattr(item, 'widget') and item.widget():
                    if isinstance(item.widget(), QLabel) and "שם החברה" in item.widget().text():
                        item.widget().setVisible(is_supplier)
                        break
            except:
                pass

    def _submit(self):
        import re
        role = "Supplier" if self.rb_supplier.isChecked() else "StoreOwner"
        email = self.ed_email.text().strip()

        # בדיקת שדות חובה
        if not all([
            self.ed_contact.text().strip(),
            self.ed_phone.text().strip(),
            self.ed_user.text().strip(),
            self.ed_pass.text().strip(),
            email
        ]):
            return self._show_error("יש למלא את כל שדות החובה")

        # בדיקת תקינות אימייל
        if not re.match(r"^[^\s@]+@[^\s@]+\.[^\s@]{2,}$", email):
            return self._show_error("כתובת אימייל לא תקינה")

        # הכנת נתוני הבקשה
        payload = {
            "username": self.ed_user.text().strip(),
            "email": email,
            "password": self.ed_pass.text().strip(),
            "companyName": self.ed_company.text().strip() if role == "Supplier" else None,
            "contactName": self.ed_contact.text().strip(),
            "phone": self.ed_phone.text().strip(),
            "userType": role,
            "city_id": None,
            "street": None,
            "house_number": None,
            "opening_time": None,
            "closing_time": None,
            "serviceCities": list(self.areas.selected_ids()) if (role == "Supplier" and self.areas) else [],
        }

        # נתונים נוספים לבעלי חנויות
        if role == "StoreOwner":
            city_name = self.ed_city.text().strip()
            payload.update({
                "city_id": self._resolve_city_id(city_name),
                "street": self.ed_street.text().strip(),
                "house_number": self.ed_house.text().strip(),
                "opening_time": self.ed_open.text().strip(),
                "closing_time": self.ed_close.text().strip(),
            })
            
            if not payload["city_id"]:
                return self._show_error("יש לבחור עיר תקינה")

        # ביצוע הרישום
        ok, uid, err = self.auth.register_user(payload)
        if ok:
            self.signup_success.emit(payload["username"], payload["password"])
        else:
            self._show_error(err or "אירעה שגיאה ברישום")

    def _resolve_city_id(self, city_name: str):
        """מציאת ID של עיר לפי שם"""
        if not (self._geo_ok and self.geo_tree and city_name):
            return None
        
        for district in self.geo_tree:
            for city in district["cities"]:
                if city["city_name"] == city_name:
                    return city["city_id"]
        return None

    def _show_error(self, message: str):
        """הצגת הודעת שגיאה"""
        self.lbl_err.setText(message)
        self.lbl_err.show()