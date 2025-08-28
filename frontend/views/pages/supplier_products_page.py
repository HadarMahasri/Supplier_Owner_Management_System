from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional
import os

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap, QBrush, QPalette, QFont
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton, QLabel, QScrollArea,
    QFrame, QGridLayout, QMessageBox, QSpinBox, QFileDialog, QDialog, QFormLayout, QLayout
)

# שירי כמו אצלך
from services import api_client


# ========= DTO =========
@dataclass
class ProductDTO:
    id: int
    supplier_id: int
    name: str
    price: float
    min_qty: int
    stock: int
    image_url: Optional[str] = None


# ========= Dialogs =========
class AdjustStockDialog(QDialog):
    def __init__(self, parent: QWidget, product: ProductDTO):
        super().__init__(parent)
        self.setWindowTitle(f"עדכון מלאי - {product.name}")
        self.setLayoutDirection(Qt.RightToLeft)

        form = QFormLayout(self)
        self.spin = QSpinBox()
        self.spin.setRange(0, 10**7)
        self.spin.setValue(product.stock)
        form.addRow("כמות במלאי:", self.spin)

        row = QHBoxLayout()
        ok = QPushButton("שמור")
        cancel = QPushButton("ביטול")
        ok.clicked.connect(self.accept)
        cancel.clicked.connect(self.reject)
        row.addWidget(cancel)
        row.addWidget(ok)
        form.addRow(row)

    def value(self) -> int:
        return self.spin.value()


