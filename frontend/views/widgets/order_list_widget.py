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
        """Build the order row UI with RTL layout and perfect synchronization"""
        self.setObjectName("orderRow")
        self.setLayoutDirection(Qt.RightToLeft)  # כיוון מימין לשמאל
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(0)
        layout.setDirection(QHBoxLayout.RightToLeft)  # סידור מימין לשמאל
        
        # כפתור הרחבה - מימין ביותר (40px)
        expand_btn = QPushButton("🔽" if not self.is_expanded else "🔼")
        expand_btn.setObjectName("expandBtn")
        expand_btn.setFixedSize(40, 30)
        expand_btn.clicked.connect(lambda _=False, oid=self.order_id: self.expand_requested.emit(oid))
        layout.addWidget(expand_btn)
        
        # פעולה (180px)
        action_widget = self.create_action_widget()
        action_widget.setMinimumWidth(180)
        action_widget.setMaximumWidth(180)
        layout.addWidget(action_widget)
        
        # סטטוס (120px)
        status_label = self.create_status_label()
        status_label.setMinimumWidth(120)
        status_label.setMaximumWidth(120)
        layout.addWidget(status_label)
        
        # סכום הזמנה (140px)
        total = self.order.get("total_amount", 0)
        amount_label = QLabel(f"₪ {total:,.2f}")
        amount_label.setObjectName("orderCell")
        amount_label.setAlignment(Qt.AlignCenter)
        amount_label.setMinimumWidth(140)
        amount_label.setMaximumWidth(140)
        layout.addWidget(amount_label)
        
        # שם חנות (200px) - יישור לימין לעברית
        store_name = self.order.get("owner_company", "חנויות מקורי בע\"מ")
        store_label = QLabel(store_name)
        store_label.setObjectName("orderCell")
        store_label.setAlignment(Qt.AlignRight)  # יישור לימין לעברית
        store_label.setMinimumWidth(200)
        store_label.setMaximumWidth(200)
        layout.addWidget(store_label)
        
        # תאריך (120px)
        date_str = self.format_date(self.order.get("created_date", ""))
        date_label = QLabel(date_str)
        date_label.setObjectName("orderCell")
        date_label.setAlignment(Qt.AlignCenter)
        date_label.setMinimumWidth(120)
        date_label.setMaximumWidth(120)
        layout.addWidget(date_label)
        
        # מס' הזמנה - שמאל ביותר (100px)
        id_label = QLabel(f"#{self.order_id}")
        id_label.setObjectName("orderCell")
        id_label.setAlignment(Qt.AlignCenter)
        id_label.setMinimumWidth(100)
        id_label.setMaximumWidth(100)
        layout.addWidget(id_label)
    
    def create_status_label(self) -> QLabel:
        """סטטוס כתצוגת טקסט בלבד"""
        status = self.order.get("status", "בתהליך")
        label = QLabel(status)
        label.setObjectName("orderCell")
        label.setAlignment(Qt.AlignCenter)
        return label

    def create_action_widget(self) -> QWidget:
        """
        עמודת פעולה עבור ספק:
        - 'בוצעה'   -> כפתור 'לאישור קבלת ההזמנה' (מעביר ל'בתהליך')
        - 'בתהליך' -> טקסט 'ממתין לאישור בעל החנות'
        - 'הושלמה' -> טקסט 'ההזמנה הושלמה'
        """
        status = self.order.get("status", "בתהליך")

        if status == "בוצעה":
            btn = QPushButton("לאישור קבלת ההזמנה")
            btn.setObjectName("statusBtnPending")
            btn.clicked.connect(lambda _=False: self.status_update_requested.emit(self.order_id, "בתהליך"))
            return btn

        elif status == "בתהליך":
            lbl = QLabel("ממתין לאישור בעל החנות")
            lbl.setObjectName("orderCell")
            lbl.setAlignment(Qt.AlignCenter)
            return lbl

        else:  # "הושלמה"
            lbl = QLabel("ההזמנה הושלמה")
            lbl.setObjectName("orderCell")
            lbl.setAlignment(Qt.AlignCenter)
            return lbl
    
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
        """Create products table with RTL headers"""
        table = QTableWidget()
        table.setColumnCount(4)
        table.setHorizontalHeaderLabels(["מחיר יחידה", "כמות", "שם מוצר", "מספר מוצר"])
        table.setRowCount(len(items))
        
        for row, item in enumerate(items):
            table.setItem(row, 0, QTableWidgetItem(f"₪ {item.get('unit_price', 0):.2f}"))
            table.setItem(row, 1, QTableWidgetItem(str(item.get("quantity", 0))))
            table.setItem(row, 2, QTableWidgetItem(item.get("product_name", "")))
            table.setItem(row, 3, QTableWidgetItem(str(item.get("product_id", ""))))
        
        table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        table.setMaximumHeight(300)
        table.setAlternatingRowColors(True)
        
        return table


