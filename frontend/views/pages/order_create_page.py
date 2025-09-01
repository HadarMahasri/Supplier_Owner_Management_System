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
        layout = QHBoxLayout(self); layout.setContentsMargins(0,0,0,0); layout.setSpacing(8)
        self.label = QLabel("כמות:"); self.label.setStyleSheet("font-size:13px;font-weight:600;color:#374151;min-width:35px;")
        self.line = QLineEdit(); self.line.setFixedHeight(32); self.line.setFixedWidth(90); self.line.setAlignment(Qt.AlignCenter)
        self.line.setPlaceholderText("0"); self.line.setObjectName("modernQtyInput")
        self.line.setValidator(QIntValidator(0, max(1_000_000_000, self.maximum_val)))
        self.line.textChanged.connect(self._emit_if_valid)
        layout.addWidget(self.label); layout.addWidget(self.line); layout.addStretch()
    def _emit_if_valid(self, _): v = self.value();  self.valueChanged.emit(v) if v is not None else None
    def setEnabledEditing(self, enabled: bool, ensure_min: Optional[int] = None):
        self.line.setReadOnly(not enabled)
        if enabled and ensure_min is not None and (self.value() or 0) < ensure_min:
            self.setValue(ensure_min)
    def setValue(self, v: int):
        try: v = int(v)
        except Exception: v = 0
        self.line.setText(str(v))
    def value(self) -> Optional[int]:
        txt = self.line.text().strip()
        if not txt: return 0
        try: return int(txt)
        except ValueError: return None

