# frontend/views/widgets/order_list_for_store_owner.py
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
    QTableWidget, QTableWidgetItem, QHeaderView, QScrollArea,
    QCheckBox, QDateEdit, QMessageBox, QSpacerItem, QSizePolicy, QFileDialog,
    QLineEdit, QComboBox
)
from PySide6.QtCore import Qt, Signal, QDate, QThread
from PySide6.QtGui import QFont
import requests
import os
from typing import List, Dict, Set
from datetime import datetime, date
import json
import pandas as pd



class OrdersFetchThread(QThread):
    """Thread לטעינת הזמנות מהשרת"""
    orders_loaded = Signal(list)
    error_occurred = Signal(str)
    
    def __init__(self, base_url: str, owner_id: int):
        super().__init__()
        self.base_url = base_url
        self.owner_id = owner_id
    
    def run(self):
        try:
            orders = self._fetch_orders()
            self.orders_loaded.emit(orders)
        except Exception as e:
            self.error_occurred.emit(f"שגיאה בטעינת הזמנות: {str(e)}")
    
    def _fetch_orders(self) -> List[Dict]:
        """טעינת הזמנות מהשרת"""
        try:
            response = requests.get(
                f"{self.base_url}/api/v1/orders/owner/{self.owner_id}",
                timeout=15
            )
            if response.status_code == 200:
                return response.json()
            return []
        except Exception:
            return []
    
