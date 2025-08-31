from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QSpinBox, QMessageBox, QHeaderView
)
from PySide6.QtCore import Qt
import requests, os
from PySide6.QtWidgets import QLabel
from PySide6.QtGui import QPixmap

API_BASE = os.getenv("API_BASE", "http://127.0.0.1:8000/api/v1")


class OrderCreateDialog(QDialog):
    def __init__(self, owner_id: int, supplier_id: int, parent=None):
        super().__init__(parent)
        self.owner_id = owner_id
        self.supplier_id = supplier_id
        self.setWindowTitle("ביצוע הזמנה")
        self.resize(850, 500)
        self.setLayoutDirection(Qt.RightToLeft)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        # כותרת
        title = QLabel("בחר מוצרים להזמנה")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 20px; font-weight: 700; color: #111827;")
        layout.addWidget(title)

        # טבלה
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(
            ["מוצר", "מחיר ליחידה", "כמות מינימלית", "מלאי", "כמות להזמנה"]
        )
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.verticalHeader().setVisible(False)
        layout.addWidget(self.table, 1)

        # כפתורים
        btns = QHBoxLayout()
        btns.addStretch()

        self.btn_cancel = QPushButton("ביטול")
        self.btn_submit = QPushButton("בצע הזמנה")

        self.btn_cancel.setObjectName("secondaryBtn")
        self.btn_submit.setObjectName("primaryBtn")

        btns.addWidget(self.btn_cancel)
        btns.addWidget(self.btn_submit)
        layout.addLayout(btns)

        self.btn_cancel.clicked.connect(self.reject)
        self.btn_submit.clicked.connect(self._submit_order)

        self._setup_styles()
        self._load_products()

    def _setup_styles(self):
        self.setStyleSheet("""
            QDialog {
                background: #fafafa;
            }
            QTableWidget {
                background: #ffffff;
                border: 1px solid #e5e7eb;
                border-radius: 8px;
                gridline-color: #e5e7eb;
            }
            QHeaderView::section {
                background: #f3f4f6;
                font-weight: 600;
                padding: 6px;
                border: none;
                color: #374151;
            }
            QTableWidget::item {
                padding: 6px;
            }
            QPushButton {
                padding: 10px 20px;
                border-radius: 6px;
                font-weight: 600;
                min-width: 120px;
            }
            QPushButton#primaryBtn {
                background: #10b981;
                color: white;
                border: 1px solid #059669;
            }
            QPushButton#primaryBtn:hover {
                background: #059669;
            }
            QPushButton#secondaryBtn {
                background: #ffffff;
                color: #374151;
                border: 1px solid #d1d5db;
            }
            QPushButton#secondaryBtn:hover {
                background: #f9fafb;
                color: #10b981;
                border-color: #10b981;
            }
        """)

    def _load_products(self):
        try:
            r = requests.get(
                f"{API_BASE}/products/",
                params={"supplier_id": self.supplier_id},
                timeout=10
            )
            r.raise_for_status()
            products = r.json()
        except Exception as e:
            QMessageBox.critical(self, "שגיאה", f"שגיאה בטעינת מוצרים: {e}")
            self.reject()
            return

        self.table.setRowCount(len(products))
        for row, p in enumerate(products):
            # שם המוצר
            self.table.setItem(row, 0, QTableWidgetItem(p.get("product_name", "")))

            # מחיר ליחידה
            self.table.setItem(row, 1, QTableWidgetItem(f"{p.get('unit_price', 0):.2f} ₪"))

            # כמות מינימלית
            min_q = p.get("min_quantity", 1)
            self.table.setItem(row, 2, QTableWidgetItem(str(min_q)))

            # מלאי
            self.table.setItem(row, 3, QTableWidgetItem(str(p.get("stock", 0))))

            # שדה כמות להזמנה
            spin = QSpinBox()
            spin.setMinimum(min_q)
            spin.setMaximum(p.get("stock", 9999))
            spin.setValue(min_q)
            self.table.setCellWidget(row, 4, spin)

            # הוספת תמונה (אם קיימת)
            if p.get("image_url"):
                img_label = QLabel()
                pixmap = QPixmap()
                if pixmap.loadFromData(requests.get(p["image_url"]).content):
                    img_label.setPixmap(pixmap.scaled(48, 48, Qt.KeepAspectRatio, Qt.SmoothTransformation))
                self.table.setCellWidget(row, 0, img_label)

            # שמירת ה־ID של המוצר
            self.table.setVerticalHeaderItem(row, QTableWidgetItem(str(p["id"])))
