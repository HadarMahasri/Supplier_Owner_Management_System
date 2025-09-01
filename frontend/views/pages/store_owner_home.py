# frontend/views/pages/store_owner_home.py
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
    QScrollArea, QMessageBox, QStackedWidget, QSizePolicy, QGraphicsDropShadowEffect,
    QLineEdit
)
from PySide6.QtCore import Qt, Signal, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QColor
import os
from typing import Dict
import json, datetime


# Import the orders component for store owner
from views.widgets.order_list_for_store_owner import OrdersForStoreOwner


class SideMenu(QFrame):
    """תפריט צידי לבעל חנות"""
    page_requested = Signal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("sideMenu")
        self.setFixedWidth(280)
        self.setup_ui()
        self.setup_styles()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # כותרת התפריט
        header = QFrame()
        header.setObjectName("menuHeader")
        header.setFixedHeight(60)
        
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(24, 16, 24, 16)
        
        title = QLabel("תפריט בעל חנות")
        title.setObjectName("menuTitle")
        header_layout.addWidget(title)
        
        # כפתור סגירה
        close_btn = QPushButton("✕")
        close_btn.setObjectName("closeBtn")
        close_btn.setFixedSize(32, 32)
        close_btn.clicked.connect(self.hide)
        header_layout.addWidget(close_btn)
        
        layout.addWidget(header)
        
        # רשימת פריטי תפריט
        menu_items = [
            ("orders", "רשימת הזמנות"),
            ("new_order", "יצירת הזמנה חדשה"),
            ("suppliers", "רשימת ספקים"),
            ("reports", "דוחות הזמנות"),
            ("settings", "הגדרות חנות"),
            ("help", "עזרה ותמיכה")
        ]
        
        menu_container = QWidget()
        menu_layout = QVBoxLayout(menu_container)
        menu_layout.setContentsMargins(16, 24, 16, 24)
        menu_layout.setSpacing(8)
        
        for action, text in menu_items:
            btn = self.create_menu_button(action, text)
            menu_layout.addWidget(btn)
        
        menu_layout.addStretch()
        layout.addWidget(menu_container)
        
    def create_menu_button(self, action: str, text: str) -> QPushButton:
        btn = QPushButton(text)
        btn.setObjectName("menuItem")
        btn.clicked.connect(lambda: self.on_menu_click(action))
        return btn
        
    def on_menu_click(self, action: str):
        if action in ["orders", "new_order", "suppliers"]:
            self.page_requested.emit(action)
            self.hide()
        else:
            # פעולות עתידיות
            QMessageBox.information(self, "בקרוב", f"תכונה '{action}' תהיה זמינה בקרוב")
    
    def setup_styles(self):
        self.setStyleSheet("""
            QFrame#sideMenu {
                background: #ffffff;
                border: 1px solid #e5e7eb;
                border-radius: 0px 8px 8px 0px;
            }
            
            QFrame#menuHeader {
                background: #eff6ff;
                border-bottom: 1px solid #bfdbfe;
                border-radius: 0px 8px 0px 0px;
            }
            
            QLabel#menuTitle {
                font-size: 18px;
                font-weight: 700;
                color: #1e40af;
            }
            
            QPushButton#closeBtn {
                background: transparent;
                border: 1px solid #e5e7eb;
                border-radius: 16px;
                color: #6b7280;
                font-size: 14px;
            }
            QPushButton#closeBtn:hover {
                background: #f3f4f6;
                color: #374151;
            }
            
            QPushButton#menuItem {
                background: transparent;
                border: none;
                border-radius: 8px;
                padding: 14px 16px;
                text-align: left;
                font-size: 14px;
                font-weight: 500;
                color: #374151;
                min-height: 20px;
            }
            QPushButton#menuItem:hover {
                background: #dbeafe;
                color: #1d4ed8;
            }
            QPushButton#menuItem:pressed {
                background: #bfdbfe;
            }
        """)


