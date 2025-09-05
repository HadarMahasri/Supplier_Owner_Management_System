# frontend/views/pages/store_owner_home.py
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
    QScrollArea, QMessageBox, QStackedWidget, QSizePolicy, QGraphicsDropShadowEffect
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from typing import Dict

# שימוש ב-widget החדש במקום הישן
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

        # index 0: Orders - שימוש ב-widget החדש
        orders_page = QWidget()
        orders_layout = QVBoxLayout(orders_page)
        orders_layout.setContentsMargins(16, 16, 16, 16)
        orders_layout.setSpacing(20)
        owner_id = self.user_data.get('id')
        
        # שימוש ב-widget החדש
        self.orders_widget = StoreOwnerOrdersWidget(owner_id)
        self.orders_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        orders_layout.addWidget(self.orders_widget, 1)
        self.content_stack.addWidget(orders_page)

        # index 1: Suppliers
        suppliers_page = OwnerLinksPage(owner_id, open_order_inline=self.open_order_inline)
        self.content_stack.addWidget(suppliers_page)

        # index 2: New Order (נטען דינמית בכל פתיחה)
        placeholder = QWidget()
        self.content_stack.addWidget(placeholder)

        scroll_area.setWidget(self.content_stack)
        main_layout.addWidget(scroll_area, 1)

        self.content_stack.setCurrentIndex(0)
        self.create_side_menu()

    def create_side_menu(self):
        self.side_menu = SideMenu(self)
        self.side_menu.page_requested.connect(self.show_page)
        self.side_menu.hide()

        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(15)
        shadow.setColor(QColor(0, 0, 0, 80))
        shadow.setOffset(3, 0)
        self.side_menu.setGraphicsEffect(shadow)

    def create_topbar(self) -> QWidget:
        topbar = QFrame()
        topbar.setObjectName("topbar")
        topbar.setFixedHeight(60)

        layout = QHBoxLayout(topbar)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(12)

        # Actions - צד שמאל (הכפתורים בסדר: התנתק, רשימת הזמנות, הזמנה חדשה)
        # כפתור התנתקות בצד שמאל
        logout_btn = QPushButton("התנתק")
        logout_btn.setObjectName("ghostBtn")
        logout_btn.clicked.connect(self.logout_requested.emit)

        # Title - במרכז
        company_name = self.user_data.get('company_name', '')
        title_text = "ממשק בעל חנות" + (f" - {company_name}" if company_name else "")
        title = QLabel(title_text)
        title.setObjectName("title")
        title.setAlignment(Qt.AlignCenter)

        # כפתורי ניווט בצד ימין
        nav_layout = QHBoxLayout()
        nav_layout.setSpacing(8)

        orders_btn = QPushButton("רשימת הזמנות")
        orders_btn.setObjectName("secondaryBtn")
        orders_btn.clicked.connect(self.show_orders_page)

        new_order_btn = QPushButton("הזמנה חדשה")
        new_order_btn.setObjectName("primaryBtn")
        new_order_btn.clicked.connect(self.show_suppliers_page)

        nav_layout.addWidget(orders_btn)
        nav_layout.addWidget(new_order_btn)

        # Menu button - ימין ביותר
        menu_btn = QPushButton("☰")
        menu_btn.setObjectName("menuBtn")
        menu_btn.setFixedSize(40, 40)
        menu_btn.clicked.connect(self.toggle_side_menu)

        # סידור כללי בליאות הראשי
        layout.addWidget(logout_btn)       # שמאל
        layout.addWidget(title, 1)         # מרכז עם stretch
        layout.addLayout(nav_layout)       # ימין
        layout.addWidget(menu_btn)         # ימין ביותר

        return topbar

    def setup_styles(self):
        self.setStyleSheet("""
            StoreOwnerHome { background:#fafafa; }
            QFrame#topbar { background:#fff; border-bottom:1px solid #eee; }
            QPushButton#menuBtn {
                font-size:20px; border:1px solid #e5e7eb; background:#fff;
                border-radius:10px; padding:6px 10px; font-weight:500;
            }
            QPushButton#menuBtn:hover { background:#f9fafb; border-color:#3b82f6; }
            QPushButton#menuBtn:pressed { background:#f3f4f6; }
            QLabel#title { font-size:20px; font-weight:700; color:#111827; }
            QPushButton#primaryBtn {
                background:#3b82f6; color:#fff; border:1px solid #2563eb;
                border-radius:10px; padding:8px 12px; font-weight:600; min-width:120px;
            }
            QPushButton#primaryBtn:hover { background:#2563eb; transform: translateY(-1px); }
            QPushButton#primaryBtn:pressed { background:#1d4ed8; transform: translateY(0px); }
            QPushButton#secondaryBtn {
                background:#fff; color:#374151; border:1px solid #d1d5db;
                border-radius:10px; padding:8px 12px; font-weight:500; min-width:120px;
            }
            QPushButton#secondaryBtn:hover { background:#f9fafb; border-color:#3b82f6; color:#3b82f6; }
          QPushButton#ghostBtn {
    background:#fff; color:#111827; border:1px solid #dc2626;
    border-radius:10px; padding:8px 12px; font-weight:500;
}
QPushButton#ghostBtn:hover { 
    background:#fef2f2; border-color:#b91c1c; color:#dc2626; 
}""")

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
        # הסרנו את הטיפול ב-ai_chat

    def show_orders_page(self): self.show_page("orders")
    def show_new_order_page(self): self.show_suppliers_page()
    def show_suppliers_page(self): self.show_page("suppliers")

    def update_buttons_state(self, active_page: str):
        topbar = self.findChild(QFrame, "topbar")
        if not topbar:
            return
        orders_btn = None
        new_order_btn = None
        for btn in topbar.findChildren(QPushButton):
            if btn.text() == "רשימת הזמנות": orders_btn = btn
            elif btn.text() == "הזמנה חדשה": new_order_btn = btn
        if active_page == "orders":
            if orders_btn: orders_btn.setObjectName("primaryBtn")
            if new_order_btn: new_order_btn.setObjectName("secondaryBtn")
        elif active_page == "new_order":
            if orders_btn: orders_btn.setObjectName("secondaryBtn")
            if new_order_btn: new_order_btn.setObjectName("primaryBtn")
        else:  # suppliers
            if orders_btn: orders_btn.setObjectName("secondaryBtn")
            if new_order_btn: new_order_btn.setObjectName("secondaryBtn")
        self.setup_styles()

    # ===== Side menu =====
    def toggle_side_menu(self):
        if self.side_menu.isVisible():
            self.hide_side_menu()
        else:
            self.show_side_menu()

    def show_side_menu(self):
        menu_height = min(400, self.height() - 60)
        self.side_menu.resize(280, menu_height)
        menu_x = self.width() - 280  # רוחב החלון פחות רוחב התפריט
        self.side_menu.move(menu_x, 60)
        self.side_menu.show()
        self.side_menu.raise_()

    def hide_side_menu(self):
        self.side_menu.hide()

    # ===== Actions =====
    def show_menu(self): self.toggle_side_menu()
    def show_management(self): self.show_new_order_page()
    def refresh_all_data(self):
        if hasattr(self, 'orders_widget'):
            try: 
                self.orders_widget.refresh_orders()
            except: 
                pass
        current_widget = self.content_stack.currentWidget()
        if hasattr(current_widget, 'reload_from_server'): 
            current_widget.reload_from_server()
        elif hasattr(current_widget, 'refresh'): 
            current_widget.refresh()
        QMessageBox.information(self, "רענון", "כל הנתונים רוענו בהצלחה!")