class OrderCreatePage(QWidget):
    canceled = Signal()        # חזרה אחורה
    submitted = Signal()       # אחרי הצלחה (למשל: רענון דפי הזמנות/ספקים)

    def __init__(self, owner_id: int, supplier_id: int, parent=None):
        super().__init__(parent)
        self.owner_id = owner_id
        self.supplier_id = supplier_id
        self.products = []
        self.product_widgets = {}

        self.setLayoutDirection(Qt.RightToLeft)
        layout = QVBoxLayout(self); layout.setContentsMargins(20,20,20,20); layout.setSpacing(16)

        title = QLabel("בחר מוצרים להזמנה", alignment=Qt.AlignCenter)
        title.setStyleSheet("font-size:24px;font-weight:bold;color:#1f2937;margin-bottom:10px;")
        layout.addWidget(title)

        scroll = QScrollArea(); scroll.setWidgetResizable(True); scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        self.products_container = QWidget()
        self.products_layout = QVBoxLayout(self.products_container); self.products_layout.setContentsMargins(0,0,0,0); self.products_layout.setSpacing(12)
        scroll.setWidget(self.products_container); layout.addWidget(scroll, 1)

        summary_frame = QFrame(objectName="summaryFrame")
        summary_layout = QVBoxLayout(summary_frame); summary_layout.setSpacing(8)
        self.summary_label = QLabel("סה״כ פריטים: 0 | סה״כ לתשלום: 0.00 ₪", objectName="summaryMain", alignment=Qt.AlignRight)
        self.detailed_summary = QLabel("", objectName="summaryDetails", alignment=Qt.AlignRight); self.detailed_summary.setWordWrap(True)
        summary_layout.addWidget(self.summary_label); summary_layout.addWidget(self.detailed_summary)
        layout.addWidget(summary_frame)

        btns = QHBoxLayout(); btns.addStretch()
        self.btn_cancel = QPushButton("ביטול", objectName="cancelBtn")
        self.btn_submit = QPushButton("בצע הזמנה", objectName="submitBtn")
        btns.addWidget(self.btn_cancel); btns.addWidget(self.btn_submit); layout.addLayout(btns)

        self.btn_cancel.clicked.connect(self.canceled.emit)
        self.btn_submit.clicked.connect(self._submit_order)

        self._setup_styles()
        self._load_products()

    def _setup_styles(self):
        # צבעים מותאמים ל-StoreOwnerHome: כחולים וכפתורי primary/secondary תואמים
        self.setStyleSheet("""
            QWidget { background:#fafafa; }  /* כמו דף הבית */

            QPushButton#submitBtn {
                background:#3b82f6;           /* primary כחול */
                color:white; border:1px solid #2563eb;
                border-radius:10px; padding:12px 24px;
                font-weight:600; font-size:14px; min-width:120px;
            }
            QPushButton#submitBtn:hover { background:#2563eb; }
            QPushButton#submitBtn:pressed { background:#1d4ed8; }

            QPushButton#cancelBtn {
                background:#fff; color:#374151; border:1px solid #d1d5db;
                border-radius:10px; padding:12px 24px; font-weight:500; font-size:14px; min-width:120px;
            }
            QPushButton#cancelBtn:hover { background:#f9fafb; border-color:#3b82f6; color:#3b82f6; }

            QWidget[objectName="ProductCard"] {
                background:#fff; border:2px solid #e5e7eb; border-radius:12px; padding:16px;
            }
            QWidget[objectName="ProductCard"]:hover { border-color:#cbd5e1; }

            QCheckBox { font-size:14px; font-weight:600; color:#374151; spacing:8px; }
            QCheckBox::indicator {
                width:18px; height:18px; border:2px solid #d1d5db; border-radius:4px; background:#fff;
            }
            QCheckBox::indicator:hover { border-color:#3b82f6; background:#eff6ff; }
            QCheckBox::indicator:checked { background:#3b82f6; border-color:#3b82f6; }

            QLineEdit#modernQtyInput {
                background:#fff; border:2px solid #e5e7eb; border-radius:6px;
                padding:4px 6px; font-size:14px; font-weight:600; color:#1f2937;
            }
            QLineEdit#modernQtyInput:read-only { background:#f9fafb; color:#9ca3af; }
            QLineEdit#modernQtyInput:focus { border-color:#2563eb; background:#eff6ff; }

            QFrame#summaryFrame { background:#fff; border:2px solid #e5e7eb; border-radius:10px; padding:12px; }
            QLabel#summaryMain { font-size:16px; font-weight:bold; color:#1f2937; }
            QLabel#summaryDetails { font-size:13px; color:#6b7280; }
        """)


    def _load_products(self):
        try:
            self.products = svc.products_by_supplier(self.supplier_id)
            if not self.products:
                QMessageBox.information(self, "מידע", "לא נמצאו מוצרים עבור ספק זה")
                self.canceled.emit(); return
        except Exception as e:
            QMessageBox.critical(self, "שגיאה", f"שגיאה בטעינת מוצרים: {e}")
            self.canceled.emit(); return

        for p in self.products:
            self._add_product_card(p)

    def _add_product_card(self, product):
        stock = product.get("stock", 0)
        price = product.get("price", 0)
        if stock <= 0 or price <= 0:
            return
        min_qty = max(1, product.get("min_qty", 1))
        product_id = product["id"]

        card = QWidget(objectName="ProductCard")
        main_layout = QVBoxLayout(card); main_layout.setSpacing(16)

        top_row = QHBoxLayout()
        img_label = QLabel(); img_label.setFixedSize(80, 80)
        img_label.setStyleSheet("border:1px solid #e5e7eb; border-radius:8px; background:#f9fafb;")
        if product.get("image_url"):
            try:
                import requests
                data = requests.get(product["image_url"], timeout=5).content
                pixmap = QPixmap(); pixmap.loadFromData(data)
                img_label.setPixmap(pixmap.scaled(80, 80, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            except:
                pass

        info_layout = QVBoxLayout()
        name_label = QLabel(product.get("name", "שם לא זמין"))
        name_label.setStyleSheet("font-size:18px; font-weight:bold; color:#1f2937;")
        price_label = QLabel(f"{price:.2f} ₪")
        price_label.setStyleSheet("font-size:16px; font-weight:bold; color:#3b82f6;")
        details_label = QLabel(f"מלאי: {stock} יח׳ • מינימום: {min_qty} יח׳"); details_label.setStyleSheet("font-size:12px; color:#6b7280;")
        info_layout.addWidget(name_label); info_layout.addWidget(price_label); info_layout.addWidget(details_label); info_layout.addStretch()
        top_row.addWidget(img_label); top_row.addLayout(info_layout, 1)

        bottom_row = QHBoxLayout()
        checkbox = QCheckBox("הוסף להזמנה")
        qty_input = SimpleQuantityInput(minimum=min_qty, maximum=stock, value=min_qty)
        qty_input.setEnabledEditing(True)
        bottom_row.addWidget(checkbox); bottom_row.addStretch(); bottom_row.addWidget(qty_input)

        main_layout.addLayout(top_row); main_layout.addLayout(bottom_row)

        self.product_widgets[product_id] = {
            'checkbox': checkbox, 'qty_input': qty_input, 'product': product,
            'min_qty': min_qty, 'stock': stock, 'card': card,
        }

        def on_checkbox_changed(state):
            is_selected = (state == Qt.Checked)
            qty_input.setEnabledEditing(is_selected, ensure_min=min_qty)
            self._update_summary()
        def on_qty_changed(_):
            if checkbox.isChecked(): self._update_summary()

        checkbox.stateChanged.connect(on_checkbox_changed)
        qty_input.valueChanged.connect(on_qty_changed)

        self.products_layout.addWidget(card)

    def _update_summary(self):
        total_qty = 0; total_price = 0.0; details = []
        for pid, w in self.product_widgets.items():
            if w['checkbox'].isChecked():
                q = w['qty_input'].value()
                if q is None: continue
                price = w['product'].get('price', 0)
                item_total = q * price
                total_qty += q; total_price += item_total
                details.append(f"{w['product']['name']} — {q} יח׳ × {price:.2f} ₪ = {item_total:.2f} ₪")
        self.summary_label.setText(f"סה״כ פריטים: {total_qty} | סה״כ לתשלום: {total_price:.2f} ₪")
        self.detailed_summary.setText("<br/>".join(details) if details else "לא נבחרו מוצרים")

    def _submit_order(self):
        items = []
        for pid, w in self.product_widgets.items():
            if not w['checkbox'].isChecked(): continue
            qty = w['qty_input'].value()
            name = w['product'].get('name', f"מוצר {pid}")
            min_qty = w['min_qty']; stock = w['stock']
            if qty is None or qty <= 0:
                QMessageBox.warning(self, "שגיאה", f"אנא הזן כמות חוקית עבור '{name}'."); return
            if qty < min_qty:
                QMessageBox.warning(self, "שגיאה", f"לא ניתן לבצע הזמנה עבור '{name}' בכמות {qty}. מינימום הזמנה הוא {min_qty} יח׳."); return
            if qty > stock:
                QMessageBox.warning(self, "שגיאה", f"הכמות המבוקשת עבור '{name}' גבוהה מהמלאי ({stock})."); return
            items.append({"product_id": pid, "quantity": qty})

        if not items:
            QMessageBox.warning(self, "שגיאה", "אנא בחר לפחות מוצר אחד להזמנה"); return

        total_items = sum(i["quantity"] for i in items)
        if QMessageBox.question(self, "אישור הזמנה",
                                f"האם אתה בטוח שברצונך להזמין {total_items} פריטים?",
                                QMessageBox.Yes | QMessageBox.No, QMessageBox.No) != QMessageBox.Yes:
            return
        try:
            self.btn_submit.setEnabled(False); self.btn_submit.setText("שולח...")
            svc.create_order(self.owner_id, self.supplier_id, items)
            QMessageBox.information(self, "הצלחה", "ההזמנה נשלחה בהצלחה!")
            self.submitted.emit()
        except Exception as e:
            QMessageBox.critical(self, "שגיאה", f"נכשל ביצוע ההזמנה: {e}")
            self.btn_submit.setEnabled(True); self.btn_submit.setText("בצע הזמנה")