class EditProductDialog(QDialog):
    def __init__(self, parent: QWidget, product: ProductDTO | None):
        super().__init__(parent)
        self.setWindowTitle("הוספת מוצר זמין" if not (product and product.id) else "עריכת מוצר")
        self.setLayoutDirection(Qt.RightToLeft)
        self.setFixedSize(520, 600)

        self.setStyleSheet(self._dialog_stylesheet())

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ===== Header =====
        header = QFrame(); header.setObjectName("Header")
        hbox = QVBoxLayout(header)
        hbox.setContentsMargins(28, 20, 28, 12)
        hbox.setSpacing(10)
        title = QLabel(self.windowTitle()); title.setObjectName("DialogTitle"); title.setAlignment(Qt.AlignCenter)
        line = QFrame(); line.setObjectName("TitleLine"); line.setFixedHeight(3)
        hbox.addWidget(title); hbox.addWidget(line)
        root.addWidget(header)

        # ===== Content (Form) =====
        content = QFrame()
        form = QFormLayout(content)
        form.setFormAlignment(Qt.AlignTop | Qt.AlignRight)
        form.setLabelAlignment(Qt.AlignRight)
        form.setContentsMargins(40, 20, 40, 20)   # דוחף את הכל לצד ימין
        form.setHorizontalSpacing(12)
        form.setVerticalSpacing(14)

        # Fields
        self.name_edit = QLineEdit(product.name if product else ""); self.name_edit.setObjectName("Input")
        self.name_edit.setPlaceholderText("לדוגמה: גבינה לבנה %5 · 500 גרם")
        self.price_edit = QLineEdit(f"{product.price:.2f}" if product else "0.00"); self.price_edit.setObjectName("Input")
        self.price_edit.setPlaceholderText("לדוגמה: 5.90")

        self.min_edit = QSpinBox(); self.min_edit.setObjectName("Spin")
        self.min_edit.setRange(0, 10**7)
        self.min_edit.setValue(product.min_qty if product else 0)

        self.stock_edit = QSpinBox(); self.stock_edit.setObjectName("Spin")
        self.stock_edit.setRange(0, 10**7)
        self.stock_edit.setValue(product.stock if product else 0)

        # Image field + buttons
        self.img_path = QLineEdit(product.image_url if (product and product.image_url) else "")
        self.img_path.setReadOnly(True)
        self.img_path.setObjectName("Input")

        self.btn_no_image = QPushButton("לא נבחר קובץ"); self.btn_no_image.setObjectName("ImageButtonSelected")
        self.btn_browse   = QPushButton("בחירת קובץ");   self.btn_browse.setObjectName("ImageButton")
        img_row = QHBoxLayout(); img_row.setSpacing(10)
        img_row.addWidget(self.btn_no_image, 1); img_row.addWidget(self.btn_browse, 1)

        # Rows
        def lab(t): x = QLabel(t); x.setObjectName("FieldLabel"); return x
        form.addRow(lab("שם המוצר"), self.name_edit)
        form.addRow(lab("מחיר"), self.price_edit)

        # תווית בשתי שורות
        min_label = QLabel("כמות מינימלית\nלהזמנה"); min_label.setObjectName("FieldLabel")
        form.addRow(min_label, self.min_edit)

        form.addRow(lab("כמות במלאי"), self.stock_edit)
        form.addRow(lab("תמונת המוצר"), self.img_path)
        form.addRow("", self._as_widget(img_row))

        root.addWidget(content, 1)

        # ===== Footer =====
        footer = QHBoxLayout()
        footer.setContentsMargins(28, 16, 28, 24)
        cancel = QPushButton("ביטול"); cancel.setObjectName("Cancel")
        save   = QPushButton("לחץ להוספת מוצר" if not (product and product.id) else "שמור שינויים"); save.setObjectName("Save")
        footer.addWidget(cancel); footer.addStretch(1); footer.addWidget(save)
        root.addLayout(footer)

        # Events
        cancel.clicked.connect(self.reject)
        save.clicked.connect(self.accept)

        def pick_image():
            p, _ = QFileDialog.getOpenFileName(self, "בחרי תמונה", "", "Images (*.png *.jpg *.jpeg)")
            if p:
                self.img_path.setText(p)
                self.btn_no_image.setObjectName("ImageButton")
                self.btn_browse.setObjectName("ImageButtonSelected")
            else:
                self.btn_no_image.setObjectName("ImageButtonSelected")
                self.btn_browse.setObjectName("ImageButton")
            self.setStyleSheet(self._dialog_stylesheet())  # refresh

        def no_image():
            self.img_path.setText("")
            self.btn_no_image.setObjectName("ImageButtonSelected")
            self.btn_browse.setObjectName("ImageButton")
            self.setStyleSheet(self._dialog_stylesheet())

        self.btn_browse.clicked.connect(pick_image)
        self.btn_no_image.clicked.connect(no_image)

    # ----- helpers -----
    def _as_widget(self, layout: QLayout) -> QWidget:
        w = QWidget(); w.setLayout(layout); return w

    # ----- payload (לוגיקה ללא שינוי) -----
    def result_payload(self) -> Optional[dict]:
        try:
            price = float(self.price_edit.text().strip() or "0")
        except ValueError:
            QMessageBox.warning(self, "שגיאה", "מחיר לא תקין.")
            return None
        name = self.name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "שגיאה", "יש להזין שם מוצר.")
            return None
        return {
            "name": name,
            "price": price,
            "min_qty": int(self.min_edit.value()),
            "stock": int(self.stock_edit.value()),
            "image_url": (self.img_path.text().strip() or None),
        }

    # ----- styles -----
    def _dialog_stylesheet(self) -> str:
        return """
        QDialog { background: #ffffff; }
        QFrame#Header { background: #ffffff; }
        QLabel#DialogTitle { font-size: 22px; font-weight: 700; color: #1f2937; }
        QFrame#TitleLine { background: #3b82f6; border-radius: 2px; margin: 0 96px; }

        QLabel#FieldLabel { font-size: 14px; color: #374151; padding-top: 4px; }

        QLineEdit#Input {
            padding: 10px 12px; border: 1px solid #e5e7eb; border-radius: 8px; font-size: 14px;
            background: #ffffff; color: #111827;
        }
        QLineEdit#Input:focus { border-color: #3b82f6; }

        QSpinBox#Spin {
            padding: 6px 8px; border: 1px solid #e5e7eb; border-radius: 8px; font-size: 14px;
            background: #ffffff; color: #111827; min-height: 34px;
        }
        QSpinBox#Spin:focus { border-color: #3b82f6; }

        QPushButton#ImageButton {
            background: #ffffff; border: 1px solid #3b82f6; color: #3b82f6;
            padding: 10px 16px; border-radius: 8px; font-size: 13px;
        }
        QPushButton#ImageButtonSelected {
            background: #3b82f6; border: 1px solid #3b82f6; color: #ffffff;
            padding: 10px 16px; border-radius: 8px; font-size: 13px;
        }

        QPushButton#Cancel {
            background: #6b7280; color: #ffffff; border: none; padding: 12px 24px; border-radius: 8px; font-size: 14px;
        }
        QPushButton#Cancel:hover { background: #4b5563; }
        QPushButton#Save {
            background: #2563eb; color: #ffffff; border: none; padding: 12px 24px; border-radius: 8px; font-size: 14px;
        }
        QPushButton#Save:hover { background: #1d4ed8; }
        """



