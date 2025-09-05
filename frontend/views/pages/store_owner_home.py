# frontend/views/pages/store_owner_home.py
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
    QScrollArea, QMessageBox, QStackedWidget, QSizePolicy, QGraphicsDropShadowEffect
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from typing import Dict

# ייבוא עמוד הצ'אט החדש
from views.pages.ai_chat_page import AIChatPage
from views.widgets.store_owner_orders_widget import StoreOwnerOrdersWidget
from views.widgets.side_menu_store_owner import SideMenu
from views.pages.owner_links_page import OwnerLinksPage
from views.pages.order_create_page import OrderCreatePage


class StoreOwnerHome(QWidget):
    logout_requested = Signal()

    def __init__(self, user_data: Dict):
        super().__init__()
        self.user_data = user_data
        self.side_menu = None
        self.setup_ui()
        self.setup_styles()

    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Topbar
        topbar = self.create_topbar()
        main_layout.addWidget(topbar)

        # Content area with scroll
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setFrameShape(QFrame.NoFrame)

        self.content_stack = QStackedWidget()
        self.content_stack.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # index 0: Orders
        orders_page = QWidget()
        orders_layout = QVBoxLayout(orders_page)
        orders_layout.setContentsMargins(16, 16, 16, 16)
        orders_layout.setSpacing(20)
        owner_id = self.user_data.get('id')
        
        self.orders_widget = StoreOwnerOrdersWidget(owner_id)
        self.orders_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        orders_layout.addWidget(self.orders_widget, 1)
        self.content_stack.addWidget(orders_page)

        # index 1: Suppliers (for creating orders)
        suppliers_page = self.create_suppliers_page()
        self.content_stack.addWidget(suppliers_page)

        # index 2: Order creation (dynamic)
        empty_page = QWidget()
        self.content_stack.addWidget(empty_page)

        # index 3: AI Chat (חדש!)
        ai_chat_page = AIChatPage(self.user_data)
        self.content_stack.addWidget(ai_chat_page)

        scroll_area.setWidget(self.content_stack)
        main_layout.addWidget(scroll_area, 1)

        # Start with orders page
        self.content_stack.setCurrentIndex(0)

        # יצירת התפריט הצידי
        self.create_side_menu()

    def create_suppliers_page(self) -> QWidget:
        """יצירת עמוד רשימת ספקים"""
        try:
            # העברת callback במקום שימוש ב-signal שלא קיים
            supplier_page = OwnerLinksPage(
                self.user_data.get('id', 1),
                open_order_inline=self.open_order_inline  # ← זה העיקר
            )
            return supplier_page
        except Exception as e:
            return self.create_error_page(f"שגיאה בטעינת עמוד הספקים:\n{str(e)}")

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
        
        # Menu button
        menu_btn = QPushButton("☰")
        menu_btn.setObjectName("menuBtn")
        menu_btn.setFixedSize(40, 40)
        menu_btn.clicked.connect(self.toggle_side_menu)
        
        # Title
        owner_name = self.user_data.get('contact_name', 'בעל חנות')
        company_name = self.user_data.get('company_name', '')
        title_text = f"נתוני בעל חנות"
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

        suppliers_btn = QPushButton("ביצוע הזמנה")
        suppliers_btn.setObjectName("primaryBtn")
        suppliers_btn.clicked.connect(self.show_suppliers_page)

        # כפתור צ'אט AI חדש
        ai_chat_btn = QPushButton("💬 שיחה עם AI")
        ai_chat_btn.setObjectName("aiChatBtn")
        ai_chat_btn.clicked.connect(self.show_ai_chat_page)

        nav_layout.addWidget(orders_btn)
        nav_layout.addWidget(suppliers_btn)
        nav_layout.addWidget(ai_chat_btn)

        # כפתור התנתקות בצד שמאל
        logout_btn = QPushButton("התנתק")
        logout_btn.setObjectName("ghostBtn")
        logout_btn.clicked.connect(self.logout_requested.emit)

        # סידור כללי בליאאוט הראשי
        layout.addWidget(logout_btn)
        layout.addWidget(title, 1)
        layout.addLayout(nav_layout)
        layout.addWidget(menu_btn)
        return topbar

    def setup_styles(self):
        """סגנונות מעודכנים"""
        self.setStyleSheet("""
            StoreOwnerHome { background:#f0f4f8; }
            QFrame#topbar { background:#fff; border-bottom:1px solid #e5e7eb; }
            QPushButton#menuBtn {
                font-size:20px; border:1px solid #e5e7eb; background:#fff; border-radius:10px; 
                padding:6px 10px; font-weight:500;
            }
            QPushButton#menuBtn:hover { background:#f9fafb; border-color:#3b82f6; }
            QPushButton#menuBtn:pressed { background:#f3f4f6; }
            QLabel#title { font-size:20px; font-weight:700; color:#111827; }
            
            QPushButton#primaryBtn {
                background:#3b82f6; color:#fff; border:1px solid #2563eb; border-radius:10px; 
                padding:8px 12px; font-weight:600; min-width:120px;
            }
            QPushButton#primaryBtn:hover { background:#2563eb; transform:translateY(-1px); }
            QPushButton#primaryBtn:pressed { background:#1d4ed8; transform:translateY(0px); }
            
            QPushButton#secondaryBtn {
                background:#fff; color:#374151; border:1px solid #d1d5db; border-radius:10px; 
                padding:8px 12px; font-weight:500; min-width:120px;
            }
            QPushButton#secondaryBtn:hover { background:#f9fafb; border-color:#3b82f6; color:#3b82f6; }
            
            QPushButton#aiChatBtn {
                background:#6366f1; color:#fff; border:1px solid #4f46e5; border-radius:10px; 
                padding:8px 12px; font-weight:600; min-width:120px;
            }
            QPushButton#aiChatBtn:hover { background:#4f46e5; transform:translateY(-1px); }
            QPushButton#aiChatBtn:pressed { background:#4338ca; transform:translateY(0px); }
            
            QPushButton#ghostBtn {
                background:#fff; color:#111827; border:1px solid #dc2626; border-radius:10px; 
                padding:8px 12px; font-weight:500;
            }
            QPushButton#ghostBtn:hover { background:#fef2f2; border-color:#b91c1c; color:#dc2626; }
        """)

    # ===== ניווט לביצוע הזמנת ספק (inline) =====
    def open_order_inline(self, supplier_id: int):
        owner_id = self.user_data.get('id', 1)
        order_page = OrderCreatePage(owner_id, supplier_id, self)
        order_page.canceled.connect(lambda: self.show_suppliers_page())
        order_page.submitted.connect(self._after_order_submitted)

        prev = self.content_stack.widget(2)
        if prev is not None:
            prev.setParent(None)
        self.content_stack.insertWidget(2, order_page)
        self.content_stack.setCurrentIndex(2)
        self.update_buttons_state("new_order")

    def _after_order_submitted(self):
        self.show_orders_page()
        try:
            if hasattr(self, 'orders_widget'):
                self.orders_widget.refresh_orders()
        except:
            pass

    # ===== ניווט כללי =====
    def show_page(self, page: str):
        if page == "orders":
            self.content_stack.setCurrentIndex(0)
            self.update_buttons_state("orders")
        elif page == "suppliers":
            self.content_stack.setCurrentIndex(1)
            self.update_buttons_state("suppliers")
        elif page == "new_order":
            self.content_stack.setCurrentIndex(2)
            self.update_buttons_state("new_order")
        elif page == "ai_chat":  # הוספת הטיפול בצ'אט AI
            self.show_ai_chat_page()

    def show_orders_page(self): 
        self.show_page("orders")
        
    def show_new_order_page(self): 
        self.show_suppliers_page()
        
    def show_suppliers_page(self): 
        self.show_page("suppliers")
        
    def show_ai_chat_page(self):
        """מעבר לעמוד צ'אט AI"""
        self.content_stack.setCurrentIndex(3)
        self.update_buttons_state("ai_chat")

    def update_buttons_state(self, active_page: str):
        topbar = self.findChild(QFrame, "topbar")
        if not topbar:
            return
            
        orders_btn = None
        suppliers_btn = None
        ai_chat_btn = None
        
        for btn in topbar.findChildren(QPushButton):
            if btn.text() == "רשימת הזמנות":
                orders_btn = btn
            elif btn.text() == "ביצוע הזמנה":
                suppliers_btn = btn
            elif "שיחה עם AI" in btn.text():
                ai_chat_btn = btn
        
        # איפוס כל הכפתורים למצב רגיל
        if orders_btn:
            orders_btn.setObjectName("secondaryBtn")
        if suppliers_btn:
            suppliers_btn.setObjectName("secondaryBtn")
        if ai_chat_btn:
            ai_chat_btn.setObjectName("secondaryBtn")
            
        # הפעלת הכפתור הנוכחי
        if active_page == "orders" and orders_btn:
            orders_btn.setObjectName("primaryBtn")
        elif active_page in ["suppliers", "new_order"] and suppliers_btn:
            suppliers_btn.setObjectName("primaryBtn")
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
        menu_height = min(400, self.height() - 60)
        self.side_menu.resize(280, menu_height)
        
        menu_x = self.width() - 280
        menu_y = 60
        
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
        """ניהול מערכת - עכשיו מפנה לביצוע הזמנה"""
        self.show_suppliers_page()

    def refresh_all_data(self):
        """רענון כל הנתונים"""
        # רענון הזמנות
        if hasattr(self, 'orders_widget'):
            self.orders_widget.refresh_orders()
        
        # רענון עמוד נוכחי
        current_widget = self.content_stack.currentWidget()
        if hasattr(current_widget, 'reload_from_server'):
            current_widget.reload_from_server()
        elif hasattr(current_widget, 'refresh'):
            current_widget.refresh()
        
        QMessageBox.information(self, "רענון", "כל הנתונים רוענו בהצלחה!")