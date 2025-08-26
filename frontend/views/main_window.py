# frontend/views/main_window.py
from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QLabel, 
                               QPushButton, QTableWidget, QTableWidgetItem,
                               QLineEdit, QHBoxLayout, QMessageBox, QInputDialog)
from PySide6.QtCore import Qt
from services.api_client import APIClient  # אם יש לך קובץ כזה (לקריאת ספקים)
import requests
import uuid

class MainWindow(QMainWindow):
    def __init__(self, current_user: dict | None = None):
        super().__init__()
        self.api_client = APIClient() if 'APIClient' in globals() else None
        self.current_user = current_user or {}
        self.setWindowTitle("מערכת ניהול ספקים")
        self.setGeometry(100, 100, 1200, 800)

        self.setup_ui()
        self.load_suppliers()

    def setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        # Title + logged-in user
        title = QLabel("מערכת ניהול ספקים")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 24px; font-weight: bold; margin: 6px;")
        layout.addWidget(title)

        if self.current_user:
            who = self.current_user.get("company_name") or self.current_user.get("username", "משתמש")
            role_he = "ספק" if self.current_user.get("role") == "Supplier" else "בעל/ת חנות"
            lbl_user = QLabel(f"מחובר/ת: {who} ({role_he})")
            lbl_user.setAlignment(Qt.AlignCenter)
            lbl_user.setStyleSheet("color:#6b7280; margin-bottom:8px;")
            layout.addWidget(lbl_user)

        # Search + Add
        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("חיפוש ספק...")

        self.search_button = QPushButton("חיפוש")
        self.search_button.clicked.connect(self.search_suppliers)

        self.add_button = QPushButton("➕ הוסף ספק")
        self.add_button.setStyleSheet(
            "QPushButton { background-color: #28a745; padding: 10px; font-weight: bold; }"
        )
        self.add_button.clicked.connect(self.add_supplier)

        search_layout.addWidget(self.search_input)
        search_layout.addWidget(self.search_button)
        search_layout.addWidget(self.add_button)
        layout.addLayout(search_layout)

        # Table
        self.suppliers_table = QTableWidget()
        self.suppliers_table.setColumnCount(5)
        self.suppliers_table.setHorizontalHeaderLabels(["שם הספק", "קטגוריה", "עיר", "דירוג", "טלפון"])
        layout.addWidget(self.suppliers_table)

        self.suppliers_table.itemDoubleClicked.connect(self.on_supplier_double_clicked)

    def load_suppliers(self):
        suppliers = self.api_client.get_suppliers() if self.api_client else []
        self.display_suppliers(suppliers)

    def search_suppliers(self):
        term = self.search_input.text()
        suppliers = self.api_client.get_suppliers(search_term=term) if self.api_client else []
        self.display_suppliers(suppliers)

    def display_suppliers(self, suppliers):
        self.suppliers_table.setRowCount(len(suppliers))
        for row, supplier in enumerate(suppliers):
            self.suppliers_table.setItem(row, 0, QTableWidgetItem(supplier.get('name', '')))
            self.suppliers_table.setItem(row, 1, QTableWidgetItem(supplier.get('category', '')))
            city = supplier.get('address', {}).get('city', '') if supplier.get('address') else ''
            self.suppliers_table.setItem(row, 2, QTableWidgetItem(city))
            rating = f"{supplier.get('rating', 0):.1f} ⭐"
            self.suppliers_table.setItem(row, 3, QTableWidgetItem(rating))
            phone = supplier.get('contact_info', {}).get('phone', '') if supplier.get('contact_info') else ''
            self.suppliers_table.setItem(row, 4, QTableWidgetItem(phone))
        self.suppliers_table.resizeColumnsToContents()

    def add_supplier(self):
        name, ok = QInputDialog.getText(self, 'הוספת ספק', 'שם הספק:')
        if not ok or not name.strip():
            return
        phone, ok = QInputDialog.getText(self, 'הוספת ספק', 'מספר טלפון:')
        if not ok or not phone.strip():
            return
        categories = ["מזון ומשקאות", "בנייה ותשתיות", "טכנולוגיה וציוד"]
        category, ok = QInputDialog.getItem(self, 'הוספת ספק', 'בחר קטגוריה:', categories)
        if not ok:
            return
        city, ok = QInputDialog.getText(self, 'הוספת ספק', 'עיר:')
        if not ok:
            city = "לא צוין"

        try:
            supplier_data = {
                "id": str(uuid.uuid4()),
                "name": name.strip(),
                "category": category,
                "contact_info": {"phone": phone.strip()},
                "address": {"city": city.strip()},
                "rating": 4.0,
                "review_count": 0
            }
            # דוגמה – אם יש לך שרת FastAPI רץ לכתובת הזו
            res = requests.post("http://localhost:8000/api/v1/suppliers", json=supplier_data)
            if res.status_code in (200, 201):
                from PySide6.QtWidgets import QMessageBox
                QMessageBox.information(self, "הצלחה", f"הספק '{name}' נוסף בהצלחה")
                self.load_suppliers()
            else:
                from PySide6.QtWidgets import QMessageBox
                QMessageBox.warning(self, "שגיאה", "שגיאה בשמירה")
        except Exception as e:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.critical(self, "שגיאה", f"שגיאה: {e}")

    def on_supplier_double_clicked(self, item):
        row = item.row()
        supplier_name = self.suppliers_table.item(row, 0).text()
        from PySide6.QtWidgets import QMessageBox
        QMessageBox.information(self, "פרטי ספק", f"ספק: {supplier_name}")