# ========= Product Card =========
class ProductCard(QFrame):
    editRequested = Signal(int)
    deleteRequested = Signal(int)
    adjustStockRequested = Signal(int)

    def __init__(self, product: ProductDTO):
        super().__init__()
        self.setObjectName("ProductCard")
        self.setLayoutDirection(Qt.RightToLeft)
        self.product = product

        # כרטיס בגודל סביר
        self.setMaximumWidth(240)

        root = QVBoxLayout(self)
        root.setSpacing(8)
        root.setContentsMargins(12, 12, 12, 12)

        # תמונה
        self.img = QLabel()
        self.img.setFixedHeight(120)
        self.img.setAlignment(Qt.AlignCenter)
        self.img.setObjectName("ProductImage")
        self.set_image(product.image_url)
        root.addWidget(self.img)

        # מידע
        info = QVBoxLayout()
        info.setSpacing(4)
        
        self.title_lbl = QLabel(product.name)
        self.title_lbl.setObjectName("ProductTitle")
        info.addWidget(self.title_lbl)

        self.price_lbl = QLabel(f"מחיר: {product.price:.2f} ₪")
        self.min_lbl = QLabel(f"כמות מינימלית: {product.min_qty}")

        # שורת מלאי + כפתור עדכון מלאי
        stock_row = QHBoxLayout()
        stock_row.setSpacing(8)
        self.stock_lbl = QLabel(f"כמות במלאי: {product.stock}")
        self.btn_stock = QPushButton("עדכון מלאי")
        self.btn_stock.setObjectName("SmallLight")
        self.btn_stock.clicked.connect(lambda: self.adjustStockRequested.emit(self.product.id))
        stock_row.addWidget(self.stock_lbl)
        stock_row.addStretch(1)
        stock_row.addWidget(self.btn_stock)

        info.addWidget(self.price_lbl)
        info.addWidget(self.min_lbl)
        info.addLayout(stock_row)
        root.addLayout(info)

        # כפתורים אחרים - ממורכזים יותר
        actions = QHBoxLayout()
        actions.setSpacing(6)  # רווח מופחת
        self.btn_delete = QPushButton("מחק מוצר")
        self.btn_edit   = QPushButton("ערוך מוצר")
        self.btn_delete.setObjectName("Danger")
        self.btn_edit.setObjectName("Primary")
        actions.addStretch(1)
        actions.addWidget(self.btn_delete)
        actions.addWidget(self.btn_edit)
        actions.addStretch(1)
        root.addLayout(actions)

        # סיגנלין
        self.btn_edit.clicked.connect(lambda: self.editRequested.emit(self.product.id))
        self.btn_delete.clicked.connect(lambda: self.deleteRequested.emit(self.product.id))

    def set_image(self, path_or_url: Optional[str]):
        if not path_or_url:
            self.img.setPixmap(QPixmap()); return
        pix = QPixmap(path_or_url)
        if not pix.isNull():
            self.img.setPixmap(pix.scaled(self.img.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))
        else:
            self.img.setPixmap(QPixmap())

    def update_stock_label(self, value: int):
        self.stock_lbl.setText(f"כמות במלאי: {value}")


