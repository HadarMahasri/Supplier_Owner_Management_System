# frontend/views/pages/supplier_products_page.py
from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional
import os

from PySide6.QtCore import Qt, Signal, QThread
from PySide6.QtGui import QPixmap, QBrush, QPalette, QFont
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton, QLabel, QScrollArea,
    QFrame, QGridLayout, QMessageBox, QSpinBox, QFileDialog, QFormLayout, QLayout,
    QStackedWidget, QProgressDialog
)

# שירת כמו אצלך
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


# ========= Thread להעלאת תמונות =========
class ImageUploadThread(QThread):
    """Thread להעלאת תמונות ל-Cloudinary בפעולה אסינכרונית"""
    upload_finished = Signal(dict)  # תוצאה
    upload_failed = Signal(str)     # הודעת שגיאה
    
    def __init__(self, supplier_id: int, image_path: str, product_data: dict, is_new_product: bool = True):
        super().__init__()
        self.supplier_id = supplier_id
        self.image_path = image_path
        self.product_data = product_data
        self.is_new_product = is_new_product
    
    def run(self):
        try:
            if self.is_new_product:
                # יצירת מוצר חדש עם תמונה
                result = api_client.create_product_with_image(
                    supplier_id=self.supplier_id,
                    name=self.product_data["name"],
                    price=self.product_data["price"],
                    min_qty=self.product_data["min_qty"],
                    stock=self.product_data["stock"],
                    image_path=self.image_path
                )
            else:
                # עדכון תמונה למוצר קיים
                product_id = self.product_data["id"]
                result = api_client.update_product_image(product_id, self.image_path)
            
            self.upload_finished.emit(result)
            
        except Exception as e:
            self.upload_failed.emit(str(e))


