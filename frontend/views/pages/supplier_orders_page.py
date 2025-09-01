# frontend/views/pages/supplier_orders_page.py
"""
Orders management page for suppliers
Combines service, widgets and handles the main logic
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
    QScrollArea, QDateEdit, QMessageBox, QSpacerItem, QSizePolicy, QFileDialog
)
from PySide6.QtCore import Qt, Signal, QDate
from typing import List, Dict, Set
from datetime import datetime
import pandas as pd

# Import service and widgets
from services.orders_service import OrdersService, OrdersFetchThread
from views.widgets.order_list_widget import OrderRowWidget, OrderDetailsWidget, OrdersHeaderWidget


class OrdersFilterBar(QFrame):
    """Filter bar for orders"""
    
    filter_changed = Signal()
    export_requested = Signal()
    history_toggled = Signal()
    
    def __init__(self):
        super().__init__()
        self.setup_ui()
    
    def setup_ui(self):
        """Build filter bar UI"""
        self.setObjectName("filterBar")
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(16)
        
        # כפתורי פעולות - מימין
        actions_layout = QHBoxLayout()
        actions_layout.setSpacing(10)
        
        # היסטוריה / פעילות
        self.history_btn = QPushButton("לצפייה בהיסטוריית ההזמנות")
        self.history_btn.setObjectName("historyBtn")
        self.history_btn.clicked.connect(self.history_toggled.emit)
        
        # ייצוא לאקסל
        self.export_btn = QPushButton("📥 ייצא ל-Excel (0 הזמנות)")
        self.export_btn.setObjectName("exportBtn")
        self.export_btn.clicked.connect(self.export_requested.emit)
        
        actions_layout.addWidget(self.history_btn)
        actions_layout.addWidget(self.export_btn)
        
        layout.addLayout(actions_layout)
        layout.addStretch()
        
        # קבוצת פילטר תאריכים - משמאל
        filter_group = QFrame()
        filter_layout = QHBoxLayout(filter_group)
        filter_layout.setContentsMargins(0, 0, 0, 0)
        filter_layout.setSpacing(12)
        
        # כפתור ניקוי פילטר
        clear_filter_btn = QPushButton("בטל סינון")
        clear_filter_btn.setObjectName("clearFilterBtn")
        clear_filter_btn.clicked.connect(self.clear_filter)
        filter_layout.addWidget(clear_filter_btn)
        
        # עד תאריך
        to_label = QLabel("עד תאריך")
        self.date_to = QDateEdit()
        self.date_to.setDate(QDate.currentDate())
        self.date_to.setObjectName("dateInput")
        self.date_to.dateChanged.connect(self.filter_changed.emit)
        
        filter_layout.addWidget(self.date_to)
        filter_layout.addWidget(to_label)
        
        # מתאריך
        from_label = QLabel("מתאריך")
        self.date_from = QDateEdit()
        self.date_from.setDate(QDate.currentDate().addDays(-30))
        self.date_from.setObjectName("dateInput")
        self.date_from.dateChanged.connect(self.filter_changed.emit)
        
        filter_layout.addWidget(self.date_from)
        filter_layout.addWidget(from_label)
        
        filter_label = QLabel("סינון לפי תאריך:")
        filter_label.setObjectName("filterLabel")
        filter_layout.addWidget(filter_label)
        
        layout.addWidget(filter_group)
    
    def clear_filter(self):
        """Clear date filter"""
        self.date_from.setDate(QDate.currentDate().addDays(-30))
        self.date_to.setDate(QDate.currentDate())
        self.filter_changed.emit()
    
    def get_date_range(self):
        """Get selected date range"""
        return self.date_from.date().toPython(), self.date_to.date().toPython()
    
    def update_export_count(self, count: int):
        """Update export button text with count"""
        self.export_btn.setText(f"📥 ייצא ל-Excel ({count} הזמנות)")
    
    def toggle_history_button(self, is_history: bool):
        """Toggle history button text"""
        if is_history:
            self.history_btn.setText("לצפייה בהזמנות שטרם סופקו")
        else:
            self.history_btn.setText("לצפייה בהיסטוריית ההזמנות")


class SupplierOrdersPage(QWidget):
    """Main orders page for suppliers"""
    
    def __init__(self, supplier_id: int = None):
        super().__init__()
        self.supplier_id = supplier_id
        
        # Services
        self.orders_service = OrdersService()
        
        # State
        self.orders = []
        self.filtered_orders = []
        self.expanded_orders: Set[int] = set()
        self.display_history = False
        
        self.setup_ui()
        self.setup_styles()
        self.load_orders()
    
    def setup_ui(self):
        """Build the main UI"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(16)
        
        # כותרת
        title = QLabel("רשימת הזמנות לספק")
        title.setObjectName("ordersTitle")
        main_layout.addWidget(title)
        
        # פילטר תאריכים ופעולות
        self.filter_bar = OrdersFilterBar()
        self.filter_bar.filter_changed.connect(self.apply_filters)
        self.filter_bar.export_requested.connect(self.export_to_excel)
        self.filter_bar.history_toggled.connect(self.toggle_history_view)
        main_layout.addWidget(self.filter_bar)
        
        # כותרות טבלה
        header = OrdersHeaderWidget()
        main_layout.addWidget(header)
        
        # אזור ההזמנות עם גלילה
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setFrameShape(QFrame.NoFrame)
        
        # Container for orders
        self.orders_container = QWidget()
        self.orders_container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Maximum)
        
        self.orders_layout = QVBoxLayout(self.orders_container)
        self.orders_layout.setContentsMargins(0, 0, 0, 0)
        self.orders_layout.setSpacing(2)
        
        scroll_area.setWidget(self.orders_container)
        main_layout.addWidget(scroll_area, 1)
    
    def load_orders(self):
        """Load orders from service"""
        if not self.supplier_id:
            self.update_display([])
            return
        
        self.fetch_thread = OrdersFetchThread(
            self.orders_service.base_url, 
            self.supplier_id
        )
        self.fetch_thread.orders_loaded.connect(self.on_orders_loaded)
        self.fetch_thread.error_occurred.connect(self.on_error)
        self.fetch_thread.start()
    
    def on_orders_loaded(self, orders: List[Dict]):
        """Handle loaded orders"""
        self.orders = orders
        self.apply_filters()
    
    def on_error(self, error: str):
        """Handle loading errors"""
        QMessageBox.warning(self, "שגיאה", error)
    
    def apply_filters(self):
        """Apply all filters to orders"""
        date_from, date_to = self.filter_bar.get_date_range()
        
        self.filtered_orders = self.orders_service.filter_orders(
            self.orders,
            display_history=self.display_history,
            date_from=date_from,
            date_to=date_to
        )
        
        self.update_display()
    
    def update_display(self, orders_list: List[Dict] = None):
        """Update orders display"""
        if orders_list is None:
            orders_list = self.filtered_orders
        
        # Clear existing widgets
        for i in reversed(range(self.orders_layout.count())):
            child = self.orders_layout.itemAt(i).widget()
            if child:
                child.setParent(None)
        
        # Update export count
        self.filter_bar.update_export_count(len(orders_list))
        
        # Create order widgets
        if not orders_list:
            no_orders_label = QLabel("לא נמצאו הזמנות בהתאם לסינון הנוכחי.")
            no_orders_label.setAlignment(Qt.AlignCenter)
            no_orders_label.setStyleSheet("color: #6b7280; padding: 32px; font-size: 16px;")
            self.orders_layout.addWidget(no_orders_label)
        else:
            for order in orders_list:
                container = self.create_order_container(order)
                self.orders_layout.addWidget(container)
        
        # Add spacer
        if orders_list:
            spacer = QSpacerItem(20, 20, QSizePolicy.Minimum, QSizePolicy.Expanding)
            self.orders_layout.addItem(spacer)
        else:
            self.orders_layout.addStretch()
    
    def create_order_container(self, order: Dict) -> QWidget:
        """Create container for order with row and optional details"""
        container = QFrame()
        container.setObjectName("orderContainer")
        
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Main order row
        order_id = order.get("id", 0)
        is_expanded = order_id in self.expanded_orders
        
        row = OrderRowWidget(order, is_expanded)
        row.expand_requested.connect(self.toggle_expand)
        row.status_update_requested.connect(self.update_order_status)
        layout.addWidget(row)
        
        # Details if expanded
        if is_expanded:
            details = OrderDetailsWidget(order)
            layout.addWidget(details)
        
        return container
    
    def toggle_expand(self, order_id: int):
        """Toggle order expansion"""
        if order_id in self.expanded_orders:
            self.expanded_orders.remove(order_id)
        else:
            self.expanded_orders.add(order_id)
        
        self.update_display()
    
    def update_order_status(self, order_id: int, new_status: str):
        """Update order status"""
        # Confirmation dialog
        if new_status == "בתהליך":
            message = f"האם לאשר קבלת הזמנה #{order_id}?"
            success_msg = f"הזמנה #{order_id} אושרה בהצלחה!"
        elif new_status == "הושלמה":
            message = f"האם לסמן הזמנה #{order_id} כהושלמה?"
            success_msg = f"הזמנה #{order_id} סומנה כהושלמה!"
        else:
            return
        
        reply = QMessageBox.question(
            self, "אישור שינוי סטטוס",
            message,
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            return
        
        # Call service to update status
        success, error_msg = self.orders_service.update_order_status(
            order_id, new_status, self.supplier_id
        )
        
        if success:
            # Update local status
            for i, order in enumerate(self.orders):
                if order.get("id") == order_id:
                    self.orders[i]["status"] = new_status
                    break
            
            # Refresh display
            self.apply_filters()
            QMessageBox.information(self, "עדכון הצליח", success_msg)
        else:
            QMessageBox.warning(self, "שגיאה", error_msg)
    
    def toggle_history_view(self):
        """Toggle between active and history view"""
        self.display_history = not self.display_history
        self.filter_bar.toggle_history_button(self.display_history)
        self.apply_filters()
    
    def export_to_excel(self):
        """Export orders to Excel file"""
        if not self.filtered_orders:
            QMessageBox.information(self, "ייצוא לאקסל", "אין הזמנות לייצא")
            return
        
        try:
            # Get data from service
            orders_data, products_data = self.orders_service.prepare_export_data(
                self.filtered_orders
            )
            
            # Suggest filename
            from datetime import date
            suggested = f"הזמנות_ספק_{self.supplier_id or ''}_{date.today():%Y-%m-%d}_{'היסטוריה' if self.display_history else 'פעילות'}.xlsx"
            
            # File dialog
            path, _ = QFileDialog.getSaveFileName(
                self,
                "שמירת דוח הזמנות",
                suggested,
                "Excel (*.xlsx);;CSV (*.csv)"
            )
            
            if not path:
                return
            
            # Create DataFrames
            df_orders = pd.DataFrame(orders_data)
            df_products = pd.DataFrame(products_data)
            
            if path.lower().endswith(".csv"):
                # Save as CSV files
                base = path[:-4]
                orders_csv = base + "_הזמנות.csv"
                products_csv = base + "_מוצרים.csv"
                df_orders.to_csv(orders_csv, index=False, encoding="utf-8-sig")
                df_products.to_csv(products_csv, index=False, encoding="utf-8-sig")
                
                QMessageBox.information(
                    self, "ייצוא הושלם",
                    f"נשמרו שני קבצי CSV:\n• {orders_csv}\n• {products_csv}"
                )
            else:
                # Save as Excel with two sheets
                with pd.ExcelWriter(path, engine="xlsxwriter") as writer:
                    df_orders.to_excel(writer, sheet_name="הזמנות", index=False)
                    df_products.to_excel(writer, sheet_name="מוצרים", index=False)
                    
                    # Adjust column widths
                    for sheet_name, df in [("הזמנות", df_orders), ("מוצרים", df_products)]:
                        ws = writer.sheets[sheet_name]
                        for col_idx, col in enumerate(df.columns):
                            ws.set_column(col_idx, col_idx, max(12, min(50, len(str(col)) + 6)))
                
                QMessageBox.information(self, "ייצוא הושלם", f"הקובץ נשמר בהצלחה:\n{path}")
        
        except Exception as e:
            QMessageBox.critical(self, "שגיאת ייצוא", f"שגיאה בייצוא הקובץ:\n{str(e)}")
    
    def refresh_orders(self):
        """Refresh orders list"""
        self.load_orders()
        QMessageBox.information(self, "רענון", "רשימת ההזמנות רועננה!")
    
    def set_supplier_id(self, supplier_id: int):
        """Update supplier ID and reload"""
        self.supplier_id = supplier_id
        self.load_orders()
    
    def setup_styles(self):
        """Apply styles to the page"""
        self.setStyleSheet("""
        QLabel#ordersTitle {
            font-size: 24px;
            font-weight: 700;
            color: #065f46;
            margin-bottom: 8px;
            padding: 12px;
            background: #ecfdf5;
            border-radius: 8px;
        }
        
        QFrame#filterBar {
            background: #f0fdf4;
            border: 1px solid #bbf7d0;
            border-radius: 12px;
            margin-bottom: 8px;
        }
        
        QLabel#filterLabel {
            font-weight: 600;
            color: #065f46;
        }
        
        QDateEdit#dateInput {
            padding: 8px 12px;
            border: 1px solid #bbf7d0;
            border-radius: 8px;
            background: white;
            min-width: 130px;
            font-size: 14px;
        }
        QDateEdit#dateInput:focus {
            border: 2px solid #10b981;
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
            border-color: #10b981;
        }
        
        QPushButton#exportBtn {
            background: #10b981;
            color: white;
            border: none;
            border-radius: 10px;
            padding: 10px 20px;
            font-weight: 600;
            font-size: 14px;
        }
        QPushButton#exportBtn:hover {
            background: #059669;
        }
        
        QPushButton#historyBtn {
            background: #6366f1;
            color: white;
            border: none;
            border-radius: 10px;
            padding: 10px 20px;
            font-weight: 600;
            font-size: 14px;
        }
        QPushButton#historyBtn:hover {
            background: #4f46e5;
        }
        
        /* כותרות הטבלה */
        QFrame#headerRow {
            background: #d1fae5;
            border: 1px solid #a7f3d0;
            border-radius: 12px 12px 0px 0px;
            margin-bottom: 0px;
        }
        
        QLabel#headerLabel {
            font-weight: 700;
            color: #065f46;
            padding: 12px 8px;
            font-size: 14px;
        }
        
        /* שורות ההזמנות */
        QFrame#orderRow {
            background: #f0fdf4;
            border: 1px solid #bbf7d0;
            border-top: none;
            margin: 0px;
        }
        QFrame#orderRow:hover {
            background: #ecfdf5;
        }
        
        QLabel#orderCell {
            padding: 14px 8px;
            color: #065f46;
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
            background: #10b981;
            color: white;
            border: none;
            border-radius: 20px;
            padding: 8px 16px;
            font-weight: 600;
            font-size: 12px;
        }
        QPushButton#statusBtnActive:hover {
            background: #059669;
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
            border: 1px solid #bbf7d0;
            border-radius: 6px;
            font-size: 14px;
            padding: 6px;
            color: #059669;
        }
        QPushButton#expandBtn:hover {
            background: #ecfdf5;
            border-color: #059669;
        }
        
        /* פרטים מורחבים */
        QFrame#orderDetails {
            background: #f8fafc;
            border: 1px solid #bbf7d0;
            border-top: 1px solid #a7f3d0;
            padding: 20px;
            margin: 0px;
        }
        
        QLabel#detailLabel {
            font-weight: 700;
            color: #065f46;
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
            background: #ecfdf5;
            color: #065f46;
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


# For backward compatibility - wrapper widget
class OrdersForSupplier(SupplierOrdersPage):
    """Backward compatibility wrapper"""
    pass