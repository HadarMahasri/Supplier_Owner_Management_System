from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QLabel, 
                             QPushButton, QTableWidget, QTableWidgetItem,
                             QLineEdit, QHBoxLayout, QMessageBox, QInputDialog)
from PySide6.QtCore import Qt
from services.api_client import APIClient
import requests
import uuid

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.api_client = APIClient()
        self.setWindowTitle("מערכת ניהול ספקים")
        self.setGeometry(100, 100, 1200, 800)
        
        self.setup_ui()
        self.load_suppliers()
    
    def setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        layout = QVBoxLayout(central_widget)
        
        # Title
        title = QLabel("מערכת ניהול ספקים")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 24px; font-weight: bold; margin: 20px;")
        layout.addWidget(title)
        
        # Search bar + Add button
        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("חיפוש ספק...")
        
        self.search_button = QPushButton("חיפוש")
        self.search_button.clicked.connect(self.search_suppliers)
        
        self.add_button = QPushButton("➕ הוסף ספק")
        self.add_button.setStyleSheet("QPushButton { background-color: #28a745; padding: 10px; font-weight: bold; }")
        self.add_button.clicked.connect(self.add_supplier)
        
        search_layout.addWidget(self.search_input)
        search_layout.addWidget(self.search_button)
        search_layout.addWidget(self.add_button)
        layout.addLayout(search_layout)
        
        # Table
        self.suppliers_table = QTableWidget()
        self.suppliers_table.setColumnCount(5)
        self.suppliers_table.setHorizontalHeaderLabels([
            "שם הספק", "קטגוריה", "עיר", "דירוג", "טלפון"
        ])
        layout.addWidget(self.suppliers_table)
        
        # Double-click
        self.suppliers_table.itemDoubleClicked.connect(self.on_supplier_double_clicked)
    
    def load_suppliers(self):
        suppliers = self.api_client.get_suppliers()
        self.display_suppliers(suppliers)
    
    def search_suppliers(self):
        search_term = self.search_input.text()
        suppliers = self.api_client.get_suppliers(search_term=search_term)
        self.display_suppliers(suppliers)
    
    def display_suppliers(self, suppliers):
        self.suppliers_table.setRowCount(len(suppliers))
        
        for row, supplier in enumerate(suppliers):
            self.suppliers_table.setItem(row, 0, QTableWidgetItem(supplier.get('name', '')))
            self.suppliers_table.setItem(row, 1, QTableWidgetItem(supplier.get('category', '')))
            
            city = ""
            if supplier.get('address'):
                city = supplier['address'].get('city', '')
            self.suppliers_table.setItem(row, 2, QTableWidgetItem(city))
            
            rating = f"{supplier.get('rating', 0):.1f} ⭐"
            self.suppliers_table.setItem(row, 3, QTableWidgetItem(rating))
            
            phone = ""
            if supplier.get('contact_info'):
                phone = supplier['contact_info'].get('phone', '')
            self.suppliers_table.setItem(row, 4, QTableWidgetItem(phone))
        
        self.suppliers_table.resizeColumnsToContents()
    
    def add_supplier(self):
        """הוספת ספק חדש"""
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
            
            response = requests.post("http://localhost:8000/api/v1/suppliers", json=supplier_data)
            
            if response.status_code in [200, 201]:
                QMessageBox.information(self, "הצלחה", f"הספק '{name}' נוסף בהצלחה!")
                self.load_suppliers()
            else:
                QMessageBox.warning(self, "שגיאה", "שגיאה בשמירה")
                
        except Exception as e:
            QMessageBox.critical(self, "שגיאה", f"שגיאה: {str(e)}")
    
    def on_supplier_double_clicked(self, item):
        row = item.row()
        supplier_name = self.suppliers_table.item(row, 0).text()
        QMessageBox.information(self, "פרטי ספק", f"ספק: {supplier_name}")