# ========= Embedded Edit Form - מעודכן =========
class ProductEditForm(QWidget):
    """טופס עריכה משולב בעמוד במקום dialog"""
    save_requested = Signal(dict)  # payload
    cancel_requested = Signal()
    
    def __init__(self, product: ProductDTO | None = None):
        super().__init__()
        self.product = product
        self.setLayoutDirection(Qt.RightToLeft)
        self._selected_image_path = ""
        self._upload_thread = None
        self.setup_ui()
        
    def setup_ui(self):
        self.setStyleSheet(self._form_stylesheet())
        
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Header
        header = QFrame()
        header.setObjectName("Header")
        hbox = QVBoxLayout(header)
        hbox.setContentsMargins(28, 20, 28, 12)
        hbox.setSpacing(10)
        
        title_text = "הוספת מוצר חדש" if not (self.product and self.product.id) else "עריכת מוצר"
        title = QLabel(title_text)
        title.setObjectName("DialogTitle")
        title.setAlignment(Qt.AlignCenter)
        
        line = QFrame()
        line.setObjectName("TitleLine")
        line.setFixedHeight(3)
        
        hbox.addWidget(title)
        hbox.addWidget(line)
        root.addWidget(header)

        # Content (Form)
        content = QFrame()
        form = QFormLayout(content)
        form.setFormAlignment(Qt.AlignTop | Qt.AlignRight)
        form.setLabelAlignment(Qt.AlignRight)
        form.setContentsMargins(40, 20, 40, 20)
        form.setHorizontalSpacing(12)
        form.setVerticalSpacing(14)

        # Fields
        self.name_edit = QLineEdit(self.product.name if self.product else "")
        self.name_edit.setObjectName("Input")
        self.name_edit.setPlaceholderText("לדוגמה: גבינה לבנה 5% • 500 גרם")
        
        initial_price = f"{self.product.price:.2f}" if (self.product and self.product.price > 0) else ""
        self.price_edit = QLineEdit(initial_price)
        self.price_edit.setObjectName("Input")
        self.price_edit.setPlaceholderText("לדוגמה: 5.90")

        self.min_edit = QSpinBox()
        self.min_edit.setObjectName("Spin")
        self.min_edit.setRange(0, 10**7)
        self.min_edit.setValue(self.product.min_qty if self.product else 0)

        self.stock_edit = QSpinBox()
        self.stock_edit.setObjectName("Spin")
        self.stock_edit.setRange(0, 10**7)
        self.stock_edit.setValue(self.product.stock if self.product else 0)

        # תמונה - מעודכן עם תמיכה ב-Cloudinary
        self.img_path_label = QLabel()
        self.img_path_label.setObjectName("ImagePathLabel")
        self._update_image_label()

        self.btn_no_image = QPushButton("ללא תמונה")
        self.btn_no_image.setObjectName("ImageButton")
        
        self.btn_browse = QPushButton("בחירת קובץ")
        self.btn_browse.setObjectName("ImageButton")
        
        # תמונה קטנה לתצוגה מקדימה
        self.preview_label = QLabel()
        self.preview_label.setFixedSize(120, 90)
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setObjectName("ImagePreview")
        self._update_preview()
        
        img_row = QHBoxLayout()
        img_row.setSpacing(10)
        img_row.addWidget(self.btn_no_image, 1)
        img_row.addWidget(self.btn_browse, 1)

        # Rows
        def lab(t): 
            x = QLabel(t)
            x.setObjectName("FieldLabel")
            return x
            
        form.addRow(lab("שם המוצר"), self.name_edit)
        form.addRow(lab("מחיר"), self.price_edit)

        min_label = QLabel("כמות מינימלית\nלהזמנה")
        min_label.setObjectName("FieldLabel")
        form.addRow(min_label, self.min_edit)
        
        stock_label = QLabel("כמות במלאי")
        stock_label.setObjectName("FieldLabel")
        form.addRow(stock_label, self.stock_edit)

        form.addRow(lab("תמונת המוצר"), self.img_path_label)
        form.addRow("", self._as_widget(img_row))
        form.addRow(lab("תצוגה מקדימה"), self.preview_label)

        root.addWidget(content, 1)

        # Footer
        footer = QHBoxLayout()
        footer.setContentsMargins(28, 16, 28, 24)
        
        cancel = QPushButton("ביטול")
        cancel.setObjectName("Cancel")
        
        save_text = "הוסף מוצר" if not (self.product and self.product.id) else "שמור שינויים"
        save = QPushButton(save_text)
        save.setObjectName("Save")
        
        footer.addWidget(cancel)
        footer.addStretch(1)
        footer.addWidget(save)
        root.addLayout(footer)

        # Events
        cancel.clicked.connect(self.cancel_requested.emit)
        save.clicked.connect(self._handle_save)
        self.btn_browse.clicked.connect(self._pick_image)
        self.btn_no_image.clicked.connect(self._no_image)

    def _as_widget(self, layout: QLayout) -> QWidget:
        w = QWidget()
        w.setLayout(layout)
        return w

    def _update_image_label(self):
        """עדכון תווית התמונה"""
        if self._selected_image_path and os.path.exists(self._selected_image_path):
            # תמונה מקומית חדשה נבחרה
            filename = os.path.basename(self._selected_image_path)
            self.img_path_label.setText(f"נבחר: {filename}")
        elif self.product and self.product.image_url:
            # תמונה קיימת מ-Cloudinary
            self.img_path_label.setText("תמונה קיימת (Cloudinary)")
            # ← הסר את השורה הזו: self._selected_image_path = self.product.image_url
        else:
            self.img_path_label.setText("לא נבחרה תמונה")
            
    def _update_preview(self):
        """עדכון תצוגה מקדימה של התמונה"""
        if self._selected_image_path and os.path.exists(self._selected_image_path):
            # תמונה מקומית
            pix = QPixmap(self._selected_image_path)
            if not pix.isNull():
                scaled_pix = pix.scaled(self.preview_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
                self.preview_label.setPixmap(scaled_pix)
                self.preview_label.setStyleSheet("")
                return
        elif self.product and self.product.image_url and "cloudinary.com" in self.product.image_url:
            # תמונה מ-Cloudinary - נטען אותה
            try:
                import requests
                response = requests.get(self.product.image_url, timeout=10)
                if response.status_code == 200:
                    pix = QPixmap()
                    pix.loadFromData(response.content)
                    if not pix.isNull():
                        scaled_pix = pix.scaled(self.preview_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
                        self.preview_label.setPixmap(scaled_pix)
                        self.preview_label.setStyleSheet("")
                        return
            except Exception as e:
                print(f"שגיאה בטעינת תמונה מ-Cloudinary בתצוגה מקדימה: {e}")
            
            # אם הטעינה נכשלה
            self.preview_label.setText("תמונה\nמ-Cloudinary\n(שגיאה בטעינה)")
            self.preview_label.setStyleSheet("color: #f59e0b; font-weight: bold;")
            return
        
        # ללא תמונה
        self.preview_label.clear()
        self.preview_label.setText("אין תמונה")
        self.preview_label.setStyleSheet("color: #9ca3af;")

    def _pick_image(self):
        p, _ = QFileDialog.getOpenFileName(
            self, 
            "בחירת תמונת מוצר", 
            "", 
            "Images (*.png *.jpg *.jpeg *.gif *.bmp *.webp)"
        )
        if p:
            self._selected_image_path = p
            self._update_image_label()
            self._update_preview()
            self.btn_no_image.setObjectName("ImageButton")
            self.btn_browse.setObjectName("ImageButtonSelected")
        else:
            self.btn_no_image.setObjectName("ImageButtonSelected")
            self.btn_browse.setObjectName("ImageButton")
        self.setStyleSheet(self._form_stylesheet())

    def _no_image(self):
        self._selected_image_path = ""
        self._update_image_label()
        self._update_preview()
        self.btn_no_image.setObjectName("ImageButtonSelected")
        self.btn_browse.setObjectName("ImageButton")
        self.setStyleSheet(self._form_stylesheet())

    def _handle_save(self):
        payload = self._get_payload()
        if payload:
            self.save_requested.emit(payload)

    def _get_payload(self) -> Optional[dict]:
        try:
            price_text = self.price_edit.text().strip()
            if not price_text:
                price = 0.0
            else:
                price = float(price_text)
                if price < 0:
                    QMessageBox.warning(self, "שגיאה", "מחיר לא יכול להיות שלילי.")
                    return None
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
            "image_path": (self._selected_image_path if self._selected_image_path and os.path.exists(self._selected_image_path) else None),
        }

    def _form_stylesheet(self) -> str:
        return """
        QWidget { background: #ffffff; }
        QFrame#Header { background: #ffffff; }
        QLabel#DialogTitle { font-size: 22px; font-weight: 700; color: #1f2937; }
        QFrame#TitleLine { background: #3b82f6; border-radius: 2px; margin: 0 96px; }

        QLabel#FieldLabel { font-size: 14px; color: #374151; padding-top: 4px; }
        
        QLabel#ImagePathLabel { 
            padding: 10px 12px; border: 1px solid #e5e7eb; border-radius: 8px; 
            font-size: 14px; background: #f9fafb; color: #6b7280;
        }
        
        QLabel#ImagePreview {
            border: 2px dashed #e5e7eb; border-radius: 8px; background: #f9fafb;
        }

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


# ========= Stock Adjustment (embedded) - ללא שינוי =========
class StockAdjustForm(QWidget):
    """טופס עדכון מלאי משולב"""
    save_requested = Signal(int)  # new stock value
    cancel_requested = Signal()
    
    def __init__(self, product: ProductDTO):
        super().__init__()
        self.product = product
        self.setLayoutDirection(Qt.RightToLeft)
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)
        
        # כותרת
        title = QLabel(f"עדכון מלאי - {self.product.name}")
        title.setStyleSheet("font-size: 18px; font-weight: 700; color: #1f2937;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        # ספין בוקס
        form_layout = QHBoxLayout()
        form_layout.addStretch()
        
        label = QLabel("כמות במלאי:")
        label.setStyleSheet("font-size: 14px; color: #374151;")
        
        self.spin = QSpinBox()
        self.spin.setRange(0, 10**7)
        self.spin.setValue(self.product.stock)
        self.spin.setStyleSheet("padding: 8px; font-size: 14px; min-width: 100px;")
        
        form_layout.addWidget(label)
        form_layout.addWidget(self.spin)
        form_layout.addStretch()
        layout.addLayout(form_layout)
        
        # כפתורים
        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()
        
        cancel_btn = QPushButton("ביטול")
        cancel_btn.setStyleSheet("background: #6b7280; color: white; padding: 8px 16px; border-radius: 6px;")
        cancel_btn.clicked.connect(self.cancel_requested.emit)
        
        save_btn = QPushButton("שמור")
        save_btn.setStyleSheet("background: #10b981; color: white; padding: 8px 16px; border-radius: 6px;")
        save_btn.clicked.connect(lambda: self.save_requested.emit(self.spin.value()))
        
        buttons_layout.addWidget(cancel_btn)
        buttons_layout.addWidget(save_btn)
        buttons_layout.addStretch()
        layout.addLayout(buttons_layout)


# ========= Product Card - מעודכן עם תמיכה בתמונות Cloudinary =========
class ProductCard(QFrame):
    editRequested = Signal(int)
    deleteRequested = Signal(int)
    adjustStockRequested = Signal(int)

    def __init__(self, product: ProductDTO):
        super().__init__()
        self.setObjectName("ProductCard")
        self.setLayoutDirection(Qt.RightToLeft)
        self.product = product

        self.setMaximumWidth(240)

        root = QVBoxLayout(self)
        root.setSpacing(8)
        root.setContentsMargins(12, 12, 12, 12)

        # תמונה - מעודכן עם תמיכה ב-Cloudinary
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

        # כפתורים אחרים - תיקון הרווח
        actions = QHBoxLayout()
        actions.setSpacing(15)  # רווח קטן בין הכפתורים
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

    def set_image(self, url_or_path: Optional[str]):
        """הצגת תמונה - תמיכה ב-URL של Cloudinary ובקבצים מקומיים"""
        if not url_or_path:
            # אין תמונה
            self.img.setText("אין תמונה")
            self.img.setStyleSheet("color: #9ca3af; border: 1px dashed #e5e7eb;")
            return
        
        if url_or_path.startswith("http") and "cloudinary.com" in url_or_path:
            # תמונה מ-Cloudinary - נטען אותה מה-URL
            try:
                import requests
                response = requests.get(url_or_path, timeout=10)
                if response.status_code == 200:
                    pix = QPixmap()
                    pix.loadFromData(response.content)
                    if not pix.isNull():
                        scaled_pix = pix.scaled(self.img.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
                        self.img.setPixmap(scaled_pix)
                        self.img.setStyleSheet("")
                        return
            except Exception as e:
                print(f"שגיאה בטעינת תמונה מ-Cloudinary: {e}")
            
            # אם הטעינה נכשלה - הצג placeholder
            self.img.setText("תמונה מ-\nCloudinary\n(שגיאה בטעינה)")
            self.img.setStyleSheet("color: #f59e0b; font-weight: bold; border: 1px solid #f59e0b;")
            
        elif os.path.exists(url_or_path):
            # תמונה מקומית
            pix = QPixmap(url_or_path)
            if not pix.isNull():
                scaled_pix = pix.scaled(self.img.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
                self.img.setPixmap(scaled_pix)
                self.img.setStyleSheet("")
            else:
                self.img.setText("שגיאה\nבתמונה")
                self.img.setStyleSheet("color: #ef4444;")
        else:
            self.img.setText("תמונה\nלא זמינה")
            self.img.setStyleSheet("color: #f59e0b;")
    def update_stock_label(self, value: int):
        self.stock_lbl.setText(f"כמות במלאי: {value}")


# ========= Main Page - מעודכן =========
class SupplierProductsPage(QWidget):
    def __init__(self, supplier_id: int, background_image: Optional[str] = None):
        super().__init__()
        self.setWindowTitle("אזור ניהול ספק")
        self.setLayoutDirection(Qt.RightToLeft)

        self.supplier_id = supplier_id
        self._all_products: List[ProductDTO] = []
        self._cards: dict[int, ProductCard] = {}
        self._upload_thread = None

        # רקע קבוע (אופציונלי)
        if background_image and os.path.exists(background_image):
            p = self.palette()
            pix = QPixmap(background_image)
            if not pix.isNull():
                p.setBrush(QPalette.Window, QBrush(pix))
                self.setPalette(p)
                self.setAutoFillBackground(True)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(16)

        # כותרת מודרנית כמו בדפים אחרים
        title = QLabel("ניהול מוצרים עבור הספק שלי")
        title.setObjectName("productsTitle")
        root.addWidget(title)

        # עכשיו הכל embedded במקום dialogs
        self.content_stack = QStackedWidget()
        
        # עמוד רשימת מוצרים
        self.products_page = self._create_products_list_page()
        self.content_stack.addWidget(self.products_page)
        
        root.addWidget(self.content_stack, 1)
        
        self.setStyleSheet(self._stylesheet())
        self.reload_from_server()

    def _create_products_list_page(self) -> QWidget:
        """יצירת העמוד עם רשימת המוצרים"""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(24, 0, 24, 24)
        layout.setSpacing(16)

        # כותרת + הוספה
        header = QHBoxLayout()
        header.setAlignment(Qt.AlignRight)

        self.btn_add = QPushButton("הוסף מוצר חדש")
        self.btn_add.setObjectName("Primary")
        self.btn_add.clicked.connect(self._show_add_form)

        header.addWidget(self.btn_add, 0, Qt.AlignRight)
        header.addStretch(1)
        layout.addLayout(header)

        # חיפוש
        search_row = QHBoxLayout()
        search_row.setAlignment(Qt.AlignCenter)
        self.search = QLineEdit()
        self.search.setObjectName("SearchBox")
        self.search.setPlaceholderText("חיפוש מוצר…")
        self.search.textChanged.connect(self._apply_filter)
        search_row.addWidget(self.search, 0, Qt.AlignCenter)
        layout.addLayout(search_row)

        # כותרת "מוצרים קיימים במערכת" בסגנון אחיד
        sub_title = QLabel("מוצרים קיימים במערכת")
        sub_title.setObjectName("subTitle")
        layout.addWidget(sub_title)

        # אזור גלילה + גריד
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        content = QWidget()
        self.grid = QGridLayout(content)
        self.grid.setContentsMargins(8, 8, 8, 8)
        self.grid.setHorizontalSpacing(15)
        self.grid.setVerticalSpacing(15)
        scroll.setWidget(content)
        layout.addWidget(scroll, 1)

        return page

    def _show_add_form(self):
        """הצגת טופס הוספת מוצר"""
        dto = ProductDTO(id=0, supplier_id=self.supplier_id, name="", price=0.0, min_qty=0, stock=0, image_url=None)
        edit_form = ProductEditForm(dto)
        edit_form.save_requested.connect(self._handle_add_product)
        edit_form.cancel_requested.connect(self._back_to_products_list)
        
        self.content_stack.addWidget(edit_form)
        self.content_stack.setCurrentWidget(edit_form)

    def _show_edit_form(self, product: ProductDTO):
        """הצגת טופס עריכת מוצר"""
        edit_form = ProductEditForm(product)
        edit_form.save_requested.connect(lambda payload: self._handle_edit_product(product.id, payload))
        edit_form.cancel_requested.connect(self._back_to_products_list)
        
        self.content_stack.addWidget(edit_form)
        self.content_stack.setCurrentWidget(edit_form)

    def _show_stock_form(self, product: ProductDTO):
        """הצגת טופס עדכון מלאי"""
        stock_form = StockAdjustForm(product)
        stock_form.save_requested.connect(lambda new_stock: self._handle_stock_update(product.id, new_stock))
        stock_form.cancel_requested.connect(self._back_to_products_list)
        
        self.content_stack.addWidget(stock_form)
        self.content_stack.setCurrentWidget(stock_form)

    def _back_to_products_list(self):
        """חזרה לרשימת המוצרים"""
        # מסיר את הטופס הנוכחי
        current_widget = self.content_stack.currentWidget()
        if current_widget != self.products_page:
            self.content_stack.removeWidget(current_widget)
            current_widget.setParent(None)
        
        self.content_stack.setCurrentWidget(self.products_page)

    def _handle_add_product(self, payload: dict):
        """טיפול בהוספת מוצר - עם תמיכה בהעלאת תמונה"""
        try:
            image_path = payload.get("image_path")
            
            if image_path:
                # יש תמונה - נשתמש ב-Thread
                progress = QProgressDialog("מעלה מוצר עם תמונה...", "ביטול", 0, 0, self)
                progress.setWindowModality(Qt.WindowModal)
                progress.show()
                
                self._upload_thread = ImageUploadThread(
                    supplier_id=self.supplier_id,
                    image_path=image_path,
                    product_data=payload,
                    is_new_product=True
                )
                
                self._upload_thread.upload_finished.connect(
                    lambda result: self._on_upload_finished(result, progress)
                )
                self._upload_thread.upload_failed.connect(
                    lambda error: self._on_upload_failed(error, progress)
                )
                
                self._upload_thread.start()
            else:
                # אין תמונה - יצירה רגילה
                created = api_client.create_product({
                    "supplier_id": self.supplier_id,
                    "name": payload["name"],
                    "price": payload["price"],
                    "min_qty": payload["min_qty"],
                    "stock": payload["stock"]
                })
                self._add_new_product_to_list(created)
                
        except Exception as e:
            QMessageBox.critical(self, "שגיאה", f"יצירת מוצר נכשלה: {e}")

    def _on_upload_finished(self, result: dict, progress: QProgressDialog):
        """טיפול בסיום הצלחת העלאת תמונה"""
        progress.close()
        self._add_new_product_to_list(result)

    def _on_upload_failed(self, error: str, progress: QProgressDialog):
        """טיפול בכשל העלאת תמונה"""
        progress.close()
        QMessageBox.critical(self, "שגיאה", f"העלאת מוצר נכשלה: {error}")

    def _add_new_product_to_list(self, created_product: dict):
        """הוספת מוצר חדש לרשימה"""
        new = ProductDTO(
            id=created_product["id"], 
            supplier_id=created_product["supplier_id"],
            name=created_product["name"], 
            price=float(created_product["price"]),
            min_qty=int(created_product["min_qty"]), 
            stock=int(created_product["stock"]),
            image_url=created_product.get("image_url")
        )
        self._all_products.insert(0, new)
        self._render_products(self._all_products)
        self._back_to_products_list()

    def _handle_edit_product(self, pid: int, payload: dict):
        """טיפול בעריכת מוצר"""
        try:
            p = next((x for x in self._all_products if x.id == pid), None)
            if not p:
                return

            image_path = payload.get("image_path")
            
            # עדכון השדות הבסיסיים תמיד - שימוש ישירות בערכים מהטופס
            basic_update = {
                "supplier_id": p.supplier_id,
                "name": payload["name"],        # ← ישירות מהטופס
                "price": payload["price"],      # ← ישירות מהטופס  
                "min_qty": payload["min_qty"],  # ← ישירות מהטופס
                "stock": payload["stock"],     
                "image_url": p.image_url,       # שמירה על התמונה הקיימת
            }

            updated = api_client.update_product(pid, basic_update)
            
            # עדכון האובייקט המקומי עם הערכים החדשים
            p.name = updated["name"]
            p.price = float(updated["price"])
            p.min_qty = int(updated["min_qty"])
            p.stock = int(updated["stock"])

            # אם יש תמונה חדשה
            if image_path:
                progress = QProgressDialog("מעדכן תמונת מוצר...", "ביטול", 0, 0, self)
                progress.setWindowModality(Qt.WindowModal)
                progress.show()
                
                self._upload_thread = ImageUploadThread(
                    supplier_id=self.supplier_id,
                    image_path=image_path,
                    product_data={"id": pid},
                    is_new_product=False
                )
                
                self._upload_thread.upload_finished.connect(
                    lambda result: self._on_image_update_finished(result, progress, p)
                )
                self._upload_thread.upload_failed.connect(
                    lambda error: self._on_upload_failed(error, progress)
                )
                
                self._upload_thread.start()
            else:
                # אין תמונה חדשה - סיום
                self._render_products(self._all_products)
                self._back_to_products_list()
                
        except Exception as e:
            QMessageBox.critical(self, "שגיאה", f"עדכון מוצר נכשל: {e}")

    def _on_image_update_finished(self, result: dict, progress: QProgressDialog, product: ProductDTO):
        """טיפול בסיום עדכון תמונה"""
        progress.close()
        
        # עדכון ה-URL של התמונה
        if "product" in result:
            product.image_url = result["product"].get("image_url")
        elif "image_data" in result:
            product.image_url = result["image_data"].get("url")
        
        self._render_products(self._all_products)
        self._back_to_products_list()

    def _handle_stock_update(self, pid: int, new_stock: int):
        """טיפול בעדכון מלאי"""
        try:
            updated = api_client.update_stock(pid, new_stock)
            p = next((x for x in self._all_products if x.id == pid), None)
            if p:
                p.stock = int(updated["stock"])
                if pid in self._cards:
                    self._cards[pid].update_stock_label(p.stock)
            self._back_to_products_list()
        except Exception as e:
            QMessageBox.critical(self, "שגיאה", f"עדכון מלאי נכשל: {e}")

    # ---- API - ללא שינוי ----
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

        cols = 4
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
            self._render_products(self._all_products)
            return
        filtered = [p for p in self._all_products if txt in p.name]
        self._render_products(filtered)

    # ---- Actions ----
    def _edit_product(self, pid: int):
        p = next((x for x in self._all_products if x.id == pid), None)
        if p:
            self._show_edit_form(p)

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
        if p:
            self._show_stock_form(p)

    # ---- Styles ----
    def _stylesheet(self) -> str:
        return """
    QWidget { font-family: "Rubik", "Segoe UI", Arial; font-size: 14px; }
    
    /* כותרת מודרנית כמו בדפים אחרים */
    QLabel#productsTitle {
        font-size: 24px;
        font-weight: 700;
        color: #065f46;
        margin-bottom: 8px;
        padding: 12px;
        background: #ecfdf5;
        border-radius: 8px;
    }
    
    /* כותרת משנה מודרנית */
    QLabel#subTitle {
        font-size: 18px;
        font-weight: 600;
        color: #065f46;
        padding: 8px 12px;
        background: #f0fdf4;
        border-radius: 8px;
        border: 1px solid #bbf7d0;
    }

    QLineEdit#SearchBox {
        padding: 12px 16px;
        border: 2px solid #bbf7d0;
        border-radius: 25px;
        font-size: 16px;
        background: #ffffff;
        color: #111827;
        max-width: 400px;
        min-width: 300px;
    }
    QLineEdit#SearchBox:focus {
        border-color: #10b981;
        outline: none;
    }

    QFrame#ProductCard {
        background: #fff; 
        border: 1px solid #e8e8e8; 
        border-radius: 14px;
        padding: 8px;
    }
    QFrame#ProductCard:hover { 
        border-color: #10b981;
        background: #f0fdf4;
    }
    QLabel#ProductTitle { font-weight: 700; margin-top: 2px; font-size: 14px; }

    /* כפתורים רגילים */
    QPushButton { padding: 8px 12px; border-radius: 10px; border: 1px solid #A6A8AB; font-size: 16px; }
    QPushButton#Primary { 
        background: #10b981; 
        color: #fff; 
        border: none;
        padding: 6px 12px;
        font-size: 13px;
        min-width: 80px;
        max-width: 100px;
    }
    QPushButton#Primary:hover { background: #059669; }
    QPushButton#Danger { 
        background: #ffffff; 
        color: #dc2626; 
        border: 2px solid #dc2626;
        padding: 6px 12px;
        font-size: 12px;
        min-width: 80px;
        max-width: 85px;
    }
    QPushButton#Danger:hover { 
        background: #fef2f2; 
        border-color: #b91c1c;
        color: #b91c1c;
    }
    QPushButton#Light { 
        background: #f3f4f6; 
        color: #000000; 
    }
    QPushButton#Light:hover { 
        background: #e5e7eb; 
        color: #000000; 
    }
    
    /* כפתור עדכון מלאי קטן */
    QPushButton#SmallLight { 
        background: #7B7C7D; 
        color: #fff;
        padding: 4px 8px; 
        font-size: 11px; 
        border-radius: 6px;
        border: none;
        min-width: 60px;
    }
    QPushButton#SmallLight:hover { background: #6b7280; }

    QLabel#ProductImage { background: #f8fafc; border-radius: 10px; }
    """