# ========= Page =========
class SupplierProductsPage(QWidget):
    """
    עמוד ניהול מוצרים לספק - שינויי UI:
    - כרטיסים צרים/קצרים יותר
    - כפתור עדכון מלאי קטן יותר עם טקסט מקוצר
    - רווחים מצומצמים בין השורות
    - כותרת "מוצרים שקיימים במערכת" בצד ימין
    """
    def __init__(self, supplier_id: int, background_image: Optional[str] = None):
        super().__init__()
        self.setWindowTitle("אזור ניהול ספק")
        self.setLayoutDirection(Qt.RightToLeft)

        self.supplier_id = supplier_id
        self._all_products: List[ProductDTO] = []
        self._cards: dict[int, ProductCard] = {}

        # רקע קבוע (אופציונלי)
        if background_image and os.path.exists(background_image):
            p = self.palette()
            pix = QPixmap(background_image)
            if not pix.isNull():
                p.setBrush(QPalette.Window, QBrush(pix))
                self.setPalette(p)
                self.setAutoFillBackground(True)

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 24)
        root.setSpacing(10)

        # כותרת + הוספה - בצד ימין
        header = QHBoxLayout()
        header.setAlignment(Qt.AlignRight)
        title = QLabel("הוספת מוצרים עבור :"); title.setObjectName("H1")

        self.btn_add = QPushButton("הוספת מוצר")
        self.btn_add.setObjectName("Primary")
        self.btn_add.clicked.connect(self._add_product)

        header.addWidget(self.btn_add, 0, Qt.AlignRight)
        header.addWidget(title,    0, Qt.AlignRight)
        header.addStretch(1)  # דוחף לשמאל, כדי שישבו בימין
        root.addLayout(header)

        # חיפוש
        search_row = QHBoxLayout()
        search_row.setAlignment(Qt.AlignRight)
        self.search = QLineEdit(); self.search.setPlaceholderText("חיפוש מוצר…")
        self.search.textChanged.connect(self._apply_filter)
        search_row.addWidget(self.search, 1, Qt.AlignRight)
        root.addLayout(search_row)

        # כותרת "מוצרים שקיימים במערכת" - ימין (כפי שביקשת)
        sub_row = QHBoxLayout()
        sub = QLabel("מוצרים שקיימים במערכת"); sub.setObjectName("H2")
        sub_row.addWidget(sub, 0, Qt.AlignRight)
        sub_row.addStretch(1)
        root.addLayout(sub_row)

        # אזור גלילה + גריד
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)  # גלילה רק אנכית

        content = QWidget()
        self.grid = QGridLayout(content)
        self.grid.setContentsMargins(8, 8, 8, 8)
        self.grid.setHorizontalSpacing(15)
        self.grid.setVerticalSpacing(15)
        scroll.setWidget(content)
        root.addWidget(scroll, 1)

        self.setStyleSheet(self._stylesheet())
        self.reload_from_server()

    # ---- API ----
    def reload_from_server(self):
        try:
            items = api_client.get_products(self.supplier_id)
            self._all_products = [
                ProductDTO(
                    id=i["id"], supplier_id=i["supplier_id"], name=i["name"],
                    price=float(i["price"]), min_qty=int(i["min_qty"]), stock=int(i["stock"]),
                    image_url=i.get("image_url")
                ) for i in items
            ]
            self._render_products(self._all_products)
        except Exception as e:
            QMessageBox.critical(self, "שגיאה", f"שגיאה בטעינת מוצרים: {e}")

    # ---- UI logic ----
    def _render_products(self, items: List[ProductDTO]):
        for i in reversed(range(self.grid.count())):
            w = self.grid.itemAt(i).widget()
            if w: w.setParent(None)
        self._cards.clear()

        cols = 4  # <<< עמודה אחת – גלילה אנכית, מוצרים נערמים למטה
        r = c = 0
        for p in items:
            card = ProductCard(p)
            card.editRequested.connect(self._edit_product)
            card.deleteRequested.connect(self._delete_product)
            card.adjustStockRequested.connect(self._adjust_stock)
            self.grid.addWidget(card, r, c)
            self._cards[p.id] = card
            c += 1
            if c >= cols:
                c = 0; r += 1

    def _apply_filter(self, text: str):
        txt = (text or "").strip()
        if not txt:
            self._render_products(self._all_products); return
        filtered = [p for p in self._all_products if txt in p.name]
        self._render_products(filtered)

    # ---- Actions ----
    def _add_product(self):
        dto = ProductDTO(id=0, supplier_id=self.supplier_id, name="", price=0.0, min_qty=0, stock=0, image_url=None)
        dlg = EditProductDialog(self, dto)
        if dlg.exec() == QDialog.Accepted:
            payload = dlg.result_payload()
            if not payload: return
            try:
                created = api_client.create_product({
                    "supplier_id": self.supplier_id,
                    **payload
                })
                new = ProductDTO(
                    id=created["id"], supplier_id=created["supplier_id"],
                    name=created["name"], price=float(created["price"]),
                    min_qty=int(created["min_qty"]), stock=int(created["stock"]),
                    image_url=created.get("image_url")
                )
                self._all_products.insert(0, new)
                self._render_products(self._all_products)
            except Exception as e:
                QMessageBox.critical(self, "שגיאה", f"יצירת מוצר נכשלה: {e}")

    def _edit_product(self, pid: int):
        p = next((x for x in self._all_products if x.id == pid), None)
        if not p: return
        dlg = EditProductDialog(self, p)
        if dlg.exec() == QDialog.Accepted:
            payload = dlg.result_payload()
            if not payload: return
            try:
                updated = api_client.update_product(pid, payload)
                p.name = updated["name"]
                p.price = float(updated["price"])
                p.min_qty = int(updated["min_qty"])
                p.stock = int(updated.get("stock", p.stock))
                p.image_url = updated.get("image_url")
                self._render_products(self._all_products)
            except Exception as e:
                QMessageBox.critical(self, "שגיאה", f"עדכון מוצר נכשל: {e}")

    def _delete_product(self, pid: int):
        p = next((x for x in self._all_products if x.id == pid), None)
        if not p: return
        if QMessageBox.question(self, "מחיקת מוצר", f"להסיר את '{p.name}'?") == QMessageBox.Yes:
            try:
                api_client.delete_product(pid)
                self._all_products = [x for x in self._all_products if x.id != pid]
                self._render_products(self._all_products)
            except Exception as e:
                QMessageBox.critical(self, "שגיאה", f"מחיקה נכשלה: {e}")

    def _adjust_stock(self, pid: int):
        p = next((x for x in self._all_products if x.id == pid), None)
        if not p: return
        dlg = AdjustStockDialog(self, p)
        if dlg.exec() == QDialog.Accepted:
            try:
                updated = api_client.update_stock(pid, dlg.value())
                p.stock = int(updated["stock"])
                if pid in self._cards:
                    self._cards[pid].update_stock_label(p.stock)
            except Exception as e:
                QMessageBox.critical(self, "שגיאה", f"עדכון מלאי נכשל: {e}")

    # ---- Styles ----
    def _stylesheet(self) -> str:
        return """
        QWidget { font-family: "Rubik", "Segoe UI", Arial; font-size: 14px; }
        QLabel#H1 { font-size: 22px; font-weight: 700; padding: 4px 0; }
        QLabel#H2 { font-size: 16px; font-weight: 600; padding: 8px 0 0; color: #333; }

        QFrame#ProductCard {
            background: #fff; border: 1px solid #e8e8e8; border-radius: 14px;
        }
        QFrame#ProductCard:hover { border-color: #cfcfcf; }
        QLabel#ProductTitle { font-weight: 700; margin-top: 2px; font-size: 14px; }

        /* כפתורים רגילים */
        QPushButton { padding: 8px 12px; border-radius: 10px; border: 1px solid #e5e7eb; font-size: 16px; }
        QPushButton#Primary { background: #2563eb; color: #fff; border: none; }
        QPushButton#Primary:hover { background: #1d4ed8; }
        QPushButton#Danger { background: #22c55e; color: #fff; border: none; }
        QPushButton#Danger:hover { background: #16a34a; }
        QPushButton#Light { background: #f3f4f6; }
        QPushButton#Light:hover { background: #e5e7eb; }
        
        /* כפתור עדכון מלאי קטן */
        QPushButton#SmallLight { 
            background: #4ade80; 
            color: #fff;
            padding: 4px 8px; 
            font-size: 11px; 
            border-radius: 6px;
            border: none;
            min-width: 60px;
        }
        QPushButton#SmallLight:hover { background: #22c55e; }

        QLabel#ProductImage { background: #f8fafc; border-radius: 10px; }
        """


# ===== Demo run =====
if __name__ == "__main__":
    import sys
    from PySide6.QtWidgets import QApplication
    app = QApplication(sys.argv)
    BG = os.getenv("APP_BG_IMAGE", "")
    w = SupplierProductsPage(supplier_id=1, background_image=BG)
    w.resize(1200, 720)
    w.show()
    sys.exit(app.exec())
