# frontend/views/widgets/order_list_for_supplier.py

from PySide6.QtWidgets import QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem, QLabel
from PySide6.QtCore import Qt


class OrderListForSupplier(QWidget):
    def __init__(self):
        super().__init__()

        layout = QVBoxLayout(self)

        lbl_title = QLabel("רשימת הזמנות")
        lbl_title.setStyleSheet("font-size:18px; font-weight:bold; margin:8px;")

        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["מספר הזמנה", "לקוח", "תאריך", "סטטוס"])

        # דוגמאות זמניות (דמה)
        demo_orders = [
            {"id": 101, "customer": "חנות א", "date": "2025-08-20", "status": "ממתין"},
            {"id": 102, "customer": "חנות ב", "date": "2025-08-21", "status": "אושר"},
        ]
        self._populate_table(demo_orders)

        self.table.cellClicked.connect(self._toggle_details)

        layout.addWidget(lbl_title)
        layout.addWidget(self.table)

        # נשמור מצב של אילו הזמנות פתוחות
        self.open_rows = set()

    def _populate_table(self, orders: list[dict]):
        """מכניס נתוני הזמנות לטבלה"""
        self.table.setRowCount(0)
        for row_idx, order in enumerate(orders):
            self.table.insertRow(row_idx)
            self.table.setItem(row_idx, 0, QTableWidgetItem(str(order["id"])))
            self.table.setItem(row_idx, 1, QTableWidgetItem(order["customer"]))
            self.table.setItem(row_idx, 2, QTableWidgetItem(order["date"]))
            self.table.setItem(row_idx, 3, QTableWidgetItem(order["status"]))

    def _toggle_details(self, row, col):
        """פותח/סוגר שורת פרטים מתחת להזמנה"""
        order_id = self.table.item(row, 0).text()

        if row in self.open_rows:
            # אם כבר פתוח → נסגור
            self.table.removeRow(row + 1)
            self.open_rows.remove(row)
        else:
            # נפתח שורה נוספת עם פרטי הזמנה
            self.table.insertRow(row + 1)
            details_item = QTableWidgetItem(f"פרטי הזמנה {order_id}: \n- מוצר א (x3)\n- מוצר ב (x5)")
            details_item.setFlags(Qt.ItemIsEnabled)  # אי אפשר לערוך
            self.table.setSpan(row + 1, 0, 1, self.table.columnCount())  # פריסה על כל העמודות
            self.table.setItem(row + 1, 0, details_item)
            self.open_rows.add(row)
