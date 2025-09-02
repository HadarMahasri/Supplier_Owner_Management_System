# ai_consultant.py - גרסה מואצת עם UX משופר
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
    QPushButton, QTextEdit, QProgressBar
)
from PySide6.QtCore import Qt, QTimer, QThread, Signal
from services.ai_client import ask_ai
import time

class FastAIWorker(QThread):
    """Worker thread לשאלות AI מהירות"""
    finished = Signal(str, float)  # תגובה + זמן
    failed = Signal(str)

    def __init__(self, question: str, user_id: int):
        super().__init__()
        self.question = question
        self.user_id = user_id

    def run(self):
        start_time = time.time()
        try:
            answer = ask_ai(self.question, self.user_id)
            duration = time.time() - start_time
            self.finished.emit(answer, duration)
        except Exception as e:
            self.failed.emit(str(e))

class OptimizedAIConsultant(QWidget):
    def __init__(self, user_id: int, parent=None):
        super().__init__(parent)
        self.user_id = user_id
        self.setLayoutDirection(Qt.RightToLeft)
        self._build_ui()
        self._style()
        self._busy = False

    def _build_ui(self):
        root = QVBoxLayout(self)
        
        # כותרת מתקדמת
        header = QHBoxLayout()
        title = QLabel("🤖 יועץ AI מהיר")
        title.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: #059669;")
        header.addWidget(title)
        
        # אינדיקטור מהירות
        self.speed_label = QLabel("⚡ מוכן לעזרה!")
        self.speed_label.setStyleSheet("color: #059669; font-size: 12px;")
        header.addStretch()
        header.addWidget(self.speed_label)
        root.addLayout(header)

        # Progress bar
        self.progress = QProgressBar()
        self.progress.setVisible(False)
        self.progress.setStyleSheet("""
            QProgressBar { 
                border: 1px solid #059669; 
                border-radius: 5px; 
                text-align: center; 
            }
            QProgressBar::chunk { 
                background-color: #059669; 
                border-radius: 4px; 
            }
        """)
        root.addWidget(self.progress)

        # קלט שאלה
        self.q = QLineEdit(placeholderText="שאל/י שאלה מהירה...")
        send = QPushButton("⚡ שלח מהר")
        
        # כפתורי שאלות מהירות
        quick_row = QHBoxLayout()
        quick_questions = ["כמה מוצרים יש?", "מצב הזמנות?", "עזרה כללית"]
        for q_text in quick_questions:
            btn = QPushButton(q_text)
            btn.setObjectName("QuickBtn")
            btn.clicked.connect(lambda checked, txt=q_text: self._ask_quick(txt))
            quick_row.addWidget(btn)
        quick_row.addStretch()
        
        root.addWidget(QLabel("שאלות מהירות:"))
        root.addLayout(quick_row)

        # שורת שליחה
        row = QHBoxLayout()
        row.addWidget(send, 0)
        row.addWidget(self.q, 1)
        root.addLayout(row)

        # תצוגת תגובות
        self.out = QTextEdit(readOnly=True)
        self.out.setPlaceholderText("🚀 התגובות יופיעו כאן במהירות הברק!")
        root.addWidget(self.out, 1)

        # חיבור אירועים
        send.clicked.connect(self._send_fast)
        self.q.returnPressed.connect(self._send_fast)
        
        # טיימר לעצירה אוטומטית
        self.timeout_timer = QTimer()
        self.timeout_timer.timeout.connect(self._force_stop)

    def _style(self):
        self.setStyleSheet("""
            QTextEdit { 
                background: #fff; 
                border: 1px solid #059669; 
                border-radius: 8px; 
                padding: 8px; 
                font-size: 13px;
            }
            QLineEdit { 
                border: 1px solid #059669; 
                border-radius: 8px; 
                padding: 8px; 
                font-size: 13px;
            }
            QPushButton { 
                background: #059669; 
                color: #fff; 
                border: none; 
                border-radius: 8px; 
                padding: 8px 16px; 
                font-weight: bold;
            }
            QPushButton:hover { 
                background: #047857; 
            }
            QPushButton#QuickBtn {
                background: #f0fdf4;
                color: #059669;
                border: 1px solid #059669;
                padding: 4px 8px;
                font-size: 11px;
            }
            QPushButton#QuickBtn:hover {
                background: #dcfce7;
            }
        """)

    def _ask_quick(self, question: str):
        """שאלה מהירה מכפתור"""
        self.q.setText(question)
        self._send_fast()

    def _send_fast(self):
        """שליחה מהירה עם אינדיקטורים"""
        if self._busy:
            return
            
        text = self.q.text().strip()
        if not text:
            return

        # הצג שאלה
        self.out.append(f"🤔 <b>את/ה:</b> {text}")
        self.q.clear()

        # התחל טעינה
        self._set_busy(True)
        self.speed_label.setText("⏱️ חושב...")
        
        # הפעל worker
        self.worker = FastAIWorker(text, self.user_id)
        self.worker.finished.connect(self._on_answer)
        self.worker.failed.connect(self._on_error)
        self.worker.start()
        
        # טיימר לעצירה אחרי 30 שניות
        self.timeout_timer.start(30000)

    def _on_answer(self, answer: str, duration: float):
        """קבלת תגובה מוצלחת"""
        self.timeout_timer.stop()
        
        # הצג תגובה עם זמן
        speed_icon = "🚀" if duration < 2 else "⚡" if duration < 5 else "✅"
        self.out.append(f"{speed_icon} <b>AI:</b> {answer}")
        self.out.append(f"<i style='color:#666'>⏱️ תגובה ב-{duration:.1f} שניות</i>\n")
        
        # עדכן אינדיקטור
        if duration < 2:
            self.speed_label.setText("🚀 מהיר מאוד!")
        elif duration < 5:
            self.speed_label.setText("⚡ מהיר!")
        else:
            self.speed_label.setText("✅ הושלם")
            
        self._set_busy(False)

    def _on_error(self, error: str):
        """טיפול בשגיאה"""
        self.timeout_timer.stop()
        self.out.append(f"❌ <b>שגיאה:</b> {error}")
        self.speed_label.setText("❌ נכשל")
        self._set_busy(False)

    def _force_stop(self):
        """עצירה כפויה"""
        if hasattr(self, 'worker') and self.worker.isRunning():
            self.worker.terminate()
            self.out.append("⏰ <b>התגובה הופסקה</b> אחרי 30 שניות")
            self.speed_label.setText("⏰ הופסק")
            self._set_busy(False)

    def _set_busy(self, busy: bool):
        """עדכון מצב טעינה"""
        self._busy = busy
        self.progress.setVisible(busy)
        
        if busy:
            self.progress.setRange(0, 0)  # אנימציה אינסופית
        else:
            self.progress.setRange(0, 100)
            self.progress.setValue(100)