class OrdersHeaderWidget(QFrame):
    """Widget for orders table header with RTL layout"""
    
    def __init__(self):
        super().__init__()
        self.setup_ui()
    
    def setup_ui(self):
        """Build the header UI with perfect synchronization"""
        self.setObjectName("headerRow")
        self.setLayoutDirection(Qt.RightToLeft)  # כיוון מימין לשמאל
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(0)
        layout.setDirection(QHBoxLayout.RightToLeft)  # סידור מימין לשמאל
        
        # הכותרות מסודרות מימין לשמאל - תואמות בדיוק לשורות
        headers = ["", "פעולה", "סטטוס", "סכום הזמנה", "שם חנות", "תאריך", "מס' הזמנה"]
        widths = [40, 180, 120, 140, 200, 120, 100]
        alignments = [Qt.AlignCenter, Qt.AlignCenter, Qt.AlignCenter, 
                     Qt.AlignCenter, Qt.AlignRight, Qt.AlignCenter, Qt.AlignCenter]
        
        for header_text, width, alignment in zip(headers, widths, alignments):
            label = QLabel(header_text)
            label.setObjectName("headerLabel")
            label.setAlignment(alignment)
            label.setMinimumWidth(width)
            label.setMaximumWidth(width)
            layout.addWidget(label)


# הוספת סגנונות משופרים לטבלה מסונכרנת
ORDERS_TABLE_STYLES = """
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
    padding: 12px 4px;
    font-size: 14px;
    border-right: 1px solid rgba(147, 197, 253, 0.3);
}

QLabel#headerLabel:first-child {
    border-right: none;
}

/* שורות ההזמנות - טבלה מסונכרנת */
QFrame#orderRow {
    background: #dbeafe;
    border: 1px solid #93c5fd;
    border-top: none;
    margin: 0px;
    min-height: 60px;
}
QFrame#orderRow:hover {
    background: #eff6ff;
}

QLabel#orderCell {
    padding: 14px 4px;
    color: #1e40af;
    font-size: 14px;
    font-weight: 500;
    border-right: 1px solid rgba(147, 197, 253, 0.3);
}

QLabel#orderCell:first-child {
    border-right: none;
}

/* כפתורי פעולה בתוך הטבלה */
QPushButton#statusBtnPending {
    background: #f59e0b;
    color: white;
    border: none;
    border-radius: 20px;
    padding: 8px 16px;
    font-weight: 600;
    font-size: 12px;
    margin: 4px;
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
    margin: 4px;
}
QPushButton#statusBtnActive:hover {
    background: #2563eb;
}

/* כפתור הרחבה בטבלה */
QPushButton#expandBtn {
    background: transparent;
    border: 1px solid #93c5fd;
    border-radius: 6px;
    font-size: 14px;
    padding: 4px;
    color: #2563eb;
    margin: 2px;
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
"""