class OrdersForStoreOwner(QWidget):
    """רכיב רשימת הזמנות לבעל חנות"""
    
    def __init__(self, owner_id: int = None):
        super().__init__()
        self.owner_id = owner_id
        self.base_url = os.getenv("API_BASE_URL", "http://localhost:8000")
        
        # מצב הרכיב
        self.orders = []
        self.expanded_orders: Set[int] = set()
        self.display_history = False
        self.date_filter = {"from": None, "to": None}
        self.supplier_filter = ""
        
        self.setup_ui()
        self.setup_styles()
        self.load_orders()
    
    def setup_ui(self):
        """בניית הממשק"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(16)
        
        # כותרת
        title = QLabel("הזמנות שלי")
        title.setObjectName("ordersTitle")
        main_layout.addWidget(title)
        
        # פילטר תאריכים ופעולות
        filter_bar = self.create_filter_bar()
        main_layout.addWidget(filter_bar)
        
        # כותרות טבלה
        header_row = self.create_header_row()
        main_layout.addWidget(header_row)
        
        # אזור ההזמנות עם גלילה
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setFrameShape(QFrame.NoFrame)
        
        # הגדרות חשובות עבור ה-container
        self.orders_container = QWidget()
        self.orders_container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Maximum)  # שינוי חשוב!
        
        self.orders_layout = QVBoxLayout(self.orders_container)
        self.orders_layout.setContentsMargins(0, 0, 0, 0)
        self.orders_layout.setSpacing(2)
        
        scroll_area.setWidget(self.orders_container)
        main_layout.addWidget(scroll_area, 1)  # stretch

    def create_filter_bar(self) -> QWidget:
        """יצירת פס הפילטרים"""
        filter_frame = QFrame()
        filter_frame.setObjectName("filterBar")
        
        layout = QHBoxLayout(filter_frame)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(16)
        
        # קבוצת פילטר תאריכים
        filter_group = QFrame()
        filter_layout = QHBoxLayout(filter_group)
        filter_layout.setContentsMargins(0, 0, 0, 0)
        filter_layout.setSpacing(12)
        
        filter_label = QLabel("סינון לפי תאריך:")
        filter_label.setObjectName("filterLabel")
        filter_layout.addWidget(filter_label)
        
        # מתאריך
        from_label = QLabel("מתאריך")
        self.date_from = QDateEdit()
        self.date_from.setDate(QDate.currentDate().addDays(-30))
        self.date_from.setObjectName("dateInput")
        self.date_from.dateChanged.connect(self.on_date_filter_changed)
        
        filter_layout.addWidget(from_label)
        filter_layout.addWidget(self.date_from)
        
        # עד תאריך
        to_label = QLabel("עד תאריך")
        self.date_to = QDateEdit()
        self.date_to.setDate(QDate.currentDate())
        self.date_to.setObjectName("dateInput")
        self.date_to.dateChanged.connect(self.on_date_filter_changed)
        
        filter_layout.addWidget(to_label)
        filter_layout.addWidget(self.date_to)
        
        # כפתור ניקוי פילטר
        self.clear_filter_btn = QPushButton("בטל סינון")
        self.clear_filter_btn.setObjectName("clearFilterBtn")
        self.clear_filter_btn.clicked.connect(self.clear_date_filter)
        filter_layout.addWidget(self.clear_filter_btn)
        
        layout.addWidget(filter_group)
        
        # פילטר ספקים (החדש!)
        supplier_group = QFrame()
        supplier_layout = QHBoxLayout(supplier_group)
        supplier_layout.setContentsMargins(0, 0, 0, 0)
        supplier_layout.setSpacing(8)
        
        supplier_label = QLabel("חיפוש לפי ספק:")
        supplier_label.setObjectName("filterLabel")
        self.supplier_search = QLineEdit()
        self.supplier_search.setObjectName("supplierSearch")
        self.supplier_search.setPlaceholderText("הכנס שם ספק...")
        self.supplier_search.textChanged.connect(self.on_supplier_filter_changed)
        
        supplier_layout.addWidget(supplier_label)
        supplier_layout.addWidget(self.supplier_search)
        
        layout.addWidget(supplier_group)
        layout.addStretch()
        
        # כפתורי פעולות
        actions_layout = QHBoxLayout()
        actions_layout.setSpacing(10)
        
        # יצוא לאקסל
        self.export_btn = QPushButton("📥 ייצא ל-Excel (0 הזמנות)")
        self.export_btn.setObjectName("exportBtn")
        self.export_btn.clicked.connect(self.export_to_excel)
        
        # היסטוריה / פעילות
        self.history_btn = QPushButton("לצפייה בהיסטוריית ההזמנות")
        self.history_btn.setObjectName("historyBtn")
        self.history_btn.clicked.connect(self.toggle_history_view)
        
        actions_layout.addWidget(self.export_btn)
        actions_layout.addWidget(self.history_btn)
        
        layout.addLayout(actions_layout)
        
        return filter_frame
    
    def create_header_row(self) -> QWidget:
        """יצירת שורת כותרות"""
        header = QFrame()
        header.setObjectName("headerRow")
        
        layout = QHBoxLayout(header)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(0)
        
        headers = ["מס' הזמנה", "תאריך", "ספק", "סכום הזמנה", "סטטוס", "פעולה", ""]
        widths = [100, 100, 200, 120, 120, 180, 30]
        
        for i, (header_text, width) in enumerate(zip(headers, widths)):
            label = QLabel(header_text)
            label.setObjectName("headerLabel")
            label.setAlignment(Qt.AlignCenter)
            label.setMinimumWidth(width)
            if i < len(headers) - 1:  # לא האחרון
                label.setMaximumWidth(width)
            layout.addWidget(label)
        
        return header
    
    def setup_styles(self):
        self.setStyleSheet("""
        QLabel#ordersTitle {
            font-size: 24px;
            font-weight: 700;
            color: #1e40af;
            margin-bottom: 8px;
            padding: 12px;
            background: #eff6ff;
            border-radius: 8px;
        }
        
        QFrame#filterBar {
            background: #dbeafe;
            border: 1px solid #93c5fd;
            border-radius: 12px;
            margin-bottom: 8px;
        }
        
        QLabel#filterLabel {
            font-weight: 600;
            color: #1e40af;
        }
        
        QDateEdit#dateInput {
            padding: 8px 12px;
            border: 1px solid #93c5fd;
            border-radius: 8px;
            background: white;
            min-width: 130px;
            font-size: 14px;
        }
        QDateEdit#dateInput:focus {
            border: 2px solid #3b82f6;
        }
        
        QLineEdit#supplierSearch {
            padding: 8px 12px;
            border: 1px solid #93c5fd;
            border-radius: 8px;
            background: white;
            min-width: 200px;
            font-size: 14px;
        }
        QLineEdit#supplierSearch:focus {
            border: 2px solid #3b82f6;
        }
        
        QPushButton#clearFilterBtn {
            background: #f9fafb;
            color: #374151;
            border: 1px solid #d1d5db;
            border-radius: 8px;
            padding: 8px 16px;
            font-weight: 500;
        }
        QPushButton#clearFilterBtn:hover {
            background: #f3f4f6;
            border-color: #3b82f6;
        }
        
        QPushButton#exportBtn {
            background: #3b82f6;
            color: white;
            border: none;
            border-radius: 10px;
            padding: 10px 20px;
            font-weight: 600;
            font-size: 14px;
        }
        QPushButton#exportBtn:hover {
            background: #2563eb;
        }
        
        QPushButton#historyBtn {
            background: #8b5cf6;
            color: white;
            border: none;
            border-radius: 10px;
            padding: 10px 20px;
            font-weight: 600;
            font-size: 14px;
        }
        QPushButton#historyBtn:hover {
            background: #7c3aed;
        }
        
        /* כותרות הטבלה */
        QFrame#headerRow {
            background: #bfdbfe;
            border: 1px solid #93c5fd;
            border-radius: 12px 12px 0px 0px;
            margin-bottom: 0px;
        }
        
        QLabel#headerLabel {
            font-weight: 700;
            color: #1e40af;
            padding: 12px 8px;
            font-size: 14px;
        }
        
        /* שורות ההזמנות */
        QFrame#orderRow {
            background: #dbeafe;
            border: 1px solid #93c5fd;
            border-top: none;
            margin: 0px;
        }
        QFrame#orderRow:hover {
            background: #eff6ff;
        }
        
        QLabel#orderCell {
            padding: 14px 8px;
            color: #1e40af;
            font-size: 14px;
            font-weight: 500;
        }
        
        /* כפתורי סטטוס */
        QPushButton#statusBtnPending {
            background: #f59e0b;
            color: white;
            border: none;
            border-radius: 20px;
            padding: 8px 16px;
            font-weight: 600;
            font-size: 12px;
        }
        QPushButton#statusBtnPending:hover {
            background: #d97706;
        }
        
        QPushButton#statusBtnActive {
            background: #3b82f6;
            color: white;
            border: none;
            border-radius: 20px;
            padding: 8px 16px;
            font-weight: 600;
            font-size: 12px;
        }
        QPushButton#statusBtnActive:hover {
            background: #2563eb;
        }
        
        QPushButton#statusBtnCompleted {
            background: #6b7280;
            color: white;
            border: none;
            border-radius: 20px;
            padding: 8px 16px;
            font-weight: 600;
            font-size: 12px;
        }
        
        /* כפתור הרחבה */
        QPushButton#expandBtn {
            background: transparent;
            border: 1px solid #93c5fd;
            border-radius: 6px;
            font-size: 14px;
            padding: 6px;
            color: #2563eb;
        }
        QPushButton#expandBtn:hover {
            background: #eff6ff;
            border-color: #2563eb;
        }
        
        /* פרטים מורחבים */
        QFrame#orderDetails {
            background: #f8fafc;
            border: 1px solid #93c5fd;
            border-top: 1px solid #60a5fa;
            padding: 20px;
            margin: 0px;
        }
        
        QLabel#detailLabel {
            font-weight: 700;
            color: #1e40af;
            font-size: 14px;
            margin-bottom: 4px;
        }
        
        QLabel#detailValue {
            color: #374151;
            font-size: 13px;
            margin-bottom: 8px;
        }
        
        /* טבלת מוצרים בפרטים */
        QTableWidget {
            background: white;
            border: 1px solid #d1d5db;
            border-radius: 8px;
            gridline-color: #e5e7eb;
            font-size: 13px;
        }
        
        QTableWidget::item {
            padding: 8px;
            border-bottom: 1px solid #f3f4f6;
        }
        
        QTableWidget::item:selected {
            background: #eff6ff;
            color: #1e40af;
        }
        
        QHeaderView::section {
            background: #f9fafb;
            color: #374151;
            padding: 10px;
            border: 1px solid #e5e7eb;
            font-weight: 600;
        }
        
        /* Scroll area */
        QScrollArea {
            background: transparent;
            border: none;
        }
        
        /* Container כללי */
        QFrame#orderContainer {
            margin-bottom: 0px;
        }
        
        /* הודעה כשאין הזמנות */
        QLabel {
            color: #6b7280;
        }
    """)
    
    def load_orders(self):
        """טעינת הזמנות"""
        if not self.owner_id:
            self._update_orders_display([])
            return
        
        self.fetch_thread = OrdersFetchThread(self.base_url, self.owner_id)
        self.fetch_thread.orders_loaded.connect(self._on_orders_loaded)
        self.fetch_thread.error_occurred.connect(self._on_error)
        self.fetch_thread.start()
    
    def _on_orders_loaded(self, orders: List[Dict]):
        """טיפול בהזמנות שנטענו"""
        self.orders = orders
        self._update_orders_display()
    
    def _on_error(self, error: str):
        """טיפול בשגיאות"""
        QMessageBox.warning(self, "שגיאה", error)
        
    
    def _update_orders_display(self, orders_list: List[Dict] = None):
        """עדכון תצוגת ההזמנות"""
        if orders_list is None:
            orders_list = self._get_filtered_orders()
        
        # נקה הזמנות קיימות
        for i in reversed(range(self.orders_layout.count())):
            child = self.orders_layout.itemAt(i).widget()
            if child:
                child.setParent(None)
        
        # עדכן מונה יצוא
        self.export_btn.setText(f"📥 ייצא ל-Excel ({len(orders_list)} הזמנות)")
        
        # צור הזמנות חדשות
        if not orders_list:
            no_orders_label = QLabel("לא נמצאו הזמנות בהתאם לסינון הנוכחי.")
            no_orders_label.setAlignment(Qt.AlignCenter)
            no_orders_label.setStyleSheet("color: #6b7280; padding: 32px; font-size: 16px;")
            self.orders_layout.addWidget(no_orders_label)
        else:
            for order in orders_list:
                order_widget = self._create_order_widget(order)
                self.orders_layout.addWidget(order_widget)
        
        # הוסף spacer קטן רק אם יש הזמנות
        if orders_list:
            spacer = QSpacerItem(20, 20, QSizePolicy.Minimum, QSizePolicy.Expanding)
            self.orders_layout.addItem(spacer)
        else:
            # אם אין הזמנות, הוסף stretch כדי למרכז את ההודעה
            self.orders_layout.addStretch()

    
    def _create_order_widget(self, order: Dict) -> QWidget:
        """יצירת widget של הזמנה"""
        container = QFrame()
        container.setObjectName("orderContainer")
        
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # שורת ההזמנה הראשית
        main_row = self._create_order_main_row(order)
        layout.addWidget(main_row)
        
        # פרטים מורחבים (מוסתר בהתחלה)
        if order["id"] in self.expanded_orders:
            details = self._create_order_details(order)
            layout.addWidget(details)
        
        return container
    
    def _create_order_main_row(self, order: Dict) -> QWidget:
        """יצירת השורה הראשית של ההזמנה"""
        row = QFrame()
        row.setObjectName("orderRow")
        
        layout = QHBoxLayout(row)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(0)
        
        order_id = order.get("id", 0)
        
        # מס' הזמנה
        id_label = QLabel(f"#{order_id}")
        id_label.setObjectName("orderCell")
        id_label.setAlignment(Qt.AlignCenter)
        id_label.setMinimumWidth(100)
        id_label.setMaximumWidth(100)
        
        # תאריך
        created_date = order.get("created_date", "")
        if created_date:
            try:
                dt = datetime.fromisoformat(created_date.replace('Z', '+00:00'))
                date_str = dt.strftime("%d.%m.%Y")
            except:
                date_str = created_date[:10]
        else:
            date_str = ""
        
        date_label = QLabel(date_str)
        date_label.setObjectName("orderCell")
        date_label.setAlignment(Qt.AlignCenter)
        date_label.setMinimumWidth(100)
        date_label.setMaximumWidth(100)
        
        # שם ספק (במקום שם חנות!)
        supplier_name = order.get("owner_company", "ספק לא ידוע")
        supplier_label = QLabel(supplier_name)
        supplier_label.setObjectName("orderCell")
        supplier_label.setMinimumWidth(200)
        supplier_label.setMaximumWidth(200)
        
        # סכום
        total = order.get("total_amount", 0)
        amount_label = QLabel(f"₪ {total:,.2f}")
        amount_label.setObjectName("orderCell")
        amount_label.setAlignment(Qt.AlignRight)
        amount_label.setMinimumWidth(120)
        amount_label.setMaximumWidth(120)
        
        # סטטוס כפתור
        #status = order.get("status", "בתהליך")
        status_label = self._create_status_label(order)
        status_label.setMinimumWidth(120)
        status_label.setMaximumWidth(120)
        
        # פעולה
        action_widget = self._create_action_widget(order)
        action_widget.setMinimumWidth(180)
        action_widget.setMaximumWidth(180)
        
        # כפתור הרחבה
        expand_btn = QPushButton("🔽" if order_id not in self.expanded_orders else "🔼")
        expand_btn.setObjectName("expandBtn")
        expand_btn.setFixedSize(30, 30)
        expand_btn.clicked.connect(lambda _=False, oid=order_id: self._toggle_expand(oid))
        
        # הוספה ללייאאוט
        layout.addWidget(id_label)
        layout.addWidget(date_label)
        layout.addWidget(supplier_label)
        layout.addWidget(amount_label)
        layout.addWidget(status_label)   # במקום status_btn
        layout.addWidget(action_widget)  # במקום action_btn הישן שהיה מוסתר
        layout.addWidget(expand_btn)

        
        return row
    
    def _create_status_label(self, order: Dict) -> QLabel:
        status = order.get("status", "בתהליך")
        lbl = QLabel(status)
        lbl.setObjectName("orderCell")
        lbl.setAlignment(Qt.AlignCenter)
        return lbl

    def _create_action_widget(self, order: Dict) -> QWidget:
        status = order.get("status", "בתהליך")
        order_id = order.get("id", 0)

        if status == "בוצעה":
            # בעל החנות ממתין לאישור הספק
            lbl = QLabel("ממתין לאישור ספק")
            lbl.setObjectName("orderCell")
            lbl.setAlignment(Qt.AlignCenter)
            return lbl

        elif status == "בתהליך":
            # בעל החנות מאשר הגעה -> משנה ל"הושלמה"
            btn = QPushButton("אשר הגעת הזמנה")
            btn.setObjectName("statusBtnActive")  # סטייל קיים
            btn.clicked.connect(lambda _=False, oid=order_id: self._update_order_status(oid, "הושלמה"))
            return btn

        else:  # "הושלמה"
            lbl = QLabel("הזמנה הושלמה")
            lbl.setObjectName("orderCell")
            lbl.setAlignment(Qt.AlignCenter)
            return lbl

    def _create_status_button(self, order: Dict) -> QPushButton:
        """יצירת כפתור סטטוס/פעולה לבעל חנות"""
        status = order.get("status", "בתהליך")
        order_id = order.get("id", 0)
        
        if status == "בוצעה":
            btn = QPushButton("הזמנה בוצעה")
            btn.setObjectName("statusBtnPending")
            btn.setEnabled(False)  # בעל חנות לא יכול לשנות סטטוס "בוצעה"
        elif status == "בתהליך":
            btn = QPushButton("אישור הגעה")
            btn.setObjectName("statusBtnActive")
            btn.clicked.connect(lambda: self._update_order_status(order_id, "הושלמה"))
        else:  # "הושלמה"
            btn = QPushButton("הזמנה הושלמה")
            btn.setObjectName("statusBtnCompleted")
            btn.setEnabled(False)
        
        return btn
    
    def _create_action_button(self, order: Dict) -> QPushButton:
        """כפתור פעולה נוסף (כרגע ריק)"""
        btn = QPushButton("")
        btn.setVisible(False)  # מוסתר כרגע
        return btn
    
    def _create_order_details(self, order: Dict) -> QWidget:
        details = QFrame()
        details.setObjectName("orderDetails")
        
        layout = QVBoxLayout(details)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)
        
        # פרטי הספק ואיש קשר
        info_layout = QVBoxLayout()
        info_layout.setSpacing(8)
        
        supplier_name = order.get("owner_company", "")
        contact_name = order.get("owner_name", "")
        phone = order.get("owner_phone", "")
        created_date = order.get("created_date", "")
        
        if supplier_name:
            supplier_label = QLabel("שם הספק:")
            supplier_label.setObjectName("detailLabel")
            supplier_value = QLabel(supplier_name)
            supplier_value.setObjectName("detailValue")
            info_layout.addWidget(supplier_label)
            info_layout.addWidget(supplier_value)
        
        if contact_name:
            contact_label = QLabel("איש קשר:")
            contact_label.setObjectName("detailLabel")
            contact_value = QLabel(contact_name)
            contact_value.setObjectName("detailValue")
            info_layout.addWidget(contact_label)
            info_layout.addWidget(contact_value)
        
        if phone:
            phone_label = QLabel("טלפון:")
            phone_label.setObjectName("detailLabel")
            phone_value = QLabel(phone)
            phone_value.setObjectName("detailValue")
            info_layout.addWidget(phone_label)
            info_layout.addWidget(phone_value)
        
        # שעות פתיחה אם יש
        if created_date:
            try:
                dt = datetime.fromisoformat(created_date.replace('Z', '+00:00'))
                time_str = dt.strftime("%H:%M")
                hours_label = QLabel("שעת הזמנה:")
                hours_label.setObjectName("detailLabel")
                hours_value = QLabel(f"{time_str}")
                hours_value.setObjectName("detailValue")
                info_layout.addWidget(hours_label)
                info_layout.addWidget(hours_value)
            except:
                pass
        
        layout.addLayout(info_layout)
        
        # טבלת מוצרים
        items = order.get("items", [])
        if items:
            products_label = QLabel("פירוט מוצרים:")
            products_label.setObjectName("detailLabel")
            layout.addWidget(products_label)
            
            table = QTableWidget()
            table.setColumnCount(4)
            table.setHorizontalHeaderLabels(["מספר מוצר", "שם מוצר", "כמות", "מחיר יחידה"])
            table.setRowCount(len(items))
            
            for row, item in enumerate(items):
                table.setItem(row, 0, QTableWidgetItem(str(item.get("product_id", ""))))
                table.setItem(row, 1, QTableWidgetItem(item.get("product_name", "")))
                table.setItem(row, 2, QTableWidgetItem(str(item.get("quantity", 0))))
                table.setItem(row, 3, QTableWidgetItem(f"₪ {item.get('unit_price', 0):.2f}"))
            
            table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
            table.setMaximumHeight(300)
            table.setAlternatingRowColors(True)
            
            layout.addWidget(table)
        
        return details
    
    def _toggle_expand(self, order_id: int):
        """החלפת מצב הרחבה של הזמנה"""
        if order_id in self.expanded_orders:
            self.expanded_orders.remove(order_id)
        else:
            self.expanded_orders.add(order_id)
        
        self._update_orders_display()
    
    def _update_order_status(self, order_id: int, new_status: str):
        """עדכון סטטוס הזמנה בשרת - רק אישור הגעה לבעל חנות"""
        
        # הודעת אישור למשתמש
        if new_status == "הושלמה":
            message = f"האם לאשר הגעת הזמנה #{order_id}?"
            success_msg = f"הזמנה #{order_id} אושרה כהושלמה!"
        else:
            return
        
        reply = QMessageBox.question(
            self, "אישור שינוי סטטוס",
            message,
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            return
        
        try:
            # שליחת בקשה לשרת - צריך לוודא שזה endpoint נכון לבעל חנות
            response = requests.put(
                f"{self.base_url}/api/v1/orders/{order_id}/status/owner",
                json={"status": new_status},
                params={"owner_id": self.owner_id},  # שים לב: owner_id ולא supplier_id
                timeout=10
            )
            
            if response.status_code == 200:
                # עדכון מקומי של הסטטוס
                for i, order in enumerate(self.orders):
                    if order.get("id") == order_id:
                        self.orders[i]["status"] = new_status
                        break
                
                # רענון התצוגה
                self._update_orders_display()
                QMessageBox.information(self, "עדכון הצליח", success_msg)
                
            else:
                error_msg = "שגיאה בעדכון הסטטוס"
                try:
                    error_detail = response.json().get("detail", "")
                    if error_detail:
                        error_msg += f": {error_detail}"
                except:
                    pass
                QMessageBox.warning(self, "שגיאה", error_msg)
                
        except requests.exceptions.Timeout:
            QMessageBox.warning(self, "שגיאה", "הבקשה נכשלה - זמן המתנה יתר על המידה")
        except requests.exceptions.ConnectionError:
            QMessageBox.warning(self, "שגיאה", "לא ניתן להתחבר לשרת")
        except Exception as e:
            QMessageBox.warning(self, "שגיאה", f"שגיאה בעדכון הסטטוס: {str(e)}")

    def _get_filtered_orders(self) -> List[Dict]:
        """קבלת הזמנות מסוננות"""
        filtered = []
        
        for order in self.orders:
            # סינון לפי היסטוריה
            status = order.get("status", "")
            if self.display_history:
                if status != "הושלמה":
                    continue
            else:
                if status == "הושלמה":
                    continue
            
            # סינון לפי תאריך
            if self.date_filter["from"] or self.date_filter["to"]:
                created_date = order.get("created_date", "")
                if created_date:
                    try:
                        order_date = datetime.fromisoformat(created_date.replace('Z', '+00:00')).date()
                        if self.date_filter["from"] and order_date < self.date_filter["from"]:
                            continue
                        if self.date_filter["to"] and order_date > self.date_filter["to"]:
                            continue
                    except:
                        continue
            
            # סינון לפי ספק (החדש!)
            if self.supplier_filter:
                supplier_name = order.get("owner_company", "").lower()
                if self.supplier_filter.lower() not in supplier_name:
                    continue
            
            filtered.append(order)
        
        return filtered
    
    # Event handlers
    def on_date_filter_changed(self):
        """טיפול בשינוי פילטר תאריכים"""
        self.date_filter["from"] = self.date_from.date().toPython()
        self.date_filter["to"] = self.date_to.date().toPython()
        self._update_orders_display()
    
    def on_supplier_filter_changed(self):
        """טיפול בשינוי פילטר ספקים"""
        self.supplier_filter = self.supplier_search.text().strip()
        self._update_orders_display()
    
    def clear_date_filter(self):
        """ניקוי פילטר תאריכים"""
        self.date_from.setDate(QDate.currentDate().addDays(-30))
        self.date_to.setDate(QDate.currentDate())
        self.date_filter = {"from": None, "to": None}
        self.supplier_search.clear()
        self.supplier_filter = ""
        self._update_orders_display()
    
    def toggle_history_view(self):
        """החלפת תצוגת היסטוריה"""
        self.display_history = not self.display_history
        
        if self.display_history:
            self.history_btn.setText("לצפייה בהזמנות שטרם הושלמו")
        else:
            self.history_btn.setText("לצפייה בהיסטוריית ההזמנות")
        
        self._update_orders_display()
    
    def export_to_excel(self):
        """יצוא הזמנות לקובץ Excel (או CSV)"""
        filtered_orders = self._get_filtered_orders()

        if not filtered_orders:
            QMessageBox.information(self, "יצוא לאקסל", "אין הזמנות לייצא")
            return

        try:
            # הכנת נתונים לשתי טבלאות: הזמנות ומוצרים
            orders_data = []
            products_data = []

            for order in filtered_orders:
                # טיפול בתאריך
                try:
                    date_str = datetime.fromisoformat(
                        order.get('created_date', '').replace('Z', '+00:00')
                    ).strftime('%d/%m/%Y') if order.get('created_date') else ''
                except Exception:
                    date_str = order.get('created_date', '')[:10]

                # נתוני הזמנה בסיסיים
                order_info = {
                    'מספר הזמנה': order.get('id', ''),
                    'תאריך': date_str,
                    'סכום ההזמנה': order.get('total_amount', 0),
                    'סטטוס': order.get('status', ''),
                    'שם הספק': order.get('owner_company', ''),
                    'איש קשר': order.get('owner_name', ''),
                    'מספר מוצרים': len(order.get('items', [])),
                }
                orders_data.append(order_info)

                # פירוט מוצרים
                for item in order.get('items', []):
                    products_data.append({
                        'מספר הזמנה': order.get('id', ''),
                        'תאריך הזמנה': date_str,
                        'שם הספק': order.get('owner_company', ''),
                        'מספר מוצר': item.get('product_id', ''),
                        'שם מוצר': item.get('product_name', ''),
                        'כמות': item.get('quantity', 0),
                        'מחיר יחידה': item.get('unit_price', 0),
                        'סכום מוצר': (item.get('quantity', 0) or 0) * (item.get('unit_price', 0) or 0),
                    })

            # שם קובץ מוצע
            from datetime import date
            suggested = f"הזמנות_בעל_חנות_{self.owner_id or ''}_{date.today():%Y-%m-%d}_{'היסטוריה' if self.display_history else 'פעילות'}.xlsx"

            # חלון בחירת קובץ
            path, _ = QFileDialog.getSaveFileName(
                self,
                "שמירת דוח הזמנות",
                suggested,
                "Excel (*.xlsx);;CSV (*.csv)"
            )
            if not path:
                return

            import pandas as pd

            df_orders = pd.DataFrame(orders_data)
            df_products = pd.DataFrame(products_data)

            if path.lower().endswith(".csv"):
                # אם בחרו CSV – שומרים שני קבצים נפרדים
                base = path[:-4]
                orders_csv = base + "_הזמנות.csv"
                products_csv = base + "_מוצרים.csv"
                df_orders.to_csv(orders_csv, index=False, encoding="utf-8-sig")
                df_products.to_csv(products_csv, index=False, encoding="utf-8-sig")

                QMessageBox.information(
                    self, "יצוא הושלם",
                    f"נשמרו שני קבצי CSV:\n• {orders_csv}\n• {products_csv}"
                )
            else:
                # קובץ Excel עם שני גיליונות
                with pd.ExcelWriter(path, engine="xlsxwriter") as writer:
                    df_orders.to_excel(writer, sheet_name="הזמנות", index=False)
                    df_products.to_excel(writer, sheet_name="מוצרים", index=False)

                    # התאמת רוחב עמודות בסיסי
                    for sheet_name, df in [("הזמנות", df_orders), ("מוצרים", df_products)]:
                        ws = writer.sheets[sheet_name]
                        for col_idx, col in enumerate(df.columns):
                            ws.set_column(col_idx, col_idx, max(12, min(50, len(str(col)) + 6)))

                QMessageBox.information(self, "יצוא הושלם", f"הקובץ נשמר בהצלחה:\n{path}")

        except Exception as e:
            QMessageBox.critical(self, "שגיאת יצוא", f"שגיאה בייצוא הקובץ:\n{str(e)}")


    def refresh_orders(self):
        """רענון רשימת הזמנות"""
        self.load_orders()
        QMessageBox.information(self, "רענון", "רשימת ההזמנות רועננה!")
    
    def set_owner_id(self, owner_id: int):
        """עדכון מזהה בעל החנות"""
        self.owner_id = owner_id
        self.load_orders()