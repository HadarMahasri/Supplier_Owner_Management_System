# frontend/views/widgets/service_areas_picker.py
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QScrollArea, QFrame, QCheckBox, QGridLayout
)


class ServiceAreasPicker(QWidget):
    """
    data format:
    [
      {"district_id": 1, "district_name": "דרום", "cities": [
          {"city_id": 11, "city_name": "אשקלון"}, ...
      ]},
      ...
    ]
    """
    selection_changed = Signal(set)  # emits set of selected city_ids

    def __init__(self, data: list[dict]):
        super().__init__()
        self._data = data or []
        self._city_boxes: dict[int, QCheckBox] = {}
        self._district_boxes: dict[int, QCheckBox] = {}

        # הגדרת RTL לכל הוידג'ט
        self.setLayoutDirection(Qt.RightToLeft)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        
        # עיצוב: צ׳קבוקסים גדולים, טקסט ברור עם יישור לימין
        self.setStyleSheet("""
            QWidget { 
                font-size: 15px; 
            }
            QCheckBox { 
                spacing: 10px;
                text-align: right;
            }
            QCheckBox::indicator {
                width: 22px;
                height: 22px;
            }
            QCheckBox::indicator:unchecked {
                border: 2px solid #cbd5e1;
                border-radius: 4px;
                background: #fff;
            }
            QCheckBox::indicator:checked {
                border: 2px solid #2563eb;
                background: #2563eb;
                border-radius: 4px;
            }
            QLineEdit { 
                padding: 10px 12px; 
                border:1px solid #e2e8f0; 
                border-radius:8px;
                text-align: right;
            }
            QPushButton { 
                padding: 8px 12px; 
                border-radius:8px; 
                font-weight:600; 
            }
            QLabel {
                text-align: right;
            }
        """)

        # Controls - סידור מימין לשמאל
        header = QHBoxLayout()
        
        self.search = QLineEdit(placeholderText="חיפוש עיר…")
        self.search.setAlignment(Qt.AlignRight)
        
        btn_all = QPushButton("בחר הכל")
        btn_none = QPushButton("נקה הכל")
        
        self.counter = QLabel("0 ערים נבחרו")
        self.counter.setStyleSheet("color:#6b7280; text-align: right;")
        self.counter.setAlignment(Qt.AlignRight)
        
        # סידור הכפתורים מימין לשמאל
        header.addWidget(self.search, 1)
        header.addWidget(btn_all)
        header.addWidget(btn_none)
        header.addStretch()
        header.addWidget(self.counter)
        root.addLayout(header)

        # Scrollable grid (2 columns)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setLayoutDirection(Qt.RightToLeft)
        
        container = QWidget()
        container.setLayoutDirection(Qt.RightToLeft)
        
        self.grid = QGridLayout(container)
        self.grid.setContentsMargins(6, 6, 6, 6)
        self.grid.setHorizontalSpacing(24)
        self.grid.setVerticalSpacing(6)

        # חשוב: להצמיד את כל הגריד לימין ולשמור סימטריה בין שתי עמודות
        self.grid.setAlignment(Qt.AlignTop | Qt.AlignRight)
        self.grid.setColumnStretch(0, 1)
        self.grid.setColumnStretch(1, 1)
        
        scroll.setWidget(container)
        root.addWidget(scroll, 1)

        self._build()

        # wiring
        self.search.textChanged.connect(self._apply_filter)
        btn_all.clicked.connect(self._select_all)
        btn_none.clicked.connect(self._clear_all)

    def _build(self):
        row = 0
        for d in self._data:
            # district header - עם יישור לימין
            hdr = QCheckBox(d["district_name"])
            hdr.setStyleSheet("font-weight:600; text-align: right;")
            hdr.setLayoutDirection(Qt.RightToLeft)
            
            self.grid.addWidget(hdr, row, 0, 1, 2, alignment=Qt.AlignRight | Qt.AlignTop)
            self._district_boxes[d["district_id"]] = hdr
            row += 1

            # cities in two columns - עם יישור לימין
            col = 0
            ids = []
            for c in d["cities"]:
                cid = c["city_id"]
                ids.append(cid)
                cb = QCheckBox(c["city_name"])
                cb.setLayoutDirection(Qt.RightToLeft)
                # הסרת qproperty-alignment שלא עובד עם QCheckBox
                cb.setStyleSheet("text-align: right;")
                
                self._city_boxes[cid] = cb
                # להצמיד לקצה ימין ולמרכז אנכי כדי להיות בקו אחד עם התיבה
                self.grid.addWidget(cb, row, col, alignment=Qt.AlignRight | Qt.AlignVCenter)
                cb.stateChanged.connect(self._update_counter_emit)
                if col == 1:
                    row += 1
                    col = 0
                else:
                    col = 1

            # אם יש מספר אי-זוגי של ערים, עבור לשורה הבאה
            if col == 1:
                row += 1

            # separator
            line = QFrame()
            line.setFrameShape(QFrame.HLine)
            line.setStyleSheet("color:#e5e7eb;")
            self.grid.addWidget(line, row, 0, 1, 2)
            row += 1

            hdr.stateChanged.connect(lambda st, ids=ids: self._toggle_district(ids, st))

        self._update_counter_emit()

    # helpers
    def _toggle_district(self, city_ids, state):
        checked = bool(state)
        for cid in city_ids:
            self._city_boxes[cid].setChecked(checked)
        self._update_counter_emit()

    def _select_all(self):
        for cb in self._city_boxes.values():
            cb.setChecked(True)
        self._update_counter_emit()

    def _clear_all(self):
        for cb in self._city_boxes.values():
            cb.setChecked(False)
        self._update_counter_emit()

    def _apply_filter(self, text: str):
        text = (text or "").strip().lower()
        for cb in self._city_boxes.values():
            cb.setVisible((text in cb.text().lower()) if text else True)
        self._update_counter_emit()

    def selected_ids(self) -> set[int]:
        return {cid for cid, cb in self._city_boxes.items() if cb.isChecked()}

    def _update_counter_emit(self):
        n = len(self.selected_ids())
        self.counter.setText(f"{n} ערים נבחרו")
        self.selection_changed.emit(self.selected_ids())
