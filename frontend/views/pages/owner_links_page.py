# frontend/views/pages/owner_links_page.py
from PySide6.QtCore import Qt, Slot
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTabWidget, QLabel,
    QPushButton, QScrollArea, QFrame, QMessageBox
)

from services.owner_portal_service import (
    find_suppliers as _find_suppliers,
    get_active_by_owner as _get_active,
    get_pending_by_owner as _get_pending,
    request_link as _request_link,
)


class OwnerLinksPage(QWidget):
    def __init__(self, owner_id: int, parent=None, open_order_inline=None):
        super().__init__(parent)
        self.owner_id = owner_id
        self.open_order_inline = open_order_inline  # ← תוספת קטנה: תמיכה בחלון יחיד
        self.setLayoutDirection(Qt.RightToLeft)
        self._build_ui()
        self._setup_styles()
        self.refresh()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        hdr = QHBoxLayout()
        hdr.setContentsMargins(16, 12, 16, 8)
        title = QLabel("החיבורים שלי")
        title.setStyleSheet("font-size:18px; font-weight:700; color:#111827;")
        hdr.addWidget(title, 0, Qt.AlignRight)
        hdr.addStretch(1)
        root.addLayout(hdr)

        self.tabs = QTabWidget()
        self.tabs.setObjectName("modernTabs")
        self.tabs.setDocumentMode(True)
        self.tabs.setTabPosition(QTabWidget.North)
        root.addWidget(self.tabs, 1)

        # --- Tab: פעילים (ראשון) ---
        self.tab_active = QWidget()
        la = QVBoxLayout(self.tab_active)
        la.setContentsMargins(16, 12, 16, 16)
        self._active_scroll, self._active_list = self._make_scroll()
        la.addWidget(self._active_scroll)
        self.lbl_active_empty = QLabel("אין חיבורים פעילים")
        self.lbl_active_empty.setAlignment(Qt.AlignCenter)
        self.lbl_active_empty.setStyleSheet("color:#6b7280; padding:22px;")
        la.addWidget(self.lbl_active_empty)
        self.tabs.addTab(self.tab_active, "חיבורים פעילים")

        # --- Tab: ממתינים (שני) ---
        self.tab_pending = QWidget()
        lp = QVBoxLayout(self.tab_pending)
        lp.setContentsMargins(16, 12, 16, 16)
        self._pending_scroll, self._pending_list = self._make_scroll()
        lp.addWidget(self._pending_scroll)
        self.lbl_pending_empty = QLabel("אין חיבורים ממתינים")
        self.lbl_pending_empty.setAlignment(Qt.AlignCenter)
        self.lbl_pending_empty.setStyleSheet("color:#6b7280; padding:22px;")
        lp.addWidget(self.lbl_pending_empty)
        self.tabs.addTab(self.tab_pending, "בקשות ממתינות")

        # --- Tab: מצא ספקים (שלישי) ---
        self.tab_find = QWidget()
        lf = QVBoxLayout(self.tab_find)
        lf.setContentsMargins(16, 12, 16, 16)
        self._find_scroll, self._find_list = self._make_scroll()
        lf.addWidget(self._find_scroll)
        self.lbl_find_empty = QLabel("לא נמצאו ספקים זמינים באזור שלך.")
        self.lbl_find_empty.setAlignment(Qt.AlignCenter)
        self.lbl_find_empty.setStyleSheet("color:#6b7280; padding:22px;")
        lf.addWidget(self.lbl_find_empty)
        self.tabs.addTab(self.tab_find, "מצא ספקים")

    def _make_scroll(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        inner = QWidget()
        lay = QVBoxLayout(inner)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(8)
        scroll.setWidget(inner)
        return scroll, lay

    def _setup_styles(self):
        self.setStyleSheet("""
            OwnerLinksPage { background:#fafafa; }
            QTabWidget#modernTabs::pane { border:none; background:#fff; margin-top:0; }
            QTabBar::tab {
                background:transparent; color:#6b7280; border:none;
                padding:12px 24px; margin:0 8px; min-width:120px; font-weight:500; font-size:14px;
            }
            QTabBar::tab:selected { color:#3b82f6; font-weight:600; border-bottom:2px solid #3b82f6; }
            QTabBar::tab:hover:!selected { color:#374151; }

            QPushButton {
                background:#10b981; color:#fff; border:1px solid #059669; border-radius:6px;
                padding:8px 16px; font-weight:600; min-width:100px;
            }
            QPushButton:hover { background:#059669; border-color:#047857; }
            QPushButton:pressed { background:#047857; border-color:#065f46; }

            QWidget[objectName="card"] {
                background:#fff; border:1px solid #e5e7eb; border-radius:8px; margin-bottom:4px;
            }
            QWidget[objectName="card"]:hover { border-color:#d1d5db; box-shadow:0 1px 3px rgba(0,0,0,.1); }

            QWidget[objectName="pendingCard"] {
                background:#fff; border:1px solid #f59e0b; border-radius:8px; margin-bottom:4px;
            }
            QWidget[objectName="pendingCard"]:hover { border-color:#d97706; box-shadow:0 1px 3px rgba(245,158,11,.2); }
        """)

    # --- UI cards ---
    def _add_supplier_card(self, parent_layout, user_dict):
        card = QWidget()
        card.setObjectName("card")
        card.setMinimumHeight(80)
        main_layout = QHBoxLayout(card)
        main_layout.setContentsMargins(20, 16, 20, 16)
        main_layout.setSpacing(16)

        # תוכן ראשי - פרטי הספק בצד ימין
        main_info_layout = QVBoxLayout()
        main_info_layout.setSpacing(2)

        # שם החברה
        company_name = user_dict.get("company_name") or "לא צוין"
        company_label = QLabel(company_name)
        company_label.setStyleSheet("font-size: 16px; font-weight: 700; color: #111827;")
        if any(ord(ch) < 128 and ch.isalpha() for ch in company_name):
            company_label.setAlignment(Qt.AlignRight)
        main_info_layout.addWidget(company_label)

        # שורה עם שם הספק וטלפון
        details_layout = QHBoxLayout()
        details_layout.setSpacing(20)

        supplier_name = user_dict.get("contact_name") or user_dict.get("name") or "לא צוין"
        supplier_label = QLabel(f"ספק: {supplier_name}")
        supplier_label.setStyleSheet("font-size: 13px; color: #374151;")
        details_layout.addWidget(supplier_label)

        phone = user_dict.get("phone") or "אין טלפון"
        phone_label = QLabel(f"טלפון: {phone}")
        phone_label.setStyleSheet("font-size: 13px; color: #6b7280;")
        details_layout.addWidget(phone_label)

        details_layout.addStretch()
        main_info_layout.addLayout(details_layout)
        main_layout.addLayout(main_info_layout, 1)

        # כפתור שלח בקשה בצד שמאל
        btn = QPushButton("שלח בקשה")
        btn.clicked.connect(lambda: self._send_request(user_dict.get("id")))
        main_layout.addWidget(btn, 0, Qt.AlignCenter)

        parent_layout.addWidget(card)

    def _add_pending_card(self, parent_layout, link):
        sup = link.get("owner", {})  # מבנה הקישור: owner = פרטי הספק
        card = QWidget()
        card.setObjectName("pendingCard")
        card.setMinimumHeight(80)
        main_layout = QHBoxLayout(card)
        main_layout.setContentsMargins(20, 16, 20, 16)
        main_layout.setSpacing(16)

        status_dot = QLabel("●")
        status_dot.setStyleSheet("color: #f59e0b; font-size: 16px;")
        status_dot.setFixedWidth(16)
        main_layout.addWidget(status_dot, 0, Qt.AlignCenter)

        main_info_layout = QVBoxLayout()
        main_info_layout.setSpacing(2)

        company_name = sup.get("company_name") or "לא צוין"
        company_label = QLabel(company_name)
        company_label.setStyleSheet("font-size: 16px; font-weight: 700; color: #111827;")
        if any(ord(ch) < 128 and ch.isalpha() for ch in company_name):
            company_label.setAlignment(Qt.AlignRight)
        main_info_layout.addWidget(company_label)

        details_layout = QHBoxLayout()
        details_layout.setSpacing(20)

        supplier_name = sup.get("contact_name") or sup.get("name") or "לא צוין"
        supplier_label = QLabel(f"ספק: {supplier_name}")
        supplier_label.setStyleSheet("font-size: 13px; color: #374151;")
        details_layout.addWidget(supplier_label)

        phone = sup.get("phone") or "אין טלפון"
        phone_label = QLabel(f"טלפון: {phone}")
        phone_label.setStyleSheet("font-size: 13px; color: #6b7280;")
        details_layout.addWidget(phone_label)

        details_layout.addStretch()
        main_info_layout.addLayout(details_layout)
        main_layout.addLayout(main_info_layout, 1)

        requested_at = link.get("requested_at") or link.get("created_at")
        if requested_at:
            if isinstance(requested_at, str):
                date_text = requested_at.split('T')[0] if 'T' in requested_at else requested_at
                time_text = requested_at.split('T')[1][:5] if 'T' in requested_at and len(requested_at.split('T')) > 1 else ""
            else:
                try:
                    date_text = requested_at.strftime("%d/%m/%Y")
                    time_text = requested_at.strftime("%H:%M")
                except Exception:
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

        parent_layout.addWidget(card)

    def _add_active_card(self, parent_layout, link):
        sup = link.get("owner", {})  # מבנה הקישור: owner = פרטי הספק
        card = QWidget()
        card.setObjectName("card")
        card.setMinimumHeight(80)
        main_layout = QHBoxLayout(card)
        main_layout.setContentsMargins(20, 16, 20, 16)
        main_layout.setSpacing(16)

        status_dot = QLabel("●")
        status_dot.setStyleSheet("color: #10b981; font-size: 16px;")
        status_dot.setFixedWidth(16)
        main_layout.addWidget(status_dot, 0, Qt.AlignCenter)

        main_info_layout = QVBoxLayout()
        main_info_layout.setSpacing(2)

        company_name = sup.get("company_name") or "לא צוין"
        company_label = QLabel(company_name)
        company_label.setStyleSheet("font-size: 16px; font-weight: 700; color: #111827;")
        if any(ord(ch) < 128 and ch.isalpha() for ch in company_name):
            company_label.setAlignment(Qt.AlignRight)
        main_info_layout.addWidget(company_label)

        details_layout = QHBoxLayout()
        details_layout.setSpacing(20)

        supplier_name = sup.get("contact_name") or sup.get("name") or "לא צוין"
        supplier_label = QLabel(f"ספק: {supplier_name}")
        supplier_label.setStyleSheet("font-size: 13px; color: #374151;")
        details_layout.addWidget(supplier_label)

        phone = sup.get("phone") or "אין טלפון"
        phone_label = QLabel(f"טלפון: {phone}")
        phone_label.setStyleSheet("font-size: 13px; color: #6b7280;")
        details_layout.addWidget(phone_label)

        details_layout.addStretch()
        main_info_layout.addLayout(details_layout)
        main_layout.addLayout(main_info_layout, 1)

        # כפתור הזמנה בצד השמאלי
        order_btn = QPushButton("לביצוע הזמנה")
        order_btn.clicked.connect(lambda: self._place_order(sup.get("id")))
        main_layout.addWidget(order_btn, 0, Qt.AlignCenter)

        created_at = link.get("approved_at") or link.get("created_at")
        if created_at:
            if isinstance(created_at, str):
                date_text = created_at.split('T')[0] if 'T' in created_at else created_at
                time_text = created_at.split('T')[1][:5] if 'T' in created_at and len(created_at.split('T')) > 1 else ""
            else:
                try:
                    date_text = created_at.strftime("%d/%m/%Y")
                    time_text = created_at.strftime("%H:%M")
                except Exception:
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

        parent_layout.addWidget(card)

    # --- data flow ---
    @Slot()
    def refresh(self):
        try:
            # active
            act = _get_active(self.owner_id) or []
            self._rebuild(self._active_list, act, self._add_active_card)
            self._active_scroll.setVisible(bool(act))
            self.lbl_active_empty.setVisible(not bool(act))

            # pending
            pend = _get_pending(self.owner_id) or []
            self._rebuild(self._pending_list, pend, self._add_pending_card)
            self._pending_scroll.setVisible(bool(pend))
            self.lbl_pending_empty.setVisible(not bool(pend))

            # find suppliers
            f_list = _find_suppliers(self.owner_id) or []
            self._rebuild(self._find_list, f_list, self._add_supplier_card)
            self._find_scroll.setVisible(bool(f_list))
            self.lbl_find_empty.setVisible(not bool(f_list))
        except Exception as e:
            QMessageBox.warning(self, "שגיאה", str(e))

    def _rebuild(self, lay, items, add_func):
        while lay.count():
            it = lay.takeAt(0)
            if it.widget():
                it.widget().deleteLater()
        for x in items:
            add_func(lay, x)
        lay.addStretch()

    def _send_request(self, supplier_id):
        if not supplier_id:
            return
        try:
            _request_link(self.owner_id, supplier_id)
            QMessageBox.information(self, "הודעה", "הבקשה נשלחה!")
            self.refresh()
        except Exception as e:
            QMessageBox.warning(self, "שגיאה", str(e))

    def _place_order(self, supplier_id):
        if not supplier_id:
            return
        # חלון יחיד: אם הגיע callback מהמסך הראשי – ננווט inline
        if callable(getattr(self, "open_order_inline", None)):
            self.open_order_inline(int(supplier_id))
