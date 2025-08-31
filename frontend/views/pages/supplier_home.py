# frontend/views/pages/supplier_home.py
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
    QScrollArea, QMessageBox, QStackedWidget
)
from PySide6.QtCore import Qt, Signal
import os
from typing import Dict
import json, datetime
from PySide6.QtWidgets import QFileDialog
import pandas as pd


# Import the orders component and products page
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
        
        # Page 1: Orders list (default)
        orders_page = self.create_orders_page()
        self.content_stack.addWidget(orders_page)
        
        # Page 2: Products management
        products_page = self.create_products_page()
        self.content_stack.addWidget(products_page)
        
        scroll_area.setWidget(self.content_stack)
        main_layout.addWidget(scroll_area)
        
        # Start with orders page (index 0)
        self.content_stack.setCurrentIndex(0)
    
    def create_orders_page(self) -> QWidget:
        """יצירת עמוד ההזמנות (המקורי)"""
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
        
        return content_widget
    
    def create_products_page(self) -> QWidget:
        """יצירת עמוד ניהול המוצרים"""
        # Import כאן כדי למנוע circular imports
        try:
            from views.pages.supplier_products_page import SupplierProductsPage
            supplier_id = self.user_data.get('id', 1)
            products_widget = SupplierProductsPage(supplier_id)
            return products_widget
        except ImportError as e:
            # Fallback אם אין את הקובץ
            error_widget = QWidget()
            error_layout = QVBoxLayout(error_widget)
            error_layout.setContentsMargins(50, 50, 50, 50)
            
            error_label = QLabel(f"שגיאה בטעינת עמוד המוצרים:\n{str(e)}")
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
        menu_btn.clicked.connect(self.show_menu)
        
        # Title
        supplier_name = self.user_data.get('contact_name', 'ספק')
        company_name = self.user_data.get('company_name', '')
        title_text = f"נתוני ספק"
        if company_name:
            title_text += f" - {company_name}"
            
        title = QLabel(title_text)
        title.setObjectName("title")
        
        # Actions - עכשיו עם יותר אפשרויות
        actions_layout = QHBoxLayout()
        actions_layout.setSpacing(8)
        
        # כפתור הזמנות
        orders_btn = QPushButton("רשימת הזמנות")
        orders_btn.setObjectName("secondaryBtn")
        orders_btn.clicked.connect(self.show_orders_page)
        
        # כפתור ניהול מוצרים (החדש!)
        products_btn = QPushButton("ניהול מוצרים")
        products_btn.setObjectName("primaryBtn")
        products_btn.clicked.connect(self.show_products_page)

        export_btn = QPushButton("ייצוא לאקסל")
        export_btn.setObjectName("secondaryBtn")
        export_btn.clicked.connect(self.export_orders_to_excel)
        actions_layout.addWidget(export_btn)
        
        # התנתק button
        logout_btn = QPushButton("התנתק")
        logout_btn.setObjectName("ghostBtn")
        logout_btn.clicked.connect(self.logout_requested.emit)
        
        actions_layout.addWidget(orders_btn)
        actions_layout.addWidget(products_btn)
        actions_layout.addWidget(logout_btn)
        
        # Layout assembly
        layout.addWidget(menu_btn)
        layout.addWidget(title, 1)  # stretch
        layout.addLayout(actions_layout)
        
        return topbar
    
    def export_orders_to_excel(self):
        try:
            from services import api_client
            supplier_id = self.user_data.get('id')
            if not supplier_id:
                QMessageBox.warning(self, "ייצוא לאקסל", "חסר מזהה ספק.")
                return

            # שליפת הזמנות מה־API
            orders = api_client.get_orders_for_supplier(supplier_id)

            # בחירת קובץ יעד
            suggested = f"orders_supplier_{supplier_id}_{datetime.datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
            path, _ = QFileDialog.getSaveFileName(self, "שמירת דוח הזמנות", suggested, "Excel (*.xlsx);;CSV (*.csv)")
            if not path:
                return

            # ניסיון כתיבה ל־XLSX בעזרת pandas; נפילה ל־CSV אם pandas לא קיים
            try:

                # הפחתה ל־DataFrame בצורה גנרית:
                rows = []
                for o in (orders or []):
                    row = {}
                    if isinstance(o, dict):
                        for k, v in o.items():
                            if isinstance(v, (dict, list)):
                                # שדות מורכבים – נשמר כמחרוזת JSON כדי שלא נאבד מידע
                                row[k] = json.dumps(v, ensure_ascii=False)
                            else:
                                row[k] = v
                    else:
                        row["value"] = str(o)
                    rows.append(row)

                df = pd.DataFrame(rows)
                if path.lower().endswith(".csv"):
                    df.to_csv(path, index=False, encoding="utf-8-sig")
                else:
                    # יצוא לאקסל
                    with pd.ExcelWriter(path, engine="xlsxwriter") as writer:
                        df.to_excel(writer, sheet_name="Orders", index=False)
                QMessageBox.information(self, "ייצוא לאקסל", "הדוח נשמר בהצלחה.")
            except ImportError:
                # ללא pandas – נשמור CSV פשוט
                if not path.lower().endswith(".csv"):
                    path = path.rsplit(".", 1)[0] + ".csv"
                import csv
                # איסוף כל המפתחות מכל הרשומות
                keys = set()
                for o in (orders or []):
                    if isinstance(o, dict):
                        keys.update(o.keys())
                keys = list(keys) if keys else ["value"]

                with open(path, "w", newline="", encoding="utf-8-sig") as f:
                    w = csv.DictWriter(f, fieldnames=keys)
                    w.writeheader()
                    for o in (orders or []):
                        if isinstance(o, dict):
                            row = {}
                            for k in keys:
                                v = o.get(k)
                                row[k] = json.dumps(v, ensure_ascii=False) if isinstance(v, (dict, list)) else v
                            w.writerow(row)
                        else:
                            w.writerow({"value": str(o)})

                QMessageBox.information(self, "ייצוא ל-CSV", "הדוח נשמר כ-CSV (pandas לא מותקן).")

        except Exception as e:
            QMessageBox.critical(self, "שגיאה ביצוא", f"שגיאה: {e}")
    
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
    
    # Navigation methods - החדשים!
    def show_orders_page(self):
        """מעבר לעמוד הזמנות"""
        self.content_stack.setCurrentIndex(0)
        self.update_buttons_state(active_page="orders")
    
    def show_products_page(self):
        """מעבר לעמוד ניהול מוצרים"""
        self.content_stack.setCurrentIndex(1)
        self.update_buttons_state(active_page="products")
    
    def update_buttons_state(self, active_page: str):
        """עדכון מראה הכפתורים לפי העמוד הפעיל"""
        # מציאת הכפתורים בtopbar
        topbar = self.findChild(QFrame, "topbar")
        if not topbar:
            return
            
        orders_btn = None
        products_btn = None
        
        for btn in topbar.findChildren(QPushButton):
            if btn.text() == "רשימת הזמנות":
                orders_btn = btn
            elif btn.text() == "ניהול מוצרים":
                products_btn = btn
        
        if active_page == "orders":
            if orders_btn:
                orders_btn.setObjectName("primaryBtn")
            if products_btn:
                products_btn.setObjectName("secondaryBtn")
        else:  # products
            if orders_btn:
                orders_btn.setObjectName("secondaryBtn")
            if products_btn:
                products_btn.setObjectName("primaryBtn")
        
        # רענון הסגנון
        self.setup_styles()
    
    # Event handlers המקוריים
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
        
        # הוספת פעולות לתפריט
        reply = QMessageBox.information(self, "תפריט", menu_text + "\n\nלחץ OK להמשך")
        
        # אפשר להוסיף לוגיקה נוספת כאן לעתיד
    
    def show_management(self):
        """ניהול מערכת - עכשיו מפנה לניהול מוצרים"""
        self.show_products_page()
    
    def refresh_all_data(self):
        """רענון כל הנתונים"""
        # רענון הזמנות
        if hasattr(self, 'orders_widget'):
            self.orders_widget.refresh_orders()
        
        # רענון מוצרים
        current_widget = self.content_stack.currentWidget()
        if hasattr(current_widget, 'reload_from_server'):
            current_widget.reload_from_server()
        
        QMessageBox.information(self, "רענון", "כל הנתונים רוענו בהצלחה!")