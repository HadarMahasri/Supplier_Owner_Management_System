# frontend/views/widgets/order_list_widget.py
"""
Base widget components for orders display
Contains reusable UI components
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
    QTableWidget, QTableWidgetItem, QHeaderView
)
from PySide6.QtCore import Qt, Signal
from typing import Dict
from datetime import datetime


class OrderRowWidget(QFrame):
    """Widget for displaying a single order row"""
    
    expand_requested = Signal(int)
    status_update_requested = Signal(int, str)
    
    def __init__(self, order: Dict, is_expanded: bool = False):
        super().__init__()
        self.order = order
        self.order_id = order.get("id", 0)
        self.is_expanded = is_expanded
        self.setup_ui()
    
    def setup_ui(self):
        """Build the order row UI"""
        self.setObjectName("orderRow")
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(0)
        
        # כפתור הרחבה - מימין
        expand_btn = QPushButton("🔽" if not self.is_expanded else "🔼")
        expand_btn.setObjectName("expandBtn")
        expand_btn.setFixedSize(30, 30)
        expand_btn.clicked.connect(lambda: self.expand_requested.emit(self.order_id))
        
        # פעולה (ריק כרגע)
        action_btn = QPushButton("")
        action_btn.setVisible(False)
        action_btn.setMinimumWidth(180)
        action_btn.setMaximumWidth(180)
        
        # סטטוס כפתור
        status_btn = self.create_status_button()
        status_btn.setMinimumWidth(120)
        status_btn.setMaximumWidth(120)
        
        # סכום
        total = self.order.get("total_amount", 0)
        amount_label = QLabel(f"₪ {total:,.2f}")
        amount_label.setObjectName("orderCell")
        amount_label.setAlignment(Qt.AlignCenter)
        amount_label.setMinimumWidth(120)
        amount_label.setMaximumWidth(120)
        
        # שם חנות
        store_name = self.order.get("owner_company", "חנויות מקורי בע\"מ")
        store_label = QLabel(store_name)
        store_label.setObjectName("orderCell")
        store_label.setAlignment(Qt.AlignCenter)
        store_label.setMinimumWidth(200)
        store_label.setMaximumWidth(200)
        
        # תאריך
        date_str = self.format_date(self.order.get("created_date", ""))
        date_label = QLabel(date_str)
        date_label.setObjectName("orderCell")
        date_label.setAlignment(Qt.AlignCenter)
        date_label.setMinimumWidth(100)
        date_label.setMaximumWidth(100)
        
        # מס' הזמנה - משמאל
        id_label = QLabel(f"#{self.order_id}")
        id_label.setObjectName("orderCell")
        id_label.setAlignment(Qt.AlignCenter)
        id_label.setMinimumWidth(100)
        id_label.setMaximumWidth(100)
        
        # הוספה ללייאאוט מימין לשמאל
        layout.addWidget(expand_btn)
        layout.addWidget(action_btn)
        layout.addWidget(status_btn)
        layout.addWidget(amount_label)
        layout.addWidget(store_label)
        layout.addWidget(date_label)
        layout.addWidget(id_label)
    
    def create_status_button(self) -> QPushButton:
        """Create status button based on order status"""
        status = self.order.get("status", "בתהליך")
        
        if status == "בוצעה":
            btn = QPushButton("לאישור קבלת הזמנה")
            btn.setObjectName("statusBtnPending")
            btn.clicked.connect(lambda: self.status_update_requested.emit(self.order_id, "בתהליך"))
        elif status == "בתהליך":
            btn = QPushButton("ההזמנה אושרה")
            btn.setObjectName("statusBtnActive")
            btn.clicked.connect(lambda: self.status_update_requested.emit(self.order_id, "הושלמה"))
        else:  # "הושלמה"
            btn = QPushButton("ההזמנה הושלמה")
            btn.setObjectName("statusBtnCompleted")
            btn.setEnabled(False)
        
        return btn
    
    def format_date(self, date_str: str) -> str:
        """Format date string for display"""
        if not date_str:
            return ""
        try:
            dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            return dt.strftime("%d.%m.%Y")
        except:
            return date_str[:10] if len(date_str) >= 10 else date_str


class OrderDetailsWidget(QFrame):
    """Widget for displaying expanded order details"""
    
    def __init__(self, order: Dict):
        super().__init__()
        self.order = order
        self.setup_ui()
    
    def setup_ui(self):
        """Build the order details UI"""
        self.setObjectName("orderDetails")
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)
        
        # פרטי החנות ואיש קשר
        info_layout = QVBoxLayout()
        info_layout.setSpacing(8)
        
        # הוספת פרטים שונים
        self.add_detail(info_layout, "שם החנות:", self.order.get("owner_company", ""))
        self.add_detail(info_layout, "איש קשר:", self.order.get("owner_name", ""))
        self.add_detail(info_layout, "טלפון:", self.order.get("owner_phone", ""))
        
        # שעת הזמנה אם יש
        created_date = self.order.get("created_date", "")
        if created_date:
            try:
                dt = datetime.fromisoformat(created_date.replace('Z', '+00:00'))
                time_str = dt.strftime("%H:%M")
                self.add_detail(info_layout, "שעת הזמנה:", time_str)
            except:
                pass
        
        layout.addLayout(info_layout)
        
        # טבלת מוצרים
        items = self.order.get("items", [])
        if items:
            products_label = QLabel("פירוט מוצרים:")
            products_label.setObjectName("detailLabel")
            layout.addWidget(products_label)
            
            table = self.create_products_table(items)
            layout.addWidget(table)
    
    def add_detail(self, layout: QVBoxLayout, label_text: str, value: str):
        """Add a detail label and value if value exists"""
        if value:
            label = QLabel(label_text)
            label.setObjectName("detailLabel")
            value_label = QLabel(value)
            value_label.setObjectName("detailValue")
            layout.addWidget(label)
            layout.addWidget(value_label)
    
    def create_products_table(self, items: list) -> QTableWidget:
        """Create products table"""
        table = QTableWidget()
        table.setColumnCount(3)
        table.setHorizontalHeaderLabels(["כמות", "שם מוצר", "מספר מוצר"])
        table.setRowCount(len(items))
        
        for row, item in enumerate(items):
            table.setItem(row, 0, QTableWidgetItem(str(item.get("quantity", 0))))
            table.setItem(row, 1, QTableWidgetItem(item.get("product_name", "")))
            table.setItem(row, 2, QTableWidgetItem(str(item.get("product_id", ""))))
        
        table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        table.setMaximumHeight(300)
        table.setAlternatingRowColors(True)
        
        return table


class OrdersHeaderWidget(QFrame):
    """Widget for orders table header"""
    
    def __init__(self):
        super().__init__()
        self.setup_ui()
    
    def setup_ui(self):
        """Build the header UI"""
        self.setObjectName("headerRow")
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(0)
        
        # הכותרות מסודרות מימין לשמאל
        headers = ["", "פעולה", "סטטוס", "סכום ההזמנה", "שם חנות", "תאריך", "מס' הזמנה"]
        widths = [30, 180, 120, 120, 200, 100, 100]
        
        for header_text, width in zip(headers, widths):
            label = QLabel(header_text)
            label.setObjectName("headerLabel")
            label.setAlignment(Qt.AlignCenter)
            label.setMinimumWidth(width)
            if header_text != "":  # לא האחרון
                label.setMaximumWidth(width)
            layout.addWidget(label)