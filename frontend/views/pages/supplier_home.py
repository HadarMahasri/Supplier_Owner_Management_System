# frontend/views/pages/supplier_home.py
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
    QScrollArea, QMessageBox
)
from PySide6.QtCore import Qt, Signal
import os
from typing import Dict

# Import the orders component
from views.widgets.order_list_for_supplier import OrdersForSupplier


class SupplierHome(QWidget):
    logout_requested = Signal()
    
    def __init__(self, user_data: Dict):
        super().__init__()
        self.user_data = user_data
        self.base_url = os.getenv("API_BASE_URL", "http://localhost:8000")
        
        self.setup_ui()
        self.setup_styles()
    
    def setup_ui(self):
        """בניית הממשק בדיוק כמו בתמונה"""
        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Top bar - בדיוק כמו בתמונה
        topbar = self.create_topbar()
        main_layout.addWidget(topbar)
        
        # Content area with scroll
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setFrameShape(QFrame.NoFrame)
        
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(16, 16, 16, 16)
        content_layout.setSpacing(20)
        
        # Orders component - זה החלק המרכזי
        supplier_id = self.user_data.get('id')
        self.orders_widget = OrdersForSupplier(supplier_id)
        content_layout.addWidget(self.orders_widget)
        
        # Add some space at bottom
        content_layout.addStretch()
        
        scroll_area.setWidget(content_widget)
        main_layout.addWidget(scroll_area)
    
    def create_topbar(self) -> QWidget:
        """יצירת topbar בדיוק כמו בתמונה"""
        topbar = QFrame()
        topbar.setObjectName("topbar")
        topbar.setFixedHeight(60)
        
        layout = QHBoxLayout(topbar)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(12)
        
        # Menu button (☰)
        menu_btn = QPushButton("☰")
        menu_btn.setObjectName("menuBtn")
        menu_btn.setFixedSize(40, 40)
        menu_btn.clicked.connect(self.show_menu)
        
        # Title
        supplier_name = self.user_data.get('contact_name', 'ספק')
        company_name = self.user_data.get('company_name', '')
        title_text = f"נתוני ספק"
        if company_name:
            title_text += f" - {company_name}"
            
        title = QLabel(title_text)
        title.setObjectName("title")
        
        # Actions
        actions_layout = QHBoxLayout()
        actions_layout.setSpacing(8)
        
        # ניהול מערכת button
        manage_btn = QPushButton("ניהול מערכת")
        manage_btn.setObjectName("primaryBtn")
        manage_btn.clicked.connect(self.show_management)
        
        # התנתק button
        logout_btn = QPushButton("התנתק")
        logout_btn.setObjectName("ghostBtn")
        logout_btn.clicked.connect(self.logout_requested.emit)
        
        actions_layout.addWidget(manage_btn)
        actions_layout.addWidget(logout_btn)
        
        # Layout assembly
        layout.addWidget(menu_btn)
        layout.addWidget(title, 1)  # stretch
        layout.addLayout(actions_layout)
        
        return topbar
    
    def setup_styles(self):
        """סגנונות בדיוק כמו בתמונה"""
        self.setStyleSheet("""
            /* Main page */
            SupplierHome {
                background: #fafafa;
            }
            
            /* Top bar */
            QFrame#topbar {
                background: #ffffff;
                border-bottom: 1px solid #eeeeee;
            }
            
            QPushButton#menuBtn {
                font-size: 20px;
                border: 1px solid #e5e7eb;
                background: #ffffff;
                border-radius: 10px;
                padding: 6px 10px;
                font-weight: 500;
            }
            QPushButton#menuBtn:hover {
                background: #f9fafb;
                border-color: #10b981;
            }
            QPushButton#menuBtn:pressed {
                background: #f3f4f6;
            }
            
            QLabel#title {
                font-size: 20px;
                font-weight: 700;
                color: #111827;
            }
            
            QPushButton#primaryBtn {
                background: #10b981;
                color: #ffffff;
                border: 1px solid #059669;
                border-radius: 10px;
                padding: 8px 12px;
                font-weight: 600;
                min-width: 120px;
            }
            QPushButton#primaryBtn:hover {
                background: #059669;
                transform: translateY(-1px);
            }
            QPushButton#primaryBtn:pressed {
                background: #047857;
                transform: translateY(0px);
            }
            
            QPushButton#ghostBtn {
                background: #ffffff;
                color: #111827;
                border: 1px solid #e5e7eb;
                border-radius: 10px;
                padding: 8px 12px;
                font-weight: 500;
            }
            QPushButton#ghostBtn:hover {
                background: #f6f7f9;
                border-color: #d1d5db;
            }
        """)
    
    # Event handlers - עם feedback ויזואלי אמיתי
    def show_menu(self):
        """הצגת תפריט"""
        menu_options = [
            "📊 דוח מכירות",
            "📦 ניהול מוצרים", 
            "🏪 ניהול הזמנות",
            "⚙️ הגדרות ספק",
            "📞 צור קשר",
            "📖 עזרה ותמיכה"
        ]
        
        menu_text = "תפריט ספק:\n\n" + "\n".join(menu_options)
        QMessageBox.information(self, "תפריט", menu_text)
    
    def show_management(self):
        """ניהול מערכת"""
        management_options = [
            "🔧 עדכון פרטי ספק",
            "📋 ניהול קטלוג מוצרים",
            "🚛 הגדרות משלוחים", 
            "💰 הגדרות תשלומים",
            "📈 דוחות מתקדמים",
            "👥 ניהול משתמשים"
        ]
        
        management_text = "ניהול מערכת:\n\n" + "\n".join(management_options)
        QMessageBox.information(self, "ניהול מערכת", management_text)
    
    def refresh_all_data(self):
        """רענון כל הנתונים"""
        if hasattr(self, 'orders_widget'):
            self.orders_widget.refresh_orders()
        QMessageBox.information(self, "רענון", "כל הנתונים רוענו בהצלחה!")