class StoreOwnerHome(QWidget):
    logout_requested = Signal()
    
    def __init__(self, user_data: Dict):
        super().__init__()
        self.user_data = user_data
        self.base_url = os.getenv("API_BASE_URL", "http://localhost:8000")
        
        # התפריט הצידי
        self.side_menu = None
        
        self.setup_ui()
        self.setup_styles()
    
    def setup_ui(self):
        """בניית הממשק עם אזור תוכן מתחלף"""
        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Top bar - נשאר קבוע תמיד
        topbar = self.create_topbar()
        main_layout.addWidget(topbar)
        
        # Content area with scroll - זה מה שמתחלף
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setFrameShape(QFrame.NoFrame)
        
        # Stacked widget for different content views
        self.content_stack = QStackedWidget()
        self.content_stack.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        # Page 1: Orders list (default)
        orders_page = self.create_orders_page()
        self.content_stack.addWidget(orders_page)
        
        
        # Page 3: Suppliers list
        suppliers_page = self.create_suppliers_page()
        self.content_stack.addWidget(suppliers_page)
        
        scroll_area.setWidget(self.content_stack)
        main_layout.addWidget(scroll_area, 1)
        
        # Start with orders page (index 0)
        self.content_stack.setCurrentIndex(0)
        
        # יצירת התפריט הצידי
        self.create_side_menu()
    
    def create_orders_page(self) -> QWidget:
        """יצירת עמוד ההזמנות (המקורי)"""
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(16, 16, 16, 16)
        content_layout.setSpacing(20)
        
        # Orders component - זה החלק המרכזי
        owner_id = self.user_data.get('id')
        self.orders_widget = OrdersForStoreOwner(owner_id)
        self.orders_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        content_layout.addWidget(self.orders_widget, 1)
                
        return content_widget
    
    def create_suppliers_page(self) -> QWidget:
        """יצירת עמוד רשימת ספקים"""
        try:
            from views.pages.owner_links_page import OwnerLinksPage
            owner_id = self.user_data.get('id', 1)
            suppliers_widget = OwnerLinksPage(owner_id)
            return suppliers_widget
        except ImportError as e:
            return self.create_error_page(f"שגיאה בטעינת עמוד רשימת ספקים:\n{str(e)}")
    
    def create_error_page(self, error_msg: str) -> QWidget:
        """יצירת עמוד שגיאה"""
        error_widget = QWidget()
        error_layout = QVBoxLayout(error_widget)
        error_layout.setContentsMargins(50, 50, 50, 50)
        
        error_label = QLabel(error_msg)
        error_label.setAlignment(Qt.AlignCenter)
        error_label.setStyleSheet("font-size: 16px; color: #dc2626; padding: 20px;")
        
        back_btn = QPushButton("חזור לרשימת הזמנות")
        back_btn.clicked.connect(lambda: self.show_orders_page())
        back_btn.setObjectName("primaryBtn")
        
        error_layout.addStretch()
        error_layout.addWidget(error_label)
        error_layout.addWidget(back_btn, 0, Qt.AlignCenter)
        error_layout.addStretch()
        
        return error_widget
    
    def create_side_menu(self):
        """יצירת התפריט הצידי"""
        self.side_menu = SideMenu(self)
        self.side_menu.page_requested.connect(self.show_page)
        self.side_menu.hide()
        
        # הוספת צל
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(15)
        shadow.setColor(QColor(0, 0, 0, 80))
        shadow.setOffset(3, 0)
        self.side_menu.setGraphicsEffect(shadow)
    
    def create_topbar(self) -> QWidget:
        """יצירת topbar קבוע - בדיוק כמו המקור עם תפריט המבורגר"""
        topbar = QFrame()
        topbar.setObjectName("topbar")
        topbar.setFixedHeight(60)
        
        layout = QHBoxLayout(topbar)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(12)
        
        # Menu button (☰) - עכשיו פותח תפריט צידי
        menu_btn = QPushButton("☰")
        menu_btn.setObjectName("menuBtn")
        menu_btn.setFixedSize(40, 40)
        menu_btn.clicked.connect(self.toggle_side_menu)
        
        # Title
        owner_name = self.user_data.get('contact_name', 'בעל חנות')
        company_name = self.user_data.get('company_name', '')
        title_text = f"ממשק בעל חנות"
        if company_name:
            title_text += f" - {company_name}"
            
        title = QLabel(title_text)
        title.setObjectName("title")
        
        # Actions - כפתורי המקור מותאמים לבעל חנות
        actions_layout = QHBoxLayout()
        actions_layout.setSpacing(8)
        
        # כפתור רשימת הזמנות
        orders_btn = QPushButton("רשימת הזמנות")
        orders_btn.setObjectName("secondaryBtn")
        orders_btn.clicked.connect(self.show_orders_page)
        
        # כפתור יצירת הזמנה חדשה (החדש!)
        new_order_btn = QPushButton("הזמנה חדשה")
        new_order_btn.setObjectName("primaryBtn")
        new_order_btn.clicked.connect(self.show_new_order_page)
        
        # התנתק button
        logout_btn = QPushButton("התנתק")
        logout_btn.setObjectName("ghostBtn")
        logout_btn.clicked.connect(self.logout_requested.emit)
        
        actions_layout.addWidget(orders_btn)
        actions_layout.addWidget(new_order_btn)
        actions_layout.addWidget(logout_btn)
        
        # Layout assembly
        layout.addWidget(menu_btn)
        layout.addWidget(title, 1)  # stretch
        layout.addLayout(actions_layout)
        
        return topbar
    
    def setup_styles(self):
        """סגנונות מעודכנים - כחול במקום ירוק לבעל חנות"""
        self.setStyleSheet("""
            /* Main page */
            StoreOwnerHome {
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
                border-color: #3b82f6;
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
                background: #3b82f6;
                color: #ffffff;
                border: 1px solid #2563eb;
                border-radius: 10px;
                padding: 8px 12px;
                font-weight: 600;
                min-width: 120px;
            }
            QPushButton#primaryBtn:hover {
                background: #2563eb;
                transform: translateY(-1px);
            }
            QPushButton#primaryBtn:pressed {
                background: #1d4ed8;
                transform: translateY(0px);
            }
            
            QPushButton#secondaryBtn {
                background: #ffffff;
                color: #374151;
                border: 1px solid #d1d5db;
                border-radius: 10px;
                padding: 8px 12px;
                font-weight: 500;
                min-width: 120px;
            }
            QPushButton#secondaryBtn:hover {
                background: #f9fafb;
                border-color: #3b82f6;
                color: #3b82f6;
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
    
    # Navigation methods
    def show_page(self, page: str):
        """מעבר לעמוד הרצוי"""
        page_mapping = {
            "orders": 0,
            "new_order": 1, 
            "suppliers": 2
        }
        
        if page in page_mapping:
            self.content_stack.setCurrentIndex(page_mapping[page])
            self.update_buttons_state(page)
    
    def show_orders_page(self):
        """מעבר לעמוד הזמנות"""
        self.show_page("orders")
    
    def show_new_order_page(self):
        """מעבר לעמוד יצירת הזמנה חדשה"""
        self.show_page("new_order")
    
    def show_suppliers_page(self):
        """מעבר לעמוד ספקים"""
        self.show_page("suppliers")
    
    def update_buttons_state(self, active_page: str):
        """עדכון מראה הכפתורים לפי העמוד הפעיל"""
        # מציאת הכפתורים בtopbar
        topbar = self.findChild(QFrame, "topbar")
        if not topbar:
            return
            
        orders_btn = None
        new_order_btn = None
        
        for btn in topbar.findChildren(QPushButton):
            if btn.text() == "רשימת הזמנות":
                orders_btn = btn
            elif btn.text() == "הזמנה חדשה":
                new_order_btn = btn
        
        if active_page == "orders":
            if orders_btn:
                orders_btn.setObjectName("primaryBtn")
            if new_order_btn:
                new_order_btn.setObjectName("secondaryBtn")
        elif active_page == "new_order":
            if orders_btn:
                orders_btn.setObjectName("secondaryBtn")
            if new_order_btn:
                new_order_btn.setObjectName("primaryBtn")
        else:  # suppliers
            if orders_btn:
                orders_btn.setObjectName("secondaryBtn")
            if new_order_btn:
                new_order_btn.setObjectName("secondaryBtn")
        
        # רענון הסגנון
        self.setup_styles()
    
    # Side menu methods
    def toggle_side_menu(self):
        """פתיחה/סגירה של התפריט הצידי"""
        if self.side_menu.isVisible():
            self.hide_side_menu()
        else:
            self.show_side_menu()
    
    def show_side_menu(self):
        """הצגת התפריט הצידי - בצד שמאל מתחת לטופבר"""
        # מיקום התפריט בצד שמאל מתחת לטופבר
        menu_height = min(400, self.height() - 60)
        self.side_menu.resize(280, menu_height)
        
        # מיקום ביחס לחלון הראשי
        menu_x = 0  # בצד שמאל
        menu_y = 60  # מתחת לטופבר
        
        self.side_menu.move(menu_x, menu_y)
        self.side_menu.show()
        self.side_menu.raise_()
    
    def hide_side_menu(self):
        """הסתרת התפריט הצידי"""
        self.side_menu.hide()
    
    # Event handlers המקוריים
    def show_menu(self):
        """הצגת תפריט - עכשיו פותח תפריט צידי"""
        self.toggle_side_menu()
    
    def show_management(self):
        """ניהול מערכת - עכשיו מפנה ליצירת הזמנה"""
        self.show_new_order_page()
    
    def refresh_all_data(self):
        """רענון כל הנתונים"""
        # רענון הזמנות
        if hasattr(self, 'orders_widget'):
            self.orders_widget.refresh_orders()
        
        # רענון עמודים אחרים
        current_widget = self.content_stack.currentWidget()
        if hasattr(current_widget, 'reload_from_server'):
            current_widget.reload_from_server()
        elif hasattr(current_widget, 'refresh'):
            current_widget.refresh()
        
        QMessageBox.information(self, "רענון", "כל הנתונים רוענו בהצלחה!")