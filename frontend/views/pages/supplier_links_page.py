# frontend/views/pages/supplier_links_page.py
from PySide6.QtCore import Qt, Slot, QAbstractTableModel, QModelIndex
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTabWidget, QTableView,
    QPushButton, QLabel, QMessageBox, QApplication, QAbstractItemView, QFrame, QScrollArea, QCheckBox
)

from services.links_service import (
    get_active_links as _get_active_links,
    get_pending_links as _get_pending_links,
    approve_link as _approve_link,
    reject_link as _reject_link,
)

import os
DEBUG = os.getenv("APP_DEBUG", "0") == "1"

_HEADERS = ["בעלי חנות", "איש קשר", "טלפון"]


class _LinkTableModel(QAbstractTableModel):
    def __init__(self, rows=None, parent=None):
        super().__init__(parent)
        self._rows = rows or []

    def setRows(self, rows):
        self.beginResetModel()
        self._rows = rows or []
        self.endResetModel()

    def rowCount(self, parent=QModelIndex()):
        return len(self._rows)

    def columnCount(self, parent=QModelIndex()):
        return len(_HEADERS)

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            return _HEADERS[section]
        return super().headerData(section, orientation, role)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None
        row = self._rows[index.row()]
        owner = row.get("owner", {})
        cols = (
            owner.get("company_name") or "-",
            owner.get("contact_name") or "-",
            owner.get("phone") or "-",
        )
        if role in (Qt.DisplayRole, Qt.EditRole):
            return cols[index.column()]
        return None

    def ownerIdAt(self, r: int) -> int | None:
        try:
            return int(self._rows[r]["owner"]["id"])
        except Exception:
            return None


