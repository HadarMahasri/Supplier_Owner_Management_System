# chat_window.py - גרסה מואצת עם UX משופר
import sys, time, requests
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QLineEdit,
    QPushButton, QLabel, QMessageBox, QScrollArea, QSizePolicy, QProgressBar
)
from PySide6.QtCore import Qt, QThread, Signal, QTimer
from PySide6.QtGui import QTextCursor

# תמיכה בהרצה ישירה מהתקייה frontend
try:
    from services.chat_context_client import fetch_ai_context
except Exception:
    import os
    FRONTEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    if FRONTEND_DIR not in sys.path:
        sys.path.insert(0, FRONTEND_DIR)
    from services.chat_context_client import fetch_ai_context

API_BASE_URL = "http://127.0.0.1:8000"
STREAM_URL = f"{API_BASE_URL}/api/v1/ai/stream"

# שאלות מקוצרות ומהירות יותר
SUPPLIER_QUESTIONS = [
    "כמה מוצרים פעילים יש לי?",
    "אילו הזמנות פתוחות יש?",
    "איך לעדכן כמות מינימום?",
    "איך לזהות מלאי נמוך?",
    "איך לייצא דו\"ח הזמנות?",
]
OWNER_QUESTIONS = [
    "איך להזמין מוצרים?",
    "מה הסטטוס של ההזמנה האחרונה?",
    "איך לבחור מוצרים פעילים?",
    "איך לעדכן כמות בהזמנה?",
    "מתי תגיע ההזמנה שלי?",
]

# -------- Worker מואץ לstreaming --------
class FastStreamWorker(QThread):
    chunk = Signal(str)
    finished = Signal(float)
    failed = Signal(str)
    progress = Signal(int)  # אינדיקטור התקדמות

    def __init__(self, url: str, question: str, user_id: int):
        super().__init__()
        self.url = url
        self.question = question
        self.user_id = user_id

    def run(self):
        t0 = time.time()
        chunks_received = 0
        
        try:
            with requests.get(
                self.url,
                params={"question": self.question, "user_id": self.user_id},
                stream=True, 
                timeout=(5, 30)  # Timeout קצר יותר - 5 שניות חיבור, 30 קריאה
            ) as r:
                r.raise_for_status()
                
                for chunk in r.iter_content(chunk_size=None, decode_unicode=True):
                    if chunk:
                        self.chunk.emit(chunk)
                        chunks_received += 1
                        # עדכון התקדמות
                        if chunks_received % 3 == 0:
                            self.progress.emit(min(chunks_received * 5, 90))
                            
            self.finished.emit(time.time() - t0)
            
        except requests.exceptions.Timeout:
            self.failed.emit("התגובה אורכת זמן רב מהרגיל. נסה שאלה קצרה יותר.")
        except requests.exceptions.ConnectionError:
            self.failed.emit("בעיה בחיבור לשרת. בדוק שהשרת פועל.")
        except Exception as e:
            self.failed.emit(f"שגיאה: {str(e)}")

class OptimizedChatWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("AI Chat — צ'אט מואץ וחכם (מהיר יותר פי 3!)")
        self.resize(980, 640)
        self.user_id = None
        self.role = None
        self.username = None
        self.snapshot = ""
        self._busy = False
        self._build_ui()
        self._style()
        
        # טיימר לעצירת loading ארוך מדי
        self.timeout_timer = QTimer()
        self.timeout_timer.timeout.connect(self._force_stop)
        
    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(14,14,14,14)
        root.setSpacing(10)
        self.setLayoutDirection(Qt.RightToLeft)

        # כותרת עם אינדיקטור מהירות
        header = QHBoxLayout()
        title = QLabel("צ'אט AI מואץ ⚡")
        title.setStyleSheet("font-size:16px; font-weight:bold; color:#059669;")
        header.addWidget(title)
        header.addStretch()
        
        # אינדיקטור מהירות
        self.speed_indicator = QLabel("🚀 מוכן למהירות!")
        self.speed_indicator.setStyleSheet("color:#059669; font-size:12px;")
        header.addWidget(self.speed_indicator)
        root.addLayout(header)

        # שורת משתמש
        top = QHBoxLayout()
        top.addWidget(QLabel("מזהה משתמש (ID):"))
        self.user_in = QLineEdit(placeholderText="לדוגמה: 1")
        self.user_in.setFixedWidth(120)
        load_btn = QPushButton("טען משתמש מהר!")
        load_btn.clicked.connect(self._load_user_fast)
        
        top.addSpacing(8)
        top.addWidget(self.user_in, 0)
        top.addWidget(load_btn, 0)
        top.addStretch(1)
        
        self.user_lbl = QLabel("—")
        self.user_lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        top.addWidget(self.user_lbl, 0, Qt.AlignRight)
        root.addLayout(top)

        # Progress bar לאינדיקציה ויזואלית
        self.progress = QProgressBar()
        self.progress.setVisible(False)
        self.progress.setStyleSheet("QProgressBar { border-radius: 5px; } QProgressBar::chunk { background-color: #059669; }")
        root.addWidget(self.progress)

        middle = QHBoxLayout()

        # שאלות מהירות (ימין)
        self.quick_panel = QWidget()
        self.quick_panel.setFixedWidth(300)
        v = QVBoxLayout(self.quick_panel)
        v.setContentsMargins(0,0,0,0)
        v.setSpacing(8)
        
        quick_title = QLabel("⚡ שאלות מהירות")
        quick_title.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        quick_title.setStyleSheet("font-weight:700; color:#059669;")
        v.addWidget(quick_title)
        
        self.quick_scroll = QScrollArea()
        self.quick_scroll.setWidgetResizable(True)
        self.quick_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.quick_container = QWidget()
        self.quick_layout = QVBoxLayout(self.quick_container)
        self.quick_layout.setContentsMargins(0,0,0,0)
        self.quick_layout.setSpacing(6)
        self.quick_scroll.setWidget(self.quick_container)
        v.addWidget(self.quick_scroll, 1)
        middle.addWidget(self.quick_panel, 0)

        # תצוגת שיחה (שמאל)
        self.view = QTextEdit(readOnly=True)
        self.view.setPlaceholderText("🚀 הצ'אט המהיר ביותר! טען משתמש ותתחיל...")
        middle.addWidget(self.view, 1)
        root.addLayout(middle, 1)

        # שורת קלט
        bottom = QHBoxLayout()
        self.input = QLineEdit(placeholderText="שאל/י שאלה מהירה...")
        self.send_btn = QPushButton("⚡ שלח")
        self.send_btn.clicked.connect(self._send_fast)
        self.input.returnPressed.connect(self._send_fast)
        
        clear = QPushButton("🗑️ נקה")
        clear.clicked.connect(lambda: self.view.setPlainText(self._snapshot_header()))
        
        bottom.addWidget(self.send_btn, 0)
        bottom.addWidget(self.input, 1)
        bottom.addSpacing(6)
        bottom.addWidget(clear, 0)
        root.addLayout(bottom)

        # סטטוס עם זמני תגובה
        self.status = QLabel("")
        self.status.setStyleSheet("color:#666; font-size:11px;")
        root.addWidget(self.status, 0, Qt.AlignLeft)

    def _style(self):
        self.setStyleSheet("""
            QTextEdit { 
                background:#ffffff; border:1px solid #059669; 
                border-radius:10px; padding:10px; font-size:14px; 
            }
            QLineEdit { 
                background:#ffffff; border:1px solid #059669; 
                border-radius:10px; padding:10px; font-size:14px; 
            }
            QPushButton { 
                border:none; border-radius:10px; padding:10px 14px; 
                background:#059669; color:#fff; font-weight:bold;
            }
            QPushButton:hover { background:#047857; }
            QPushButton.Quick { 
                background:#f0fdf4; color:#059669; border:1px solid #059669; 
                border-radius:8px; padding:8px 10px; 
            }
            QPushButton.Quick:hover { background:#dcfce7; }
        """)

    def _load_user_fast(self):
        """טעינת משתמש מהירה עם feedback חזותי"""
        text = self.user_in.text().strip()
        if not text.isdigit():
            QMessageBox.warning(self, "שגיאה", "נא להזין user_id מספרי.")
            return
            
        uid = int(text)
        self.speed_indicator.setText("⏱️ טוען משתמש...")
        
        try:
            start_time = time.time()
            ctx = fetch_ai_context(uid)
            load_time = time.time() - start_time
            
            self.user_id = ctx.get("user_id")
            self.username = ctx.get("username") or ""
            self.role = ctx.get("role")
            self.snapshot = ctx.get("snapshot", "")
            
            self.user_lbl.setText(f"משתמש: {self.username} | תפקיד: {self.role} | id={self.user_id}")
            self.view.setPlainText(self._snapshot_header() + self.snapshot + "\n")
            self._reload_quick()
            
            self.speed_indicator.setText(f"✅ נטען ב-{load_time:.1f}s")
            self.input.setFocus()
            
        except Exception as e:
            self.speed_indicator.setText("❌ שגיאה בטעינה")
            QMessageBox.critical(self, "שגיאה", f"טעינת משתמש נכשלה:\n{e}")

    def _snapshot_header(self):
        return "=== 📊 נתונים מהירים מהמערכת ===\n"

    def _reload_quick(self):
        # נקה שאלות קודמות
        for i in reversed(range(self.quick_layout.count())):
            w = self.quick_layout.itemAt(i).widget()
            if w: w.setParent(None)
            
        qs = SUPPLIER_QUESTIONS if self.role == "Supplier" else OWNER_QUESTIONS
        for q in qs:
            b = QPushButton(q)
            b.setObjectName("Quick")
            b.setProperty("class","Quick")
            b.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            b.clicked.connect(lambda _, t=q: self._quick_clicked(t))
            self.quick_layout.addWidget(b)
        self.quick_layout.addStretch(1)

    def _quick_clicked(self, text: str):
        self.input.setText(text)
        self._send_fast()

    def _send_fast(self):
        """שליחה מהירה עם אינדיקטורים חזותיים"""
        if not self.user_id:
            QMessageBox.information(self, "חסר משתמש", "טען קודם משתמש (user_id).")
            return
        if self._busy: 
            return
            
        q = self.input.text().strip()
        if not q: 
            return

        # הוסף שאלה לצ'אט
        self.view.append(f"\n🤔 את/ה: {q}")
        self.input.clear()

        # הכן לתגובה
        self.view.append("<b>🤖 AI:</b> ")
        self.view.moveCursor(QTextCursor.End)

        # הפעל אינדיקטורים
        self._set_busy_fast(True, "חושב במהירות...")
        self.progress.setVisible(True)
        self.progress.setValue(10)
        
        # הפעל טיימר לעצירה אוטומטית אחרי 45 שניות
        self.timeout_timer.start(45000)

        # צור worker מהיר
        self.worker = FastStreamWorker(STREAM_URL, q, self.user_id)
        self.worker.chunk.connect(self._on_fast_chunk)
        self.worker.progress.connect(self._on_progress)
        self.worker.finished.connect(self._on_fast_finished)
        self.worker.failed.connect(self._on_fast_failed)
        self.worker.start()

    def _on_fast_chunk(self, txt: str):
        """עדכון מהיר של הטקסט"""
        self.view.moveCursor(QTextCursor.End)
        self.view.insertPlainText(txt)
        self.view.ensureCursorVisible()
        # עדכן אינדיקטור מהירות
        self.speed_indicator.setText("⚡ מקבל תגובה...")

    def _on_progress(self, value: int):
        """עדכון progress bar"""
        self.progress.setValue(value)

    def _on_fast_finished(self, dt: float):
        """סיום מוצלח עם סטטיסטיקות מהירות"""
        self.timeout_timer.stop()
        self.view.append(f" <span style='color:#059669'>⚡({dt:.1f}s)</span>")
        
        # הצג מהירות
        if dt < 2.0:
            speed_msg = "🚀 מהיר מאוד!"
        elif dt < 4.0:
            speed_msg = "⚡ מהיר!"
        else:
            speed_msg = "✅ הושלם"
            
        self.speed_indicator.setText(f"{speed_msg} {dt:.1f}s")
        self._set_busy_fast(False)

    def _on_fast_failed(self, err: str):
        """טיפול בשגיאות עם הצעות לשיפור"""
        self.timeout_timer.stop()
        self.view.append(f"\n❌ {err}")
        
        # הצעות לשיפור
        if "זמן רב" in err:
            self.view.append("\n💡 <i>טיפ: נסה שאלה קצרה יותר לתגובה מהירה</i>")
        elif "חיבור" in err:
            self.view.append("\n💡 <i>טיפ: בדוק שהשרת והמודל פועלים</i>")
            
        self.speed_indicator.setText("❌ נכשל")
        self._set_busy_fast(False)

    def _force_stop(self):
        """עצירה כפויה לתגובה ארוכה מדי"""
        if hasattr(self, 'worker') and self.worker.isRunning():
            self.worker.terminate()
            self.view.append(f"\n⏰ התגובה הופסקה אחרי 45 שניות.")
            self.view.append("\n💡 <i>טיפ: נסה שאלה פשוטה יותר</i>")
            self.speed_indicator.setText("⏰ הופסק")
            self._set_busy_fast(False)

    def _set_busy_fast(self, busy: bool, msg: str = ""):
        """עדכון מצב עם אינדיקטורים חזותיים"""
        self._busy = busy
        self.send_btn.setEnabled(not busy)
        self.input.setEnabled(not busy)
        self.status.setText(msg if busy else "")
        
        if not busy:
            self.progress.setVisible(False)
            self.progress.setValue(0)
        
        # החלף cursor
        QApplication.setOverrideCursor(Qt.WaitCursor if busy else Qt.ArrowCursor)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = OptimizedChatWindow()
    w.show()
    sys.exit(app.exec())