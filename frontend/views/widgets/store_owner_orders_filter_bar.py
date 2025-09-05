# frontend/views/widgets/store_owner_orders_filter_bar.py
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QLabel, QPushButton, QFrame,
    QDateEdit, QLineEdit
)
from PySide6.QtCore import Qt, Signal, QDate
from datetime import date


class StoreOwnerOrdersFilterBar(QWidget):
    """פס פילטרים והתאמות להזמנות בעל חנות"""
    
    date_filter_changed = Signal(object, object)  # from_date, to_date
    supplier_filter_changed = Signal(str)  # supplier_name
    clear_filter_requested = Signal()
    export_requested = Signal()
    history_toggle_requested = Signal()
    
    def __init__(self):
        super().__init__()
        self.setup_ui()
        self.setup_styles()
    
    def setup_ui(self):
        """בניית ממשק פס הפילטרים"""
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
        self.clear_filter_btn.clicked.connect(self.clear_filter_requested.emit)
        filter_layout.addWidget(self.clear_filter_btn)
        
        layout.addWidget(filter_group)
        
        # פילטר ספקים
        supplier_group = QFrame()
        supplier_layout = QHBoxLayout(supplier_group)
        supplier_layout.setContentsMargins(0, 0, 0, 0)
        supplier_layout.setSpacing(8)
        
        supplier_label = QLabel("חיפוש לפי ספק:")
        supplier_label.setObjectName("filterLabel")
        self.supplier_search = QLineEdit()
        self.supplier_search.setObjectName("supplierSearch")
        self.supplier_search.setPlaceholderText("הכנס שם ספק...")
        self.supplier_search.textChanged.connect(
            lambda text: self.supplier_filter_changed.emit(text.strip())
        )
        
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
        self.export_btn.clicked.connect(self.export_requested.emit)
        
        # היסטוריה / פעילות
        self.history_btn = QPushButton("לצפייה בהיסטוריית ההזמנות")
        self.history_btn.setObjectName("historyBtn")
        self.history_btn.clicked.connect(self.history_toggle_requested.emit)
        
        actions_layout.addWidget(self.export_btn)
        actions_layout.addWidget(self.history_btn)
        
        layout.addLayout(actions_layout)
        
        # הוספת הכל לקונטיינר הראשי
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(filter_frame)
    
    def setup_styles(self):
        """הגדרת סגנונות CSS"""
        self.setStyleSheet("""
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
            background: #0891b2;
            color: white;
            border: none;
            border-radius: 10px;
            padding: 10px 20px;
            font-weight: 600;
            font-size: 14px;
        }
        QPushButton#historyBtn:hover {
            background: #06b6d4;
        }
        """)
    
    def on_date_filter_changed(self):
        """טיפול בשינוי פילטר תאריכים"""
        from_date = self.date_from.date().toPython()
        to_date = self.date_to.date().toPython()
        self.date_filter_changed.emit(from_date, to_date)
    
    def clear_filters(self):
        """ניקוי כל הפילטרים"""
        self.date_from.setDate(QDate.currentDate().addDays(-30))
        self.date_to.setDate(QDate.currentDate())
        self.supplier_search.clear()
    
    def update_export_count(self, count: int):
        """עדכון מספר ההזמנות בכפתור היצוא"""
        self.export_btn.setText(f"📥 ייצא ל-Excel ({count} הזמנות)")
    
    def update_history_button(self, is_history_mode: bool):
        """עדכון טקסט כפתור ההיסטוריה"""
        if is_history_mode:
            self.history_btn.setText("לצפייה בהזמנות שטרם הושלמו")
        else:
            self.history_btn.setText("לצפייה בהיסטוריית ההזמנות")