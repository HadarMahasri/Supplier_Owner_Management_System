# frontend/views/widgets/store_owner_orders_row.py
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
    QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox, QSizePolicy, QAbstractScrollArea
)
from PySide6.QtCore import Qt, Signal
from typing import Dict
from datetime import datetime


class StoreOwnerOrdersRow(QWidget):
    """שורת הזמנה בודדת עבור בעל חנות"""
    
    expand_toggle_requested = Signal(int)  # order_id
    status_update_requested = Signal(int, str)  # order_id, new_status
    
    def __init__(self, order: Dict, is_expanded: bool, orders_service):
        super().__init__()
        self.order = order
        self.is_expanded = is_expanded
        self.orders_service = orders_service
        self.order_id = order.get("id", 0)
        
        self.setup_ui()
        self.setup_styles()
    
    def setup_ui(self):
        """בניית ממשק שורת ההזמנה"""
        container = QFrame()
        container.setObjectName("orderContainer")
        
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # שורת ההזמנה הראשית
        main_row = self._create_order_main_row()
        layout.addWidget(main_row)
        
        # פרטים מורחבים (מוסתר בהתחלה)
        if self.is_expanded:
            details = self._create_order_details()
            layout.addWidget(details)
        
        # הוספת הכל לקונטיינר הראשי
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(container)
    
    def _create_order_main_row(self) -> QWidget:
        """יצירת השורה הראשית של ההזמנה - טבלה מסונכרנת עם כותרות"""
        row = QFrame()
        row.setObjectName("orderRow")
        row.setLayoutDirection(Qt.RightToLeft)  # כיוון מימין לשמאל
        
        layout = QHBoxLayout(row)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(0)
        layout.setDirection(QHBoxLayout.RightToLeft)  # סידור מימין לשמאל
        
        # כפתור הרחבה - מימין ביותר
        expand_btn = QPushButton("<" if not self.is_expanded else "v")
        expand_btn.setObjectName("expandBtn")
        expand_btn.setFixedSize(40, 30)
        expand_btn.clicked.connect(
            lambda _=False: self.expand_toggle_requested.emit(self.order_id)
        )
        layout.addWidget(expand_btn)
        
        # פעולה
        action_widget = self._create_action_widget()
        action_widget.setMinimumWidth(180)
        action_widget.setMaximumWidth(180)
        layout.addWidget(action_widget)
        
        # סטטוס
        status_label = self._create_status_label()
        status_label.setMinimumWidth(120)
        status_label.setMaximumWidth(120)
        layout.addWidget(status_label)
        
        # סכום - יישור לימין
        total = self.order.get("total_amount", 0)
        amount_label = QLabel(f"₪ {total:,.2f}")
        amount_label.setObjectName("orderCell")
        amount_label.setAlignment(Qt.AlignCenter)
        amount_label.setMinimumWidth(140)
        amount_label.setMaximumWidth(140)
        layout.addWidget(amount_label)
        
        # שם ספק - יישור לימין לטקסט עברי
        supplier_name = self.order.get("owner_company", "ספק לא ידוע")
        supplier_label = QLabel(supplier_name)
        supplier_label.setObjectName("orderCell")
        supplier_label.setAlignment(Qt.AlignRight)  # יישור לימין לעברית
        supplier_label.setMinimumWidth(200)
        supplier_label.setMaximumWidth(200)
        layout.addWidget(supplier_label)
        
        # תאריך
        created_date = self.order.get("created_date", "")
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
        date_label.setMinimumWidth(120)
        date_label.setMaximumWidth(120)
        layout.addWidget(date_label)
        
        # מס' הזמנה - שמאל ביותר
        id_label = QLabel(f"#{self.order_id}")
        id_label.setObjectName("orderCell")
        id_label.setAlignment(Qt.AlignCenter)
        id_label.setMinimumWidth(100)
        id_label.setMaximumWidth(100)
        layout.addWidget(id_label)
        
        return row
    
    def _create_status_label(self) -> QLabel:
        """יצירת תווית סטטוס"""
        status = self.order.get("status", "בתהליך")
        lbl = QLabel(status)
        lbl.setObjectName("orderCell")
        lbl.setAlignment(Qt.AlignCenter)
        return lbl

    def _create_action_widget(self) -> QWidget:
        """יצירת widget הפעולה"""
        status = self.order.get("status", "בתהליך")

        if status == "בוצעה":
            # בעל החנות ממתין לאישור הספק
            lbl = QLabel("ממתין לאישור ספק")
            lbl.setObjectName("orderCell")
            lbl.setAlignment(Qt.AlignCenter)
            return lbl

        elif status == "בתהליך":
            # בעל החנות מאשר הגעה -> משנה ל"הושלמה"
            btn = QPushButton("אשר הגעת הזמנה")
            btn.setObjectName("statusBtnActive")
            btn.clicked.connect(self._confirm_delivery)
            return btn

        else:  # "הושלמה"
            lbl = QLabel("הזמנה הושלמה")
            lbl.setObjectName("orderCell")
            lbl.setAlignment(Qt.AlignCenter)
            return lbl
    
    def _confirm_delivery(self):
        """אישור הגעת ההזמנה"""
        reply = QMessageBox.question(
            self, "אישור שינוי סטטוס",
            f"האם לאשר הגעת הזמנה #{self.order_id}?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.status_update_requested.emit(self.order_id, "הושלמה")
    
    def _create_order_details(self) -> QWidget:
        """יצירת פרטי ההזמנה המורחבים"""
        details = QFrame()
        details.setObjectName("orderDetails")
        
        layout = QVBoxLayout(details)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)
        
        # פרטי הספק ואיש קשר - בשורה אחת
        info_layout = QHBoxLayout()  # שונה מ-QVBoxLayout ל-QHBoxLayout
        info_layout.setSpacing(30)  # רווח בין האלמנטים
        info_layout.setDirection(QHBoxLayout.RightToLeft)  # כיוון מימין לשמאל
        
        supplier_name = self.order.get("owner_company", "")
        contact_name = self.order.get("owner_name", "")
        phone = self.order.get("owner_phone", "")
        created_date = self.order.get("created_date", "")
        
        if supplier_name:
            supplier_container = QWidget()
            supplier_layout = QHBoxLayout(supplier_container)
            supplier_layout.setContentsMargins(0, 0, 0, 0)
            supplier_layout.setSpacing(8)
            supplier_layout.setDirection(QHBoxLayout.RightToLeft)

            supplier_label = QLabel("שם הספק:")
            supplier_label.setObjectName("detailLabel")
            supplier_value = QLabel(supplier_name)
            supplier_value.setObjectName("detailValue")
            
            supplier_layout.addWidget(supplier_label)
            supplier_layout.addWidget(supplier_value)
            info_layout.addWidget(supplier_container)
        
        if contact_name:
            contact_container = QWidget()
            contact_layout = QHBoxLayout(contact_container)
            contact_layout.setContentsMargins(0, 0, 0, 0)
            contact_layout.setSpacing(8)
            contact_layout.setDirection(QHBoxLayout.RightToLeft)
            
            contact_label = QLabel("איש קשר:")
            contact_label.setObjectName("detailLabel")
            contact_value = QLabel(contact_name)
            contact_value.setObjectName("detailValue")
            
            contact_layout.addWidget(contact_label)
            contact_layout.addWidget(contact_value)
            info_layout.addWidget(contact_container)
        
        if phone:
            phone_container = QWidget()
            phone_layout = QHBoxLayout(phone_container)
            phone_layout.setContentsMargins(0, 0, 0, 0)
            phone_layout.setSpacing(8)
            phone_layout.setDirection(QHBoxLayout.RightToLeft)
            
            phone_label = QLabel("טלפון:")
            phone_label.setObjectName("detailLabel")
            phone_value = QLabel(phone)
            phone_value.setObjectName("detailValue")
            
            phone_layout.addWidget(phone_label)
            phone_layout.addWidget(phone_value)
            info_layout.addWidget(phone_container)
        
        # שעת הזמנה אם יש
        if created_date:
            try:
                dt = datetime.fromisoformat(created_date.replace('Z', '+00:00'))
                time_str = dt.strftime("%H:%M")
                
                time_container = QWidget()
                time_layout = QHBoxLayout(time_container)
                time_layout.setContentsMargins(0, 0, 0, 0)
                time_layout.setSpacing(8)
                time_layout.setDirection(QHBoxLayout.RightToLeft)


                
                hours_label = QLabel("שעת הזמנה:")
                hours_label.setObjectName("detailLabel")
                hours_value = QLabel(f"{time_str}")
                hours_value.setObjectName("detailValue")
                
                time_layout.addWidget(hours_label)
                time_layout.addWidget(hours_value)
                info_layout.addWidget(time_container)
            except:
                pass
        
        # הוספת stretch כדי ליישר את הפרטים לימין
        info_layout.addStretch()
        
        layout.addLayout(info_layout)
        
        # טבלת מוצרים
        items = self.order.get("items", [])
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
            table.setAlternatingRowColors(True)
            
            layout.addWidget(table)
        
        return details
        
    def setup_styles(self):
        """הגדרת סגנונות CSS לטבלה מסונכרנת"""
        self.setStyleSheet("""
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
            padding: 8px 4px;
            color: #1e40af;
            font-size: 14px;
            font-weight: 500;
            border-right: 1px solid rgba(147, 197, 253, 0.3);
        }
        
        QLabel#orderCell:first-child {
            border-right: none;
        }
        
        /* כפתורי פעולה בתוך הטבלה */
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
        
        /* Container כללי */
        QFrame#orderContainer {
            margin-bottom: 0px;
        }
        """)