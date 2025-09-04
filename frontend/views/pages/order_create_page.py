# frontend/views/pages/order_create_page.py
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QLineEdit, QMessageBox, QFrame, QCheckBox
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap, QIntValidator
from typing import Optional
from services import owner_portal_service as svc

class SimpleQuantityInput(QWidget):
    valueChanged = Signal(int)
    def __init__(self, minimum=1, maximum=10**9, value=1):
        super().__init__()
        self.minimum_val = int(minimum)
        self.maximum_val = int(maximum)
        self._build_ui()
        self.setValue(value)
    
    def _build_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        
        self.label = QLabel("כמות:")
        self.label.setStyleSheet("font-size: 13px; font-weight: 600; color: #374151; min-width: 40px;")
        
        self.line = QLineEdit()
        self.line.setFixedHeight(36)
        self.line.setFixedWidth(80)
        self.line.setAlignment(Qt.AlignCenter)
        self.line.setPlaceholderText("0")
        self.line.setObjectName("qtyInput")
        self.line.setValidator(QIntValidator(0, max(1_000_000_000, self.maximum_val)))
        self.line.textChanged.connect(self._emit_if_valid)
        
        layout.addWidget(self.label)
        layout.addWidget(self.line)
        layout.addStretch()
    
    def _emit_if_valid(self, _):
        v = self.value()
        if v is not None:
            self.valueChanged.emit(v)
    
    def setEnabledEditing(self, enabled: bool, ensure_min: Optional[int] = None):
        self.line.setReadOnly(not enabled)
        if enabled and ensure_min is not None and (self.value() or 0) < ensure_min:
            self.setValue(ensure_min)
    
    def setValue(self, v: int):
        try:
            v = int(v)
        except Exception:
            v = 0
        self.line.setText(str(v))
    
    def value(self) -> Optional[int]:
        txt = self.line.text().strip()
        if not txt:
            return 0
        try:
            return int(txt)
        except ValueError:
            return None


