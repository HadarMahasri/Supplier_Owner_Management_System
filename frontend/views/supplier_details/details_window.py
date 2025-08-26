from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QFrame, QScrollArea, QWidget, 
                             QGridLayout, QMessageBox)
from PySide6.QtCore import Qt
import requests

class SupplierDetailsWindow(QDialog):
    def __init__(self, supplier_id, parent=None):
        super().__init__(parent)
        self.supplier_id = supplier_id
        self.supplier_data = None
        
        self.setWindowTitle("פרטי ספק מלאים")
        self.setModal(True)
        self.resize(800, 600)
        self.setStyleSheet(self.get_dialog_stylesheet())
        
        self.setup_ui()
        self.load_supplier_details()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Title
        self.title_label = QLabel("טוען פרטי ספק...")
        self.title_label.setStyleSheet("font-size: 22px; font-weight: bold; color: #0078d4;")
        layout.addWidget(self.title_label)
        
        # Content area
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        
        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        
        scroll_area.setWidget(self.content_widget)
        layout.addWidget(scroll_area)
        
        # Buttons
        buttons_layout = QHBoxLayout()
        
        self.contact_btn = QPushButton("📞 פרטי התקשרות")
        self.order_btn = QPushButton("🛒 צור הזמנה")
        close_btn = QPushButton("סגור")
        
        buttons_layout.addWidget(self.contact_btn)
        buttons_layout.addWidget(self.order_btn)
        buttons_layout.addStretch()
        buttons_layout.addWidget(close_btn)
        
        layout.addLayout(buttons_layout)
        
        # Connect signals
        self.contact_btn.clicked.connect(self.show_contact_info)
        self.order_btn.clicked.connect(self.create_order)
        close_btn.clicked.connect(self.close)
    
    def load_supplier_details(self):
        try:
            url = f"http://localhost:8000/api/v1/suppliers/{self.supplier_id}"
            response = requests.get(url)
            
            if response.status_code == 200:
                self.supplier_data = response.json()
                self.display_supplier_details()
            else:
                self.show_error("לא ניתן לטעון פרטי ספק")
                
        except Exception as e:
            self.show_error(f"שגיאה: {str(e)}")
    
    def display_supplier_details(self):
        if not self.supplier_data:
            return
        
        supplier = self.supplier_data
        self.title_label.setText(supplier.get('name', 'ספק'))
        
        # Clear content
        for i in reversed(range(self.content_layout.count())):
            self.content_layout.itemAt(i).widget().setParent(None)
        
        # Add cards
        self.add_card("מידע בסיסי", [
            ("שם", supplier.get('name', '')),
            ("קטגוריה", supplier.get('category', '')),
            ("תיאור", supplier.get('description', ''))
        ])
        
        contact = supplier.get('contact_info', {})
        self.add_card("התקשרות", [
            ("טלפון", contact.get('phone', '')),
            ("אימייל", contact.get('email', ''))
        ])
        
        address = supplier.get('address', {})
        self.add_card("כתובת", [
            ("עיר", address.get('city', '')),
            ("רחוב", address.get('street', ''))
        ])
        
        self.add_card("דירוגים", [
            ("דירוג", f"{supplier.get('rating', 0):.1f} ⭐"),
            ("ביקורות", str(supplier.get('review_count', 0))),
            ("מאומת", "✅ כן" if supplier.get('verified') else "❌ לא")
        ])
    
    def add_card(self, title, data_pairs):
        card = QFrame()
        card.setStyleSheet("QFrame { background-color: #2d2d2d; border-radius: 8px; padding: 15px; margin: 5px; }")
        
        layout = QVBoxLayout(card)
        
        title_label = QLabel(title)
        title_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #0078d4;")
        layout.addWidget(title_label)
        
        for label, value in data_pairs:
            if value:
                info_layout = QHBoxLayout()
                label_widget = QLabel(f"{label}:")
                label_widget.setStyleSheet("font-weight: bold; color: #cccccc;")
                value_widget = QLabel(str(value))
                value_widget.setStyleSheet("color: white;")
                
                info_layout.addWidget(label_widget)
                info_layout.addWidget(value_widget)
                info_layout.addStretch()
                
                layout.addLayout(info_layout)
        
        self.content_layout.addWidget(card)
    
    def show_contact_info(self):
        contact = self.supplier_data.get('contact_info', {}) if self.supplier_data else {}
        
        msg = QMessageBox(self)
        msg.setWindowTitle("פרטי התקשרות")
        
        text = ""
        if contact.get('phone'):
            text += f"📞 {contact['phone']}\n"
        if contact.get('email'):
            text += f"📧 {contact['email']}\n"
        
        msg.setText(text or "אין פרטי התקשרות")
        msg.exec()
    
    def create_order(self):
        name = self.supplier_data.get('name', '') if self.supplier_data else ''
        
        msg = QMessageBox(self)
        msg.setWindowTitle("הזמנה")
        msg.setText(f"האם ברצונך ליצור הזמנה אצל {name}?")
        msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        
        if msg.exec() == QMessageBox.Yes:
            success = QMessageBox(self)
            success.setText("הזמנה נוצרה בהצלחה!")
            success.exec()
    
    def show_error(self, message):
        error = QMessageBox(self)
        error.setWindowTitle("שגיאה")
        error.setText(message)
        error.setIcon(QMessageBox.Critical)
        error.exec()
    
    def get_dialog_stylesheet(self):
        return """
        QDialog { background-color: #1e1e1e; color: white; }
        QLabel { color: white; }
        QPushButton { 
            background-color: #0078d4; 
            color: white; 
            border: none; 
            border-radius: 6px; 
            padding: 10px 15px; 
        }
        QPushButton:hover { background-color: #106ebe; }
        """