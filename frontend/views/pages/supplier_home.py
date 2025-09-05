# frontend/views/pages/supplier_home.py
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
    QScrollArea, QMessageBox, QStackedWidget, QSizePolicy, QGraphicsDropShadowEffect
)
from PySide6.QtCore import Qt, Signal, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QColor
import os
from typing import Dict
import json, datetime

# ייבוא עמוד הצ'אט החדש לספק
from views.pages.ai_chat_supplier_page import AIChatSupplierPage
from views.pages.supplier_orders_page import SupplierOrdersPage


class SideMenu(QFrame):
    """תפריט צידי"""
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
        
        title = QLabel("תפריט ספק")
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
            ("orders", "ניהול הזמנות"),
            ("products", "ניהול מוצרים"),
            ("links", "קישורים עם בעלי חנויות"),
            ("ai_chat", "שיחה עם העוזר הדיגיטלי"),  # הוספת פריט הצ'אט
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
        if action in ["orders", "products", "links", "ai_chat"]:  # הוספת ai_chat לפעולות זמינות
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
                background: #f0fdf4;
                border-bottom: 1px solid #dcfce7;
                border-radius: 0px 8px 0px 0px;
            }
            
            QLabel#menuTitle {
                font-size: 18px;
                font-weight: 700;
                color: #047857;
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
                background: #f0fdf4;
                color: #059669;
            }
            QPushButton#menuItem:pressed {
                background: #dcfce7;
            }
        """)


class SupplierHome(QWidget):
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
        
        # Page 0: Orders list (default)
        orders_page = self.create_orders_page()
        self.content_stack.addWidget(orders_page)
        
        # Page 1: Products management
        products_page = self.create_products_page()
        self.content_stack.addWidget(products_page)
        
        # Page 2: Links management
        links_page = self.create_links_page()
        self.content_stack.addWidget(links_page)
        
        # Page 3: AI Chat (חדש!)
        ai_chat_page = AIChatSupplierPage(self.user_data)
        self.content_stack.addWidget(ai_chat_page)
        
        scroll_area.setWidget(self.content_stack)
        main_layout.addWidget(scroll_area, 1)
        
        # Start with orders page (index 0)
        self.content_stack.setCurrentIndex(0)
        
        # יצירת התפריט הצידי
        self.create_side_menu()
    
    def create_orders_page(self) -> QWidget:
        """יצירת עמוד ההזמנות - משתמש בארכיטקטורה החדשה"""
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(16, 16, 16, 16)
        content_layout.setSpacing(20)
        
        # Orders page - משתמש בעמוד החדש במקום ווידג'ט הישן
        supplier_id = self.user_data.get('id')
        self.orders_page = SupplierOrdersPage(supplier_id)
        self.orders_page.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        content_layout.addWidget(self.orders_page, 1)
                
        return content_widget
    
    def create_products_page(self) -> QWidget:
        """יצירת עמוד ניהול המוצרים"""
        try:
            from views.pages.supplier_products_page import SupplierProductsPage
            supplier_id = self.user_data.get('id', 1)
            products_widget = SupplierProductsPage(supplier_id)
            return products_widget
        except ImportError as e:
            return self.create_error_page(f"שגיאה בטעינת עמוד המוצרים:\n{str(e)}")
    
    def create_links_page(self) -> QWidget:
        """יצירת עמוד ניהול הקישורים"""
        try:
            from views.pages.supplier_links_page import SupplierLinksPage
            supplier_id = self.user_data.get('id', 1)
            links_widget = SupplierLinksPage(supplier_id)
            return links_widget
        except ImportError as e:
            return self.create_error_page(f"שגיאה בטעינת עמוד הקישורים:\n{str(e)}")
    
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
        """יצירת topbar קבוע"""
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
        menu_btn.clicked.connect(self.toggle_side_menu)
        
        # Title
        supplier_name = self.user_data.get('contact_name', 'ספק')
        company_name = self.user_data.get('company_name', '')
        title_text = f"נתוני ספק"
        if company_name:
            title_text += f" - {company_name}"
            
        title = QLabel(title_text)
        title.setObjectName("title")
        title.setAlignment(Qt.AlignCenter)
        
        # כפתורי ניווט בצד ימין
        nav_layout = QHBoxLayout()
        nav_layout.setSpacing(8)

        orders_btn = QPushButton("רשימת הזמנות")
        orders_btn.setObjectName("secondaryBtn")
        orders_btn.clicked.connect(self.show_orders_page)

        products_btn = QPushButton("ניהול מוצרים")
        products_btn.setObjectName("primaryBtn")
        products_btn.clicked.connect(self.show_products_page)

        # כפתור צ'אט AI חדש
        ai_chat_btn = QPushButton("🤖 שיחה עם AI")
        ai_chat_btn.setObjectName("aiChatBtn")
        ai_chat_btn.clicked.connect(self.show_ai_chat_page)

        nav_layout.addWidget(orders_btn)
        nav_layout.addWidget(products_btn)
        nav_layout.addWidget(ai_chat_btn)

        # כפתור התנתקות בצד שמאל
        logout_btn = QPushButton("התנתק")
        logout_btn.setObjectName("ghostBtn")
        logout_btn.clicked.connect(self.logout_requested.emit)

        # סידור כללי בליאאוט הראשי
        layout.addWidget(logout_btn)       # שמאל
        layout.addWidget(title, 1)         # מרכז עם stretch
        layout.addLayout(nav_layout)       # ימין (לפני הmenu button)
        layout.addWidget(menu_btn)         # ימין ביותר
        return topbar

    def setup_styles(self):
        """סגנונות מעודכנים"""
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
                border-color: #10b981;
                color: #10b981;
            }
            
            QPushButton#aiChatBtn {
                background: #16a34a;
                color: #ffffff;
                border: 1px solid #15803d;
                border-radius: 10px;
                padding: 8px 12px;
                font-weight: 600;
                min-width: 120px;
            }
            QPushButton#aiChatBtn:hover {
                background: #15803d;
                transform: translateY(-1px);
            }
            QPushButton#aiChatBtn:pressed {
                background: #166534;
                transform: translateY(0px);
            }
            
            QPushButton#ghostBtn {
                background: #ffffff;
                color: #111827;
                border: 1px solid #dc2626;
                border-radius: 10px;
                padding: 8px 12px;
                font-weight: 500;
            }
            QPushButton#ghostBtn:hover {
                background: #fef2f2;
                border-color: #b91c1c;
                color: #dc2626;
            }
        """)
    
    # Navigation methods
    def show_page(self, page: str):
        """מעבר לעמוד הרצוי"""
        page_mapping = {
            "orders": 0,
            "products": 1, 
            "links": 2,
            "ai_chat": 3  # הוספת מיפוי לצ'אט AI
        }
        
        if page in page_mapping:
            self.content_stack.setCurrentIndex(page_mapping[page])
            self.update_buttons_state(page)
    
    def show_orders_page(self):
        """מעבר לעמוד הזמנות"""
        self.show_page("orders")
    
    def show_products_page(self):
        """מעבר לעמוד ניהול מוצרים"""
        self.show_page("products")
    
    def show_links_page(self):
        """מעבר לעמוד קישורים"""
        self.show_page("links")
        
    def show_ai_chat_page(self):
        """מעבר לעמוד צ'אט AI"""
        self.show_page("ai_chat")
    
    def update_buttons_state(self, active_page: str):
        """עדכון מראה הכפתורים לפי העמוד הפעיל"""
        # מציאת הכפתורים בtopbar
        topbar = self.findChild(QFrame, "topbar")
        if not topbar:
            return
            
        orders_btn = None
        products_btn = None
        ai_chat_btn = None
        
        for btn in topbar.findChildren(QPushButton):
            if btn.text() == "רשימת הזמנות":
                orders_btn = btn
            elif btn.text() == "ניהול מוצרים":
                products_btn = btn
            elif "שיחה עם AI" in btn.text():
                ai_chat_btn = btn
        
        # איפוס כל הכפתורים
        if orders_btn:
            orders_btn.setObjectName("secondaryBtn")
        if products_btn:
            products_btn.setObjectName("secondaryBtn")
        if ai_chat_btn:
            ai_chat_btn.setObjectName("secondaryBtn")
            
        # הפעלת הכפתור הנוכחי
        if active_page == "orders" and orders_btn:
            orders_btn.setObjectName("primaryBtn")
        elif active_page in ["products", "links"] and products_btn:
            products_btn.setObjectName("primaryBtn")
        elif active_page == "ai_chat" and ai_chat_btn:
            ai_chat_btn.setObjectName("aiChatBtn")
        
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
        """הצגת התפריט הצידי - בצד ימין מתחת לטופבר"""
        # מיקום התפריט בצד ימין מתחת לטופבר
        menu_height = min(400, self.height() - 60)
        self.side_menu.resize(280, menu_height)
        
        # מיקום ביחס לחלון הראשי
        menu_x = self.width() - 280  # בצד ימין
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
        """ניהול מערכת - עכשיו מפנה לניהול מוצרים"""
        self.show_products_page()
    
    def refresh_all_data(self):
        """רענון כל הנתונים"""
        # רענון הזמנות - משתמש בעמוד החדש
        if hasattr(self, 'orders_page'):
            self.orders_page.refresh_orders()
        
        # רענון מוצרים
        current_widget = self.content_stack.currentWidget()
        if hasattr(current_widget, 'reload_from_server'):
            current_widget.reload_from_server()
        elif hasattr(current_widget, 'refresh'):
            current_widget.refresh()
        
        QMessageBox.information(self, "רענון", "כל הנתונים רוענו בהצלחה!")