class OrderCreatePage(QWidget):
    canceled = Signal()
    submitted = Signal()

    def __init__(self, owner_id: int, supplier_id: int, parent=None):
        super().__init__(parent)
        self.owner_id = owner_id
        self.supplier_id = supplier_id
        self.products = []
        self.product_widgets = {}

        self.setLayoutDirection(Qt.RightToLeft)
        self.setup_ui()
        self._setup_styles()
        self._load_products()

    def setup_ui(self):
        """בניית ממשק מעוצב ומודרני (עם כותרת ותקציר קומפקטיים)"""
        # עיקרי העמוד
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(12, 12, 12, 12)   # היה 24
        main_layout.setSpacing(12)                       # היה 20

        # כותרת מעוצבת
        header_frame = QFrame()
        header_frame.setObjectName("headerFrame")
        header_layout = QVBoxLayout(header_frame)
        header_layout.setContentsMargins(12, 8, 12, 8)   # היה 20,16,20,16
        header_layout.setSpacing(4)                      # היה 8
        header_frame.setMaximumHeight(72)                # מגבלה לגובה הכותרת

        title = QLabel("בחר מוצרים להזמנה")
        title.setObjectName("pageTitle")
        title.setAlignment(Qt.AlignCenter)

        subtitle = QLabel("בחר את המוצרים הרצויים והכמויות שברצונך להזמין")
        subtitle.setObjectName("pageSubtitle")
        subtitle.setAlignment(Qt.AlignCenter)

        header_layout.addWidget(title)
        header_layout.addWidget(subtitle)
        main_layout.addWidget(header_frame)

        # אזור המוצרים עם גלילה
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setObjectName("productsScrollArea")

        self.products_container = QWidget()
        self.products_container.setObjectName("productsContainer")
        self.products_layout = QVBoxLayout(self.products_container)
        self.products_layout.setContentsMargins(0, 0, 0, 0)
        self.products_layout.setSpacing(12)

        scroll.setWidget(self.products_container)
        main_layout.addWidget(scroll, 1)

        # תקציר הזמנה (קומפקטי)
        summary_frame = QFrame()
        summary_frame.setObjectName("summaryFrame")
        summary_layout = QVBoxLayout(summary_frame)
        summary_layout.setContentsMargins(12, 8, 12, 8)  # היה 20,16,20,16
        summary_layout.setSpacing(4)                     # היה 8
        summary_frame.setMaximumHeight(120)              # מגבלה לגובה התקציר

        summary_title = QLabel("תקציר הזמנה")
        summary_title.setObjectName("summaryTitle")

        self.summary_label = QLabel("סה״כ פריטים: 0 | סה״כ לתשלום: 0.00 ₪")
        self.summary_label.setObjectName("summaryMain")
        self.summary_label.setAlignment(Qt.AlignRight)

        self.detailed_summary = QLabel("")
        self.detailed_summary.setObjectName("summaryDetails")
        self.detailed_summary.setAlignment(Qt.AlignRight)
        self.detailed_summary.setWordWrap(True)
        self.detailed_summary.setVisible(False)          # מצמצם גובה כברירת מחדל

        summary_layout.addWidget(summary_title)
        summary_layout.addWidget(self.summary_label)
        summary_layout.addWidget(self.detailed_summary)
        main_layout.addWidget(summary_frame)

        # כפתורי פעולה
        buttons_frame = QFrame()
        buttons_layout = QHBoxLayout(buttons_frame)
        buttons_layout.setContentsMargins(0, 0, 0, 0)
        buttons_layout.setSpacing(12)

        buttons_layout.addStretch()

        self.btn_cancel = QPushButton("ביטול")
        self.btn_cancel.setObjectName("cancelBtn")
        self.btn_cancel.clicked.connect(self.canceled.emit)

        self.btn_submit = QPushButton("בצע הזמנה")
        self.btn_submit.setObjectName("submitBtn")
        self.btn_submit.clicked.connect(self._submit_order)

        buttons_layout.addWidget(self.btn_cancel)
        buttons_layout.addWidget(self.btn_submit)
        main_layout.addWidget(buttons_frame)


    def _setup_styles(self):
        """עיצוב מודרני ונקי"""
        self.setStyleSheet("""
            /* רקע כללי */
            OrderCreatePage {
                background: linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%);
            }

            /* כותרת */
            QFrame#headerFrame {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #ffffff, stop:1 #f8fafc);
                border: 1px solid #e2e8f0;
                border-radius: 16px;
                margin-bottom: 8px;
            }

            QPushButton#linkBtn {
                border: none; background: transparent;
                font-size: 11px; color: #2563eb; padding: 0; margin: 0;
            }
            QPushButton#linkBtn:hover { text-decoration: underline; }

                                    
            QLabel#pageTitle {
                font-size: 28px;
                font-weight: 700;
                color: #1e293b;
                margin: 0;
                padding: 0;
            }

            QLabel#pageSubtitle {
                font-size: 14px;
                color: #64748b;
                margin: 0;
                padding: 0;
            }

            /* אזור גלילה */
            QScrollArea#productsScrollArea {
                border: none;
                background: transparent;
            }

            QWidget#productsContainer {
                background: transparent;
            }

            /* כרטיסי מוצרים */
            QWidget[objectName="ProductCard"] {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #ffffff, stop:1 #f8fafc);
                border: 2px solid #e2e8f0;
                border-radius: 16px;
                margin: 2px;
                padding: 0;
            }

            QWidget[objectName="ProductCard"]:hover {
                border-color: #3b82f6;
                box-shadow: 0 4px 12px rgba(59, 130, 246, 0.15);
            }

            /* תמונות מוצרים */
            QLabel[objectName="productImage"] {
                border: 1px solid #e2e8f0;
                border-radius: 12px;
                background: #f8fafc;
            }

            /* שמות מוצרים */
            QLabel[objectName="productName"] {
                font-size: 15px;
                font-weight: 700;
                color: #1e293b;
                margin: 0;
                padding: 2px 0;
            }

            QLabel[objectName="productPrice"] {
                font-size: 14px;
                font-weight: 600;
                color: #3b82f6;
                margin: 0;
                padding: 2px 0;
            }

            QLabel[objectName="productDetails"] {
                font-size: 11px;
                color: #64748b;
                margin: 0;
                padding: 2px 0;
            }

            /* צ'קבוקסים */
            QCheckBox {
                font-size: 14px;
                font-weight: 600;
                color: #374151;
                spacing: 8px;
                padding: 4px;
            }

            QCheckBox::indicator {
                width: 20px;
                height: 20px;
                border: 2px solid #d1d5db;
                border-radius: 6px;
                background: #ffffff;
            }

            QCheckBox::indicator:hover {
                border-color: #3b82f6;
                background: #eff6ff;
            }

            QCheckBox::indicator:checked {
                background: #3b82f6;
                border-color: #3b82f6;
                image: url(data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTIiIGhlaWdodD0iOSIgdmlld0JveD0iMCAwIDEyIDkiIGZpbGw9Im5vbmUiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+CjxwYXRoIGQ9Ik0xIDQuNUw0LjUgOEwxMSAxIiBzdHJva2U9IndoaXRlIiBzdHJva2Utd2lkdGg9IjIiIHN0cm9rZS1saW5lY2FwPSJyb3VuZCIgc3Ryb2tlLWxpbmVqb2luPSJyb3VuZCIvPgo8L3N2Zz4K);
            }

            /* שדות כמות */
            QLineEdit#qtyInput {
                background: #ffffff;
                border: 2px solid #e2e8f0;
                border-radius: 8px;
                padding: 6px 8px;
                font-size: 14px;
                font-weight: 600;
                color: #1e293b;
            }

            QLineEdit#qtyInput:read-only {
                background: #f1f5f9;
                color: #94a3b8;
                border-color: #e2e8f0;
            }

            QLineEdit#qtyInput:focus {
                border-color: #3b82f6;
                background: #eff6ff;
                outline: none;
            }

            /* תקציר */
            QFrame#summaryFrame {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #ffffff, stop:1 #f8fafc);
                border: 2px solid #e2e8f0;
                border-radius: 12px;
                margin: 4px 0;
            }

            QLabel#summaryTitle {
                font-size: 12px;
                font-weight: 700;
                color: #1e293b;
                margin: 0;
                padding: 0 0 4px 0;
            }

            QLabel#summaryMain {
                font-size: 13px;
                font-weight: 600;
                color: #1e293b;
                margin: 0;
                padding: 2px 0;
            }

            QLabel#summaryDetails {
                font-size: 11px;
                color: #64748b;
                margin: 0;
                padding: 2px 0;
                line-height: 1.2;
            }

            /* כפתורים */
            QPushButton#submitBtn {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #4f46e5, stop:1 #3b82f6);
                color: white;
                border: none;
                border-radius: 12px;
                padding: 14px 28px;
                font-weight: 700;
                font-size: 15px;
                min-width: 140px;
            }

            QPushButton#submitBtn:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #4338ca, stop:1 #2563eb);
                transform: translateY(-1px);
            }

            QPushButton#submitBtn:pressed {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #3730a3, stop:1 #1d4ed8);
                transform: translateY(0px);
            }

            QPushButton#submitBtn:disabled {
                background: #9ca3af;
                color: #ffffff;
            }

            QPushButton#cancelBtn {
                background: #ffffff;
                color: #64748b;
                border: 2px solid #e2e8f0;
                border-radius: 12px;
                padding: 14px 28px;
                font-weight: 600;
                font-size: 15px;
                min-width: 140px;
            }

            QPushButton#cancelBtn:hover {
                background: #f8fafc;
                border-color: #cbd5e1;
                color: #475569;
                transform: translateY(-1px);
            }

            QPushButton#cancelBtn:pressed {
                background: #f1f5f9;
                transform: translateY(0px);
            }
        
                           
             /* תגיות מצב */
            QLabel#oosBadge {
                padding: 2px 10px;
                border-radius: 999px;
                font-size: 11px;
                font-weight: 800;
                color: #ffffff;
                background: #ef4444; /* אדום */
                margin-bottom: 4px;
            }

            QLabel#mutedBadge {
                padding: 2px 10px;
                border-radius: 999px;
                font-size: 11px;
                font-weight: 800;
                color: #ffffff;
                background: #94a3b8; /* אפור */
                margin-bottom: 4px;
            }

            /* כרטיס של פריט אזל – מעט דהוי */
            QWidget[objectName="ProductCard"][outOfStock="true"] {
                opacity: 0.75;
                border-color: #fecaca; /* טיפה אדמדם */
            }

        """)

    def _load_products(self):
        try:
            self.products = svc.products_by_supplier(self.supplier_id)
            if not self.products:
                QMessageBox.information(self, "מידע", "לא נמצאו מוצרים עבור ספק זה")
                self.canceled.emit()
                return
        except Exception as e:
            QMessageBox.critical(self, "שגיאה", f"שגיאה בטעינת מוצרים: {e}")
            self.canceled.emit()
            return

        for p in self.products:
            self._add_product_card(p)

    def _add_product_card(self, product):
        """יצירת כרטיסי מוצרים מעוצבים"""
        stock = product.get("stock", 0)
        price = product.get("price", 0)
        
        out_of_stock = (stock <= 0)
        price_missing = (price <= 0)
            
        min_qty = max(1, product.get("min_qty", 1))
        product_id = product["id"]

        # כרטיס מוצר
        card = QWidget()
        card.setObjectName("ProductCard")
        main_layout = QVBoxLayout(card)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(12)

        # חלק עליון - תמונה ופרטים
        top_row = QHBoxLayout()
        top_row.setSpacing(12)

        # תמונה
        img_label = QLabel()
        img_label.setObjectName("productImage")
        img_label.setFixedSize(64, 64)
        img_label.setAlignment(Qt.AlignCenter)
        
        
        if product.get("image_url"):
            try:
                import requests
                data = requests.get(product["image_url"], timeout=5).content
                pixmap = QPixmap()
                pixmap.loadFromData(data)
                if not pixmap.isNull():
                    img_label.setPixmap(pixmap.scaled(80, 80, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            except:
                pass

        # פרטי מוצר
        info_layout = QVBoxLayout()
        info_layout.setSpacing(4)
        
        name_label = QLabel(product.get("name", "שם לא זמין"))
        name_label.setObjectName("productName")
        
        price_label = QLabel(f"{price:.2f} ₪")
        price_label.setObjectName("productPrice")
        
        details_label = QLabel(f"מלאי: {stock} יח׳ • מינימום: {min_qty} יח׳")
        details_label.setObjectName("productDetails")
        
        bad_reasons = []
        if out_of_stock:
            bad_reasons.append("אזל מהמלאי")
        if price_missing:
            bad_reasons.append("מחיר חסר")
        if bad_reasons:
            details_label.setText(f"מלאי: {stock} יח׳ • מינימום: {min_qty} יח׳ — " + " / ".join(bad_reasons))
        

        info_layout.addWidget(name_label)
        info_layout.addWidget(price_label)
        info_layout.addWidget(details_label)
        info_layout.addStretch()

        top_row.addWidget(img_label)
        top_row.addLayout(info_layout, 1)
        
        # תגיות מצב עליונות (אם צריך)
        if out_of_stock:
            oos_badge = QLabel("אזל מהמלאי")
            oos_badge.setObjectName("oosBadge")
            info_layout.addWidget(oos_badge)

        if price_missing:
            missing_badge = QLabel("מחיר חסר")
            missing_badge.setObjectName("mutedBadge")
            info_layout.addWidget(missing_badge)

        # חלק תחתון - בחירה וכמות
        bottom_row = QHBoxLayout()
        bottom_row.setSpacing(16)
        
        checkbox = QCheckBox("הוסף להזמנה")
        qty_input = SimpleQuantityInput(minimum=min_qty, maximum=stock, value=min_qty)
        qty_input.setEnabledEditing(True)
        
        if out_of_stock or price_missing:
            checkbox.setEnabled(False)
            qty_input.setEnabledEditing(False)
            checkbox.setToolTip("לא ניתן להזמין את הפריט כרגע")

        bottom_row.addWidget(checkbox)
        bottom_row.addStretch()
        bottom_row.addWidget(qty_input)

        main_layout.addLayout(top_row)
        main_layout.addLayout(bottom_row)

        # שמירת הנתונים
        self.product_widgets[product_id] = {
            'checkbox': checkbox,
            'qty_input': qty_input,
            'product': product,
            'min_qty': min_qty,
            'stock': stock,
            'card': card,
        }

        # חיבור אירועים
        def on_checkbox_changed(state):
            is_selected = (state == Qt.Checked)
            qty_input.setEnabledEditing(is_selected, ensure_min=min_qty)
            self._update_summary()

        def on_qty_changed(_):
            if checkbox.isChecked():
                self._update_summary()

        checkbox.stateChanged.connect(on_checkbox_changed)
        qty_input.valueChanged.connect(on_qty_changed)

        self.products_layout.addWidget(card)

    def _update_summary(self):
        """עדכון תקציר ההזמנה"""
        total_qty = 0
        total_price = 0.0
        details = []
        
        for pid, w in self.product_widgets.items():
            if w['checkbox'].isChecked():
                q = w['qty_input'].value()
                if q is None:
                    continue
                    
                price = w['product'].get('price', 0)
                item_total = q * price
                total_qty += q
                total_price += item_total
                
                product_name = w['product']['name']
                details.append(f"{product_name} — {q} יח׳ × {price:.2f} ₪ = {item_total:.2f} ₪")
        
        self.summary_label.setText(f"סה״כ פריטים: {total_qty} | סה״כ לתשלום: {total_price:.2f} ₪")
        
        if details:
            self.detailed_summary.setText("<br/>".join(details))
        else:
            self.detailed_summary.setText("לא נבחרו מוצרים")

    def _submit_order(self):
        """שליחת ההזמנה"""
        items = []
        
        for pid, w in self.product_widgets.items():
            if not w['checkbox'].isChecked():
                continue
                
            qty = w['qty_input'].value()
            name = w['product'].get('name', f"מוצר {pid}")
            min_qty = w['min_qty']
            stock = w['stock']
            
            # בדיקות תקינות
            if qty is None or qty <= 0:
                QMessageBox.warning(self, "שגיאה", f"אנא הזן כמות חוקית עבור '{name}'.")
                return
                
            if qty < min_qty:
                QMessageBox.warning(self, "שגיאה", 
                    f"לא ניתן לבצע הזמנה עבור '{name}' בכמות {qty}.\nמינימום הזמנה הוא {min_qty} יח׳.")
                return
                
            if qty > stock:
                QMessageBox.warning(self, "שגיאה",
                    f"הכמות המבוקשת עבור '{name}' גבוהה מהמלאי ({stock}).")
                return
                
            items.append({"product_id": pid, "quantity": qty})

        if not items:
            QMessageBox.warning(self, "שגיאה", "אנא בחר לפחות מוצר אחד להזמנה")
            return

        # אישור סופי
        total_items = sum(i["quantity"] for i in items)
        total_cost = sum(
            w['qty_input'].value() * w['product'].get('price', 0) 
            for w in self.product_widgets.values() 
            if w['checkbox'].isChecked()
        )
        
        reply = QMessageBox.question(
            self, "אישור הזמנה",
            f"האם אתה בטוח שברצונך להזמין {total_items} פריטים\nבסכום של {total_cost:.2f} ₪?",
            QMessageBox.Yes | QMessageBox.No, 
            QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            return

        # שליחת ההזמנה
        try:
            self.btn_submit.setEnabled(False)
            self.btn_submit.setText("שולח...")
            
            svc.create_order(self.owner_id, self.supplier_id, items)
            
            QMessageBox.information(self, "הצלחה", "ההזמנה נשלחה בהצלחה!")
            self.submitted.emit()
            
        except Exception as e:
            QMessageBox.critical(self, "שגיאה", f"נכשל ביצוע ההזמנה: {e}")
            self.btn_submit.setEnabled(True)
            self.btn_submit.setText("בצע הזמנה")