class SupplierLinksPage(QWidget):
    def __init__(self, supplier_id: int, parent=None):
        super().__init__(parent)
        self.supplier_id = supplier_id
        self.setLayoutDirection(Qt.RightToLeft)
        self._active_data = []  # לשמירת נתוני החיבורים הפעילים
        self._pending_data = []  # לשמירת נתוני החיבורים הממתינים
        self._pending_checkboxes = []  # לשמירת ה-checkboxes של הכרטיסיות הממתינות
        self._build_ui()
        self._setup_styles()
        self.refresh()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(16)

        # כותרת מודרנית כמו בעמודים אחרים
        title = QLabel("חיבורים עם בעלי חנויות")
        title.setObjectName("linksTitle")
        root.addWidget(title)

        # טאבים
        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        self.tabs.setTabPosition(QTabWidget.North)
        self.tabs.setObjectName("modernTabs")
        root.addWidget(self.tabs, 1)

        # לשונית: חיבורים פעילים - עם כרטיסיות
        tab_active = QWidget()
        layA = QVBoxLayout(tab_active)
        layA.setContentsMargins(16, 12, 16, 16)
        
        # אזור גלילה לכרטיסיות
        self.scroll_active = QScrollArea()
        self.scroll_active.setWidgetResizable(True)
        self.scroll_active.setFrameShape(QFrame.NoFrame)
        self.scroll_active.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scroll_active.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        self.cards_widget_active = QWidget()
        self.cards_layout_active = QVBoxLayout(self.cards_widget_active)
        self.cards_layout_active.setContentsMargins(0, 0, 0, 0)
        self.cards_layout_active.setSpacing(8)
        
        self.scroll_active.setWidget(self.cards_widget_active)
        layA.addWidget(self.scroll_active)

        self.lbl_active_empty = QLabel("אין חיבורים פעילים")
        self.lbl_active_empty.setAlignment(Qt.AlignCenter)
        self.lbl_active_empty.setStyleSheet("color:#6b7280; padding:32px; font-size:16px;")
        layA.addWidget(self.lbl_active_empty)

        self.tabs.addTab(tab_active, "חיבורים פעילים")

        # לשונית: בקשות ממתינות - עם כרטיסיות
        tab_pending = QWidget()
        layP = QVBoxLayout(tab_pending)
        layP.setContentsMargins(16, 12, 16, 16)
        
        # אזור גלילה לכרטיסיות ממתינות
        self.scroll_pending = QScrollArea()
        self.scroll_pending.setWidgetResizable(True)
        self.scroll_pending.setFrameShape(QFrame.NoFrame)
        self.scroll_pending.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scroll_pending.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        self.cards_widget_pending = QWidget()
        self.cards_layout_pending = QVBoxLayout(self.cards_widget_pending)
        self.cards_layout_pending.setContentsMargins(0, 0, 0, 0)
        self.cards_layout_pending.setSpacing(8)
        
        self.scroll_pending.setWidget(self.cards_widget_pending)
        layP.addWidget(self.scroll_pending)

        self.lbl_pending_empty = QLabel("אין חיבורים ממתינים")
        self.lbl_pending_empty.setAlignment(Qt.AlignCenter)
        self.lbl_pending_empty.setStyleSheet("color:#6b7280; padding:32px; font-size:16px;")
        layP.addWidget(self.lbl_pending_empty)

        # כפתורים - יוסתרו כשאין בקשות ממתינות
        self.buttons_container = QFrame()
        btns = QHBoxLayout(self.buttons_container)
        self.btn_reject = QPushButton("דחה")
        self.btn_reject.setObjectName("rejectBtn")
        self.btn_approve = QPushButton("אשר")
        self.btn_approve.setObjectName("approveBtn")
        self.btn_refresh = QPushButton("רענן")
        self.btn_refresh.setObjectName("refreshBtn")
        btns.addStretch(1)
        btns.addWidget(self.btn_reject)
        btns.addWidget(self.btn_approve)
        btns.addWidget(self.btn_refresh)
        layP.addWidget(self.buttons_container)

        self.tabs.addTab(tab_pending, "בקשות ממתינות")

        # חיבורים
        self.btn_refresh.clicked.connect(self.refresh)
        self.btn_approve.clicked.connect(self.on_approve_selected)
        self.btn_reject.clicked.connect(self.on_reject_selected)

    def _create_active_card(self, owner_data):
        """יוצר כרטיסיה עבור חיבור פעיל"""
        card = QWidget()
        card.setObjectName("linkCard")
        card.setMinimumHeight(80)
        main_layout = QHBoxLayout(card)
        main_layout.setContentsMargins(20, 16, 20, 16)
        main_layout.setSpacing(16)
        
        # נקודה ירוקה בצד ימין
        status_dot = QLabel("●")
        status_dot.setStyleSheet("color: #10b981; font-size: 16px;")
        status_dot.setFixedWidth(16)
        main_layout.addWidget(status_dot, 0, Qt.AlignCenter)
        
        # תוכן ראשי - חלק שמאלי
        main_info_layout = QVBoxLayout()
        main_info_layout.setSpacing(2)
        
        # שם החברה
        company_name = owner_data.get("company_name") or "לא צוין"
        company_label = QLabel(company_name)
        company_label.setStyleSheet("font-size: 16px; font-weight: 700; color: #111827;")
        if any(ord(ch) < 128 and ch.isalpha() for ch in company_name):
            company_label.setAlignment(Qt.AlignRight)
        main_info_layout.addWidget(company_label)
        
        # שורה עם בעל החנות וטלפון
        details_layout = QHBoxLayout()
        details_layout.setSpacing(20)
        
        # שם בעל החנות
        contact_name = owner_data.get("contact_name") or "לא צוין"
        contact_label = QLabel(f"בעל החנות: {contact_name}")
        contact_label.setStyleSheet("font-size: 13px; color: #374151;")
        details_layout.addWidget(contact_label)
        
        # טלפון
        phone = owner_data.get("phone") or "אין טלפון"
        phone_label = QLabel(f"טלפון: {phone}")
        phone_label.setStyleSheet("font-size: 13px; color: #6b7280;")
        details_layout.addWidget(phone_label)
        
        details_layout.addStretch()
        
        main_info_layout.addLayout(details_layout)
        main_layout.addLayout(main_info_layout, 1)
        
        # תאריך החיבור בצד השמאלי
        created_at = owner_data.get("created_at") or owner_data.get("approved_at")
        if created_at:
            if isinstance(created_at, str):
                date_text = created_at.split('T')[0] if 'T' in created_at else created_at
                time_text = created_at.split('T')[1][:5] if 'T' in created_at and len(created_at.split('T')) > 1 else ""
            else:
                try:
                    date_text = created_at.strftime("%d/%m/%Y")
                    time_text = created_at.strftime("%H:%M")
                except:
                    date_text, time_text = str(created_at), ""
            
            date_container = QVBoxLayout(); date_container.setSpacing(1)
            date_title = QLabel("מחובר מאז:"); date_title.setStyleSheet("font-size: 9px; color: #9ca3af; font-weight: 600;"); date_title.setAlignment(Qt.AlignCenter)
            date_value = QLabel(date_text);      date_value.setStyleSheet("font-size: 11px; color: #6b7280; font-weight: 500;"); date_value.setAlignment(Qt.AlignCenter)
            date_container.addWidget(date_title); date_container.addWidget(date_value)
            if time_text:
                time_value = QLabel(time_text); time_value.setStyleSheet("font-size: 10px; color: #9ca3af;"); time_value.setAlignment(Qt.AlignCenter)
                date_container.addWidget(time_value)
            date_widget = QWidget(); date_widget.setLayout(date_container); date_widget.setFixedWidth(90)
            main_layout.addWidget(date_widget, 0, Qt.AlignCenter)
        
        return card

    def _create_pending_card(self, owner_data, link_data):
        """יוצר כרטיסיה עבור חיבור ממתין עם checkbox לבחירה"""
        card = QWidget()
        card.setObjectName("pendingCard")
        card.setMinimumHeight(80)
        main_layout = QHBoxLayout(card)
        main_layout.setContentsMargins(20, 16, 20, 16)
        main_layout.setSpacing(16)
        
        # checkbox לבחירה בצד ימין
        checkbox = QCheckBox()
        checkbox.setStyleSheet("""
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border-radius: 4px;
                border: 2px solid #d1d5db;
                background: #fff;
            }
            QCheckBox::indicator:checked {
                background: #10b981;
                border-color: #10b981;
            }
            QCheckBox::indicator:hover {
                border-color: #9ca3af;
            }
        """)
        checkbox.setProperty("owner_id", owner_data.get("id"))
        self._pending_checkboxes.append(checkbox)
        main_layout.addWidget(checkbox, 0, Qt.AlignCenter)
        
        # נקודה כתומה בצד ימין (ממתין)
        status_dot = QLabel("●")
        status_dot.setStyleSheet("color: #f59e0b; font-size: 16px;")
        status_dot.setFixedWidth(16)
        main_layout.addWidget(status_dot, 0, Qt.AlignCenter)
        
        # תוכן ראשי
        main_info_layout = QVBoxLayout()
        main_info_layout.setSpacing(2)
        
        # שם החברה
        company_name = owner_data.get("company_name") or "לא צוין"
        company_label = QLabel(company_name)
        company_label.setStyleSheet("font-size: 16px; font-weight: 700; color: #111827;")
        if any(ord(ch) < 128 and ch.isalpha() for ch in company_name):
            company_label.setAlignment(Qt.AlignRight)
        main_info_layout.addWidget(company_label)
        
        # שורה עם בעל החנות וטלפון
        details_layout = QHBoxLayout()
        details_layout.setSpacing(20)
        
        # שם בעל החנות
        contact_name = owner_data.get("contact_name") or "לא צוין"
        contact_label = QLabel(f"בעל החנות: {contact_name}")
        contact_label.setStyleSheet("font-size: 13px; color: #374151;")
        details_layout.addWidget(contact_label)
        
        # טלפון
        phone = owner_data.get("phone") or "אין טלפון"
        phone_label = QLabel(f"טלפון: {phone}")
        phone_label.setStyleSheet("font-size: 13px; color: #6b7280;")
        details_layout.addWidget(phone_label)
        
        details_layout.addStretch()
        
        main_info_layout.addLayout(details_layout)
        main_layout.addLayout(main_info_layout, 1)
        
        # תאריך הבקשה בצד השמאלי
        requested_at = owner_data.get("requested_at") or owner_data.get("created_at")
        if requested_at:
            if isinstance(requested_at, str):
                date_text = requested_at.split('T')[0] if 'T' in requested_at else requested_at
                time_text = requested_at.split('T')[1][:5] if 'T' in requested_at and len(requested_at.split('T')) > 1 else ""
            else:
                try:
                    date_text = requested_at.strftime("%d/%m/%Y")
                    time_text = requested_at.strftime("%H:%M")
                except:
                    date_text, time_text = str(requested_at), ""
            
            date_container = QVBoxLayout(); date_container.setSpacing(1)
            date_title = QLabel("בקשה מתאריך:"); date_title.setStyleSheet("font-size: 9px; color: #9ca3af; font-weight: 600;"); date_title.setAlignment(Qt.AlignCenter)
            date_value = QLabel(date_text);      date_value.setStyleSheet("font-size: 11px; color: #6b7280; font-weight: 500;"); date_value.setAlignment(Qt.AlignCenter)
            date_container.addWidget(date_title); date_container.addWidget(date_value)
            if time_text:
                time_value = QLabel(time_text); time_value.setStyleSheet("font-size: 10px; color: #9ca3af;"); time_value.setAlignment(Qt.AlignCenter)
                date_container.addWidget(time_value)
            date_widget = QWidget(); date_widget.setLayout(date_container); date_widget.setFixedWidth(90)
            main_layout.addWidget(date_widget, 0, Qt.AlignCenter)
        
        return card

    def _update_active_cards(self, active_links):
        """מעדכן את הכרטיסיות של החיבורים הפעילים"""
        # ניקוי הכרטיסיות הקיימות
        while self.cards_layout_active.count():
            child = self.cards_layout_active.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        
        # הוספת כרטיסיות חדשות
        for link in active_links:
            owner = link.get("owner", {})
            card = self._create_active_card(owner)
            self.cards_layout_active.addWidget(card)
        
        # הוספת stretch בסוף
        self.cards_layout_active.addStretch()

    def _update_pending_cards(self, pending_links):
        """מעדכן את הכרטיסיות של החיבורים הממתינים"""
        # ניקוי הכרטיסיות הקיימות
        while self.cards_layout_pending.count():
            child = self.cards_layout_pending.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        
        # ניקוי רשימת ה-checkboxes
        self._pending_checkboxes.clear()
        
        # הוספת כרטיסיות חדשות
        for link in pending_links:
            owner = link.get("owner", {})
            card = self._create_pending_card(owner, link)
            self.cards_layout_pending.addWidget(card)
        
        # הוספת stretch בסוף
        self.cards_layout_pending.addStretch()

    def _update_empty_placeholders(self):
        """עדכון תצוגת הודעות ריקות וכפתורים"""
        has_active = len(self._active_data) > 0
        has_pending = len(self._pending_data) > 0
        
        # הצגה/הסתרה של תוכן פעיל
        self.scroll_active.setVisible(has_active)
        self.lbl_active_empty.setVisible(not has_active)
        
        # הצגה/הסתרה של תוכן ממתין
        self.scroll_pending.setVisible(has_pending)
        self.lbl_pending_empty.setVisible(not has_pending)
        
        # הצגה/הסתרה של כפתורים - רק כשיש בקשות ממתינות
        self.buttons_container.setVisible(has_pending)

    def _setup_styles(self):
        # עיצוב אחיד עם הדפים האחרים בגווני ירוק של הספק
        self.setStyleSheet("""
            SupplierLinksPage { 
                background: #fafafa; 
            }
            
            /* כותרת מודרנית כמו בדפים אחרים */
            QLabel#linksTitle {
                font-size: 24px;
                font-weight: 700;
                color: #065f46;
                margin-bottom: 8px;
                padding: 12px;
                background: #ecfdf5;
                border-radius: 8px;
            }

            /* עיצוב טאבים מודרני */
            QTabWidget#modernTabs::pane {
                border: none;
                background: #fff;
                margin-top: 0px;
            }

            QTabBar::tab {
                background: transparent;
                color: #6b7280;
                border: none;
                padding: 12px 24px;
                margin: 0 8px;
                min-width: 120px;
                font-weight: 500;
                font-size: 14px;
            }

            QTabBar::tab:selected {
                background: transparent;
                color: #10b981;
                font-weight: 600;
                border-bottom: 2px solid #10b981;
            }

            QTabBar::tab:hover:!selected {
                color: #374151;
            }

            /* עיצוב כפתורים בגווני ירוק */
            QPushButton#approveBtn {
                background: #10b981;
                color: #fff;
                border: 1px solid #059669;
                border-radius: 8px;
                padding: 8px 16px;
                font-weight: 600;
                min-width: 80px;
            }
            QPushButton#approveBtn:hover {
                background: #059669;
                border-color: #047857;
            }
            
            QPushButton#rejectBtn {
                background: #ef4444;
                color: #fff;
                border: 1px solid #dc2626;
                border-radius: 8px;
                padding: 8px 16px;
                font-weight: 600;
                min-width: 80px;
            }
            QPushButton#rejectBtn:hover {
                background: #dc2626;
                border-color: #b91c1c;
            }
            
            QPushButton#refreshBtn {
                background: #3b82f6;
                color: #fff;
                border: 1px solid #2563eb;
                border-radius: 8px;
                padding: 8px 16px;
                font-weight: 600;
                min-width: 80px;
            }
            QPushButton#refreshBtn:hover {
                background: #2563eb;
                border-color: #1d4ed8;
            }

            /* עיצוב כרטיסיות פעילות */
            QWidget[objectName="linkCard"] {
                background: #fff;
                border: 1px solid #e5e7eb;
                border-radius: 10px;
                margin-bottom: 4px;
                padding: 4px;
            }
            QWidget[objectName="linkCard"]:hover {
                border-color: #10b981;
                box-shadow: 0 4px 6px rgba(16, 185, 129, 0.1);
            }

            /* עיצוב כרטיסיות ממתינות */
            QWidget[objectName="pendingCard"] {
                background: #fff;
                border: 1px solid #f59e0b;
                border-radius: 10px;
                margin-bottom: 4px;
                padding: 4px;
            }
            QWidget[objectName="pendingCard"]:hover {
                border-color: #d97706;
                box-shadow: 0 4px 6px rgba(245, 158, 11, 0.15);
            }

            /* עיצוב אזור הגלילה */
            QScrollArea {
                border: none;
                background: transparent;
            }
        """)

    def _as_list(self, x):
        if isinstance(x, dict):
            for k in ("data", "results", "items", "links"):
                if isinstance(x.get(k), list):
                    return x[k]
            return []
        return x or []

    @Slot()
    def refresh(self):
        try:
            active = _get_active_links(self.supplier_id) or []
            pending = _get_pending_links(self.supplier_id) or []
            # בשלב הזה links_service כבר מנרמל כל פריט עם owner, אבל נשמור על הבנה:
            active = active if isinstance(active, list) else []
            pending = pending if isinstance(pending, list) else []
            
            # שמירת הנתונים עבור הכרטיסיות ועדכון
            self._active_data = active
            self._pending_data = pending
            self._update_active_cards(active)
            self._update_pending_cards(pending)
            
        except Exception as e:
            QMessageBox.warning(self, "שגיאה", str(e))
        self._update_empty_placeholders()

    @Slot()
    def on_approve_selected(self):
        selected_ids = []
        for checkbox in self._pending_checkboxes:
            if checkbox.isChecked():
                owner_id = checkbox.property("owner_id")
                if owner_id:
                    selected_ids.append(int(owner_id))
        
        if not selected_ids:
            QMessageBox.information(self, "הודעה", "אנא בחר לפחות חיבור אחד לאישור")
            return
            
        for oid in selected_ids:
            _approve_link(oid, self.supplier_id)
        self.refresh()

    @Slot()
    def on_reject_selected(self):
        selected_ids = []
        for checkbox in self._pending_checkboxes:
            if checkbox.isChecked():
                owner_id = checkbox.property("owner_id")
                if owner_id:
                    selected_ids.append(int(owner_id))
        
        if not selected_ids:
            QMessageBox.information(self, "הודעה", "אנא בחר לפחות חיבור אחד להחייה")
            return
            
        for oid in selected_ids:
            _reject_link(oid, self.supplier_id)
        self.refresh()