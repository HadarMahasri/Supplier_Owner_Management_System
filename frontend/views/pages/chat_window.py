# chat_window.py - גרסה חכמה עם השילוב החדש
import sys, time, requests
from typing import List, Dict
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QLineEdit,
    QPushButton, QLabel, QMessageBox, QScrollArea, QSizePolicy, QProgressBar,
    QTabWidget, QFrame, QCheckBox
)
from PySide6.QtCore import Qt, QThread, Signal, QTimer
from PySide6.QtGui import QTextCursor, QFont

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
SUGGESTIONS_URL = f"{API_BASE_URL}/api/v1/ai/smart-suggestions"
INSIGHTS_URL    = f"{API_BASE_URL}/api/v1/ai/business-insights"

# שאלות בסיסיות (נשארות כ-fallback)
SUPPLIER_BASE_QUESTIONS = [
    "כמה מוצרים פעילים יש לי?",
    "אילו הזמנות פתוחות יש?", 
    "אילו מוצרים במלאי נמוך?",
    "כמה הרווחתי החודש?",
    "אילו המוצרים הנמכרים ביותר?"
]

OWNER_BASE_QUESTIONS = [
    "מה המצב של ההזמנות שלי?",
    "מאיזה ספק כדאי להזמין?",
    "כמה הוצאתי החודש?", 
    "מתי תגיע ההזמנה שלי?",
    "איך להזמין שוב את אותם מוצרים?"
]

class SmartSuggestionsWorker(QThread):
    """Worker לקבלת הצעות שאלות חכמות מהשרת"""
    suggestions_ready = Signal(list)
    insights_ready = Signal(dict)
    failed = Signal(str)

    def __init__(self, user_id: int):
        super().__init__()
        self.user_id = user_id

    def run(self):
        try:
            # קבלת הצעות שאלות חכמות
            try:
                r = requests.get(SUGGESTIONS_URL, params={"user_id": self.user_id}, timeout=5)
                if r.status_code == 200:
                    suggestions = r.json().get("suggestions", [])
                    self.suggestions_ready.emit(suggestions)
            except:
                pass  # אם לא עובד, נשתמש ב-fallback
            
            # קבלת תובנות עסקיות
            try:
                r = requests.get(INSIGHTS_URL, params={"user_id": self.user_id}, timeout=5)
                if r.status_code == 200:
                    insights = r.json()
                    self.insights_ready.emit(insights)
            except:
                pass  # אם לא עובד, פשוט לא נציג תובנות
                
        except Exception as e:
            self.failed.emit(str(e))

class FastStreamWorker(QThread):
    chunk = Signal(str)
    finished = Signal(float)
    failed = Signal(str)
    progress = Signal(int)

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
                timeout=(5, 120)  # timeout יותר ארוך למערכת החכמה
            ) as r:
                r.raise_for_status()
                
                for chunk in r.iter_content(chunk_size=None, decode_unicode=True):
                    if chunk:
                        self.chunk.emit(chunk)
                        chunks_received += 1
                        if chunks_received % 2 == 0:
                            self.progress.emit(min(chunks_received * 3, 95))
                            
            self.finished.emit(time.time() - t0)
            
        except requests.exceptions.Timeout:
            self.failed.emit("התגובה החכמה אורכת יותר זמן מהרגיל. אנא המתן...")
        except requests.exceptions.ConnectionError:
            self.failed.emit("בעיה בחיבור לשרת AI. בדוק שהשרת פועל.")
        except Exception as e:
            self.failed.emit(f"שגיאה: {str(e)}")

class EnhancedChatWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("🧠 AI Chat חכם - מערכת ניהול ספקים")
        self.resize(1100, 720)
        self.user_id = None
        self.role = None
        self.username = None
        self.snapshot = ""
        self._busy = False
        self.smart_suggestions = []
        self.business_insights = {}
        
        self._build_ui()
        self._style()
        
        self.timeout_timer = QTimer()
        self.timeout_timer.timeout.connect(self._force_stop)
        
    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(16,16,16,16)
        root.setSpacing(12)
        self.setLayoutDirection(Qt.RightToLeft)

        # כותרת משופרת
        header = QHBoxLayout()
        title = QLabel("🧠 צ'אט AI חכם")
        title.setStyleSheet("font-size:18px; font-weight:bold; color:#047857;")
        header.addWidget(title)
        header.addStretch()
        
        self.ai_status = QLabel("🤖 מערכת AI מוכנה")
        self.ai_status.setStyleSheet("color:#047857; font-size:13px; font-weight:bold;")
        header.addWidget(self.ai_status)
        root.addLayout(header)

        # שורת משתמש משופרת
        user_frame = QFrame()
        user_frame.setFrameStyle(QFrame.StyledPanel)
        user_layout = QHBoxLayout(user_frame)
        
        user_layout.addWidget(QLabel("🆔 משתמש:"))
        self.user_in = QLineEdit(placeholderText="הזן user_id")
        self.user_in.setFixedWidth(100)
        
        load_btn = QPushButton("🔄 טען")
        load_btn.setFixedWidth(80)
        load_btn.clicked.connect(self._load_user_smart)
        
        user_layout.addWidget(self.user_in)
        user_layout.addWidget(load_btn)
        user_layout.addStretch()
        
        self.user_info = QLabel("—")
        self.user_info.setAlignment(Qt.AlignRight)
        user_layout.addWidget(self.user_info)
        
        root.addWidget(user_frame)

        # Progress bar מעוצב
        self.progress = QProgressBar()
        self.progress.setVisible(False)
        self.progress.setStyleSheet("""
            QProgressBar { border-radius: 8px; text-align: center; border: 1px solid #047857; }
            QProgressBar::chunk { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #059669, stop:1 #047857); border-radius: 7px; }
        """)
        root.addWidget(self.progress)

        # תצוגה ראשית עם טאבים
        self.tabs = QTabWidget()
        
        # טאב צ'אט
        chat_widget = QWidget()
        chat_layout = QHBoxLayout(chat_widget)
        
        # פאנל שאלות חכמות (ימין)
        self._build_smart_questions_panel(chat_layout)
        
        # אזור השיחה (שמאל)
        self.view = QTextEdit(readOnly=True)
        self.view.setPlaceholderText("🧠 צ'אט חכם מוכן! טען משתמש כדי להתחיל לקבל תובנות עסקיות...")
        chat_layout.addWidget(self.view, 2)
        
        self.tabs.addTab(chat_widget, "💬 צ'אט")
        
        # טאב תובנות עסקיות
        insights_widget = QWidget() 
        insights_layout = QVBoxLayout(insights_widget)
        
        insights_layout.addWidget(QLabel("📊 תובנות עסקיות"))
        self.insights_display = QTextEdit(readOnly=True)
        self.insights_display.setPlaceholderText("תובנות עסקיות יופיעו כאן אחרי טעינת המשתמש...")
        insights_layout.addWidget(self.insights_display)
        
        refresh_insights = QPushButton("🔄 רענן תובנות")
        refresh_insights.clicked.connect(self._refresh_insights)
        insights_layout.addWidget(refresh_insights)
        
        self.tabs.addTab(insights_widget, "📊 תובנות")
        
        root.addWidget(self.tabs, 1)

        # שורת קלט משופרת
        input_frame = QFrame()
        input_frame.setFrameStyle(QFrame.StyledPanel)
        input_layout = QHBoxLayout(input_frame)
        
        self.send_btn = QPushButton("🚀")
        self.send_btn.setFixedWidth(50)
        self.send_btn.clicked.connect(self._send_smart)
        
        self.input = QLineEdit(placeholderText="שאל שאלה או בקש עזרה...")
        self.input.returnPressed.connect(self._send_smart)
        
        self.auto_suggestions = QCheckBox("הצעות אוטו")
        self.auto_suggestions.setChecked(True)
        
        clear_btn = QPushButton("🗑️")
        clear_btn.setFixedWidth(40)
        clear_btn.clicked.connect(self._clear_chat)
        
        input_layout.addWidget(self.send_btn)
        input_layout.addWidget(self.input, 1)
        input_layout.addWidget(self.auto_suggestions)
        input_layout.addWidget(clear_btn)
        
        root.addWidget(input_frame)

        # סטטוס מפורט
        self.status = QLabel("")
        self.status.setStyleSheet("color:#666; font-size:11px; padding:5px;")
        root.addWidget(self.status)

    def _build_smart_questions_panel(self, parent_layout):
        """בונה פאנל שאלות חכמות"""
        panel = QWidget()
        panel.setFixedWidth(320)
        panel_layout = QVBoxLayout(panel)
        
        # כותרת
        panel_title = QLabel("🧠 שאלות חכמות")
        panel_title.setAlignment(Qt.AlignCenter)
        panel_title.setStyleSheet("font-weight:bold; color:#047857; font-size:14px; padding:5px;")
        panel_layout.addWidget(panel_title)
        
        # אזור הצעות דינמיות
        self.dynamic_suggestions = QLabel("טוען הצעות חכמות...")
        self.dynamic_suggestions.setAlignment(Qt.AlignCenter)
        self.dynamic_suggestions.setStyleSheet("color:#666; font-style:italic; padding:10px;")
        panel_layout.addWidget(self.dynamic_suggestions)
        
        # scroll area לשאלות
        self.smart_scroll = QScrollArea()
        self.smart_scroll.setWidgetResizable(True)
        self.smart_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        self.smart_container = QWidget()
        self.smart_layout = QVBoxLayout(self.smart_container)
        self.smart_layout.setContentsMargins(5,5,5,5)
        self.smart_layout.setSpacing(8)
        
        self.smart_scroll.setWidget(self.smart_container)
        panel_layout.addWidget(self.smart_scroll, 1)
        
        # כפתור רענון הצעות
        refresh_btn = QPushButton("🔄 רענן הצעות")
        refresh_btn.clicked.connect(self._refresh_suggestions)
        panel_layout.addWidget(refresh_btn)
        
        parent_layout.addWidget(panel, 0)

    def _style(self):
        self.setStyleSheet("""
            QWidget { 
                background-color: #f8fafc;
                font-family: 'Segoe UI', 'Arial';
            }
            QTextEdit { 
                background:#ffffff; 
                border:2px solid #047857; 
                border-radius:12px; 
                padding:12px; 
                font-size:14px;
                line-height:1.4;
            }
            QLineEdit { 
                background:#ffffff; 
                border:2px solid #047857; 
                border-radius:10px; 
                padding:12px; 
                font-size:14px; 
            }
            QLineEdit:focus { 
                border-color:#059669; 
                background:#f0fdf4;
            }
            QPushButton { 
                border:none; 
                border-radius:10px; 
                padding:10px 16px; 
                background:#047857; 
                color:#fff; 
                font-weight:bold;
                font-size:13px;
            }
            QPushButton:hover { 
                background:#059669; 
                transform: scale(1.05);
            }
            QPushButton.Smart { 
                background:#f0fdf4; 
                color:#047857; 
                border:2px solid #047857; 
                border-radius:10px; 
                padding:10px 12px;
                text-align: right;
                font-weight: normal;
            }
            QPushButton.Smart:hover { 
                background:#dcfce7; 
                border-color:#059669;
                color:#059669;
            }
            QFrame {
                background:#ffffff;
                border: 1px solid #e2e8f0;
                border-radius: 8px;
                padding: 5px;
            }
            QTabWidget::pane {
                border: 2px solid #047857;
                border-radius: 8px;
                background: #ffffff;
            }
            QTabBar::tab {
                background: #f1f5f9;
                padding: 8px 16px;
                margin: 2px;
                border-radius: 6px;
            }
            QTabBar::tab:selected {
                background: #047857;
                color: white;
            }
        """)

    def _load_user_smart(self):
        """טעינת משתמש עם מערכת חכמה"""
        text = self.user_in.text().strip()
        if not text.isdigit():
            QMessageBox.warning(self, "שגיאה", "נא להזין user_id מספרי.")
            return
            
        uid = int(text)
        self.ai_status.setText("🔄 טוען פרופיל...")
        
        try:
            start_time = time.time()
            
            # טעינת context בסיסי
            ctx = fetch_ai_context(uid)
            load_time = time.time() - start_time
            
            self.user_id = ctx.get("user_id")
            self.username = ctx.get("username") or ""
            self.role = ctx.get("role")
            self.snapshot = ctx.get("snapshot", "")
            
            # עדכון UI
            self.user_info.setText(f"👤 {self.username} | {self.role} | ID: {self.user_id}")
            self.view.setPlainText(self._format_snapshot())
            
            # טעינת שאלות חכמות ותובנות
            self._load_smart_features()
            
            self.ai_status.setText(f"✅ מוכן ({load_time:.1f}s)")
            self.input.setFocus()
            
        except Exception as e:
            self.ai_status.setText("❌ שגיאה")
            QMessageBox.critical(self, "שגיאה", f"טעינת משתמש נכשלה:\n{e}")

    def _format_snapshot(self) -> str:
        """פורמט מהיר לSnapshot"""
        lines = self.snapshot.split('\n')
        formatted = "🧠 === פרופיל המשתמש החכם ===\n\n"
        
        for line in lines:
            if line.strip():
                if line.startswith('===') or line.startswith('---'):
                    formatted += f"\n📋 {line.replace('=', '').strip()}\n"
                elif any(keyword in line for keyword in ['KPIs:', 'סטטיסטיקות:', 'ביצועים:']):
                    formatted += f"📊 {line}\n"
                elif any(keyword in line for keyword in ['הזמנות', 'מוצרים', 'ספקים']):
                    formatted += f"• {line}\n"
                else:
                    formatted += f"{line}\n"
        
        return formatted + "\n💡 שאל שאלות או בחר מהצד הימני!\n"

    def _load_smart_features(self):
        """טוען תכונות חכמות (הצעות ותובנות)"""
        self.dynamic_suggestions.setText("🔄 טוען הצעות חכמות...")
        
        # הפעל worker לתכונות חכמות
        self.suggestions_worker = SmartSuggestionsWorker(self.user_id)
        self.suggestions_worker.suggestions_ready.connect(self._update_smart_suggestions)
        self.suggestions_worker.insights_ready.connect(self._update_insights)
        self.suggestions_worker.failed.connect(self._handle_suggestions_failure)
        self.suggestions_worker.start()

    def _update_smart_suggestions(self, suggestions: List[str]):
        """עדכון הצעות חכמות"""
        self.smart_suggestions = suggestions
        self._reload_smart_questions()
        self.dynamic_suggestions.setText(f"💡 {len(suggestions)} הצעות חכמות")

    def _update_insights(self, insights: Dict):
        """עדכון תובנות עסקיות"""
        self.business_insights = insights
        self._display_insights()

    def _handle_suggestions_failure(self, error: str):
        """טיפול בכשל טעינת הצעות - fallback"""
        self.dynamic_suggestions.setText("⚠️ משתמש בהצעות בסיסיות")
        self._reload_basic_questions()

    def _reload_smart_questions(self):
        """טוען שאלות חכמות מהשרת"""
        # נקה שאלות קודמות
        for i in reversed(range(self.smart_layout.count())):
            w = self.smart_layout.itemAt(i).widget()
            if w: w.setParent(None)
        
        # הוסף קטגוריות שאלות
        categories = {
            "📊 מצב כללי": [],
            "💰 כספים": [],
            "📦 מוצרים/הזמנות": [],
            "🔧 פעולות": []
        }
        
        # סיווג השאלות לקטגוריות
        for suggestion in self.smart_suggestions:
            if any(word in suggestion for word in ["מצב", "סטטוס", "כמה"]):
                categories["📊 מצב כללי"].append(suggestion)
            elif any(word in suggestion for word in ["הכנס", "הוצא", "עלות", "מחיר", "רווח"]):
                categories["💰 כספים"].append(suggestion)
            elif any(word in suggestion for word in ["מוצר", "הזמנה", "מלאי", "ספק"]):
                categories["📦 מוצרים/הזמנות"].append(suggestion)
            else:
                categories["🔧 פעולות"].append(suggestion)
        
        # הצג קטגוריות עם שאלות
        for category, questions in categories.items():
            if questions:
                # כותרת קטגוריה
                cat_label = QLabel(category)
                cat_label.setStyleSheet("font-weight:bold; color:#047857; margin:5px 0px 2px 0px;")
                self.smart_layout.addWidget(cat_label)
                
                # שאלות בקטגוריה
                for q in questions[:4]:  # מגביל ל-4 שאלות לקטגוריה
                    btn = self._create_smart_question_button(q)
                    self.smart_layout.addWidget(btn)
        
        self.smart_layout.addStretch(1)

    def _reload_basic_questions(self):
        """טוען שאלות בסיסיות (fallback)"""
        for i in reversed(range(self.smart_layout.count())):
            w = self.smart_layout.itemAt(i).widget()
            if w: w.setParent(None)
            
        basic_label = QLabel("⚡ שאלות בסיסיות")
        basic_label.setStyleSheet("font-weight:bold; color:#047857; margin-bottom:5px;")
        self.smart_layout.addWidget(basic_label)
        
        qs = SUPPLIER_BASE_QUESTIONS if self.role == "Supplier" else OWNER_BASE_QUESTIONS
        for q in qs:
            btn = self._create_smart_question_button(q)
            self.smart_layout.addWidget(btn)
            
        self.smart_layout.addStretch(1)

    def _create_smart_question_button(self, question: str) -> QPushButton:
        """יוצר כפתור שאלה מעוצב"""
        btn = QPushButton(question)
        btn.setObjectName("Smart")
        btn.setProperty("class", "Smart")
        btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        btn.setMinimumHeight(40)
        btn.setWordWrap(True)
        btn.clicked.connect(lambda _, t=question: self._quick_clicked(t))
        return btn

    def _display_insights(self):
        """מציג תובנות עסקיות"""
        insights = self.business_insights
        if not insights:
            return
            
        insights_text = "📊 תובנות עסקיות מתקדמות\n\n"
        
        # התראות
        alerts = insights.get("alerts", [])
        if alerts:
            insights_text += "🚨 התראות:\n"
            for alert in alerts:
                insights_text += f"• {alert}\n"
            insights_text += "\n"
        
        # המלצות
        recommendations = insights.get("recommendations", [])
        if recommendations:
            insights_text += "💡 המלצות:\n"
            for rec in recommendations:
                insights_text += f"• {rec}\n"
            insights_text += "\n"
        
        # הזדמנויות
        opportunities = insights.get("opportunities", [])
        if opportunities:
            insights_text += "🎯 הזדמנויות:\n"
            for opp in opportunities:
                insights_text += f"• {opp}\n"
            insights_text += "\n"
        
        self.insights_display.setPlainText(insights_text)

    def _refresh_suggestions(self):
        """רענון הצעות חכמות"""
        if self.user_id:
            self._load_smart_features()

    def _refresh_insights(self):
        """רענון תובנות עסקיות"""
        if self.user_id:
            self._load_smart_features()

    def _quick_clicked(self, text: str):
        """לחיצה על שאלה מהירה"""
        self.input.setText(text)
        self._send_smart()

    def _send_smart(self):
        """שליחה חכמה עם תכונות מתקדמות"""
        if not self.user_id:
            QMessageBox.information(self, "חסר משתמש", "טען קודם פרופיל משתמש.")
            return
        if self._busy: 
            return
            
        q = self.input.text().strip()
        if not q: 
            return

        # הוסף שאלה לצ'אט עם timestamp
        timestamp = time.strftime("%H:%M")
        self.view.append(f"\n[{timestamp}] 🤔 {self.username}: {q}")
        self.input.clear()

        # הכן לתגובה מהמערכת החכמה
        self.view.append(f"<b>[{timestamp}] 🧠 AI חכם:</b> ")
        self.view.moveCursor(QTextCursor.End)

        # הפעל אינדיקטורים מתקדמים
        self._set_smart_busy(True, "🧠 AI חכם חושב...")
        self.progress.setVisible(True)
        self.progress.setValue(15)
        
        # timeout ארוך יותר למערכת חכמה
        self.timeout_timer.start(180000)  # 60 שניות

        # צור worker
        self.worker = FastStreamWorker(STREAM_URL, q, self.user_id)
        self.worker.chunk.connect(self._on_smart_chunk)
        self.worker.progress.connect(self._on_progress)
        self.worker.finished.connect(self._on_smart_finished)
        self.worker.failed.connect(self._on_smart_failed)
        self.worker.start()

    # 2) בכל chunk שמגיע - לאפס טיימר
    def _on_smart_chunk(self, txt: str):
        self.view.moveCursor(QTextCursor.End)
        self.view.insertPlainText(txt)
        self.view.ensureCursorVisible()
        self.ai_status.setText("🧠 מקבל תגובה חכמה.")
        self.timeout_timer.start(180000)  # איפוס הספירה בכל קבלת טקסט  :contentReference[oaicite:5]{index=5}

    def _on_progress(self, value: int):
        """עדכון התקדמות"""
        self.progress.setValue(value)

    def _on_smart_finished(self, dt: float):
        """סיום תגובה חכמה"""
        self.timeout_timer.stop()
        self.view.append(f" <span style='color:#047857;font-weight:bold'>🧠({dt:.1f}s)</span>")
        
        # הערכת איכות התגובה
        if dt < 3.0:
            quality_msg = "🚀 תגובה מהירה וחכמה!"
        elif dt < 6.0:
            quality_msg = "🧠 תגובה חכמה!"
        else:
            quality_msg = "✅ תגובה מקיפה"
            
        self.ai_status.setText(f"{quality_msg} {dt:.1f}s")
        
        # רענון הצעות אוטומטי (אם מופעל)
        if self.auto_suggestions.isChecked():
            self._refresh_suggestions()
            
        self._set_smart_busy(False)

    def _on_smart_failed(self, err: str):
        """טיפול בכשלים"""
        self.timeout_timer.stop()
        self.view.append(f"\n❌ {err}")
        
        # הצעות מתקדמות לפתרון
        if "זמן רב" in err or "timeout" in err.lower():
            self.view.append("\n💡 המערכת החכמה צריכה יותר זמן לשאלות מורכבות. נסה:")
            self.view.append("   • שאלה פשוטה יותר")
            self.view.append("   • חלק שאלה מורכבת לכמה שאלות קטנות")
        elif "חיבור" in err:
            self.view.append("\n💡 בדוק:")
            self.view.append("   • שהשרת FastAPI פועל")
            self.view.append("   • ששירות Ollama פועל")
            self.view.append("   • החיבור לאינטרנט תקין")
            
        self.ai_status.setText("❌ נכשל")
        self._set_smart_busy(False)

    def _force_stop(self):
        if hasattr(self, 'worker') and self.worker.isRunning():
            self.worker.terminate()
            self.view.append(f"\n⏰ התגובה הופסקה אחרי 3 דקות.")
            self.view.append("\n💡 אם זה קורה הרבה, כדאי לקצר את השאלה או לשפר אינדקסים/שאילתות.")
            self.ai_status.setText("⏰ הופסק")
            self._set_smart_busy(False)   # המקור קיים פה  :contentReference[oaicite:7]{index=7}


    def _set_smart_busy(self, busy: bool, msg: str = ""):
        """ניהול מצב עסוק חכם"""
        self._busy = busy
        self.send_btn.setEnabled(not busy)
        self.input.setEnabled(not busy)
        self.status.setText(msg if busy else "")
        
        if not busy:
            self.progress.setVisible(False)
            self.progress.setValue(0)
            
        QApplication.setOverrideCursor(Qt.WaitCursor if busy else Qt.ArrowCursor)

    def _clear_chat(self):
        """ניקוי צ'אט עם שמירת context"""
        if self.snapshot:
            self.view.setPlainText(self._format_snapshot())
        else:
            self.view.clear()
            self.view.setPlainText("🧠 צ'אט נוקה. טען משתמש מחדש כדי להתחיל.")

# ---- API Enhancement Functions ----

def fetch_smart_suggestions(user_id: int) -> List[str]:
    """מחזיר הצעות חכמות מהשרת החדש"""
    try:
        r = requests.get(f"{API_BASE_URL}/api/v1/ai/smart-suggestions", 
                        params={"user_id": user_id}, timeout=8)
        if r.status_code == 200:
            return r.json().get("suggestions", [])
    except:
        pass
    return []

def fetch_business_insights(user_id: int) -> dict:
    """מחזיר תובנות עסקיות"""
    try:
        r = requests.get(f"{API_BASE_URL}/api/v1/ai/business-insights", 
                        params={"user_id": user_id}, timeout=8)
        if r.status_code == 200:
            return r.json()
    except:
        pass
    return {}

# ---- Main Application ----

class SmartChatApp:
    """מחלקת האפליקציה החכמה"""
    
    def __init__(self):
        self.app = QApplication(sys.argv)
        self.window = EnhancedChatWindow()
        self._setup_app()
    
    def _setup_app(self):
        """הגדרת האפליקציה"""
        self.app.setApplicationName("Smart AI Chat")
        self.app.setApplicationVersion("2.0")
        self.app.setOrganizationName("Suppliers Management System")
        
        # הגדרת פונט גלובלי
        font = QFont("Arial", 12)
        self.app.setFont(font)
    
    def run(self):
        """הפעלת האפליקציה"""
        self.window.show()
        
        # הודעת פתיחה
        print("🧠 Smart AI Chat מופעל!")
        print("📋 תכונות חדשות:")
        print("  • הצעות שאלות חכמות")
        print("  • תובנות עסקיות אוטומטיות") 
        print("  • תגובות מתקדמות עם context עשיר")
        print("  • ניתוח ביצועים בזמן אמת")
        print("=" * 50)
        
        return self.app.exec()

# ---- Additional Utility Functions ----

def test_smart_features(user_id: int = 1):
    """פונקציית בדיקה למערכת החכמה"""
    print(f"🧪 בודק תכונות חכמות עבור משתמש {user_id}...")
    
    try:
        # בדיקת context
        ctx = fetch_ai_context(user_id)
        print(f"✅ Context: {ctx.get('role')} - {ctx.get('username')}")
        
        # בדיקת הצעות
        suggestions = fetch_smart_suggestions(user_id)
        print(f"✅ הצעות חכמות: {len(suggestions)} נמצאו")
        
        # בדיקת תובנות
        insights = fetch_business_insights(user_id)
        alerts_count = len(insights.get("alerts", []))
        recommendations_count = len(insights.get("recommendations", []))
        print(f"✅ תובנות: {alerts_count} התראות, {recommendations_count} המלצות")
        
        return True
        
    except Exception as e:
        print(f"❌ שגיאה בבדיקה: {e}")
        return False

if __name__ == "__main__":
    # אפשרות להפעלה עם user_id ספציפי
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        user_id = int(sys.argv[2]) if len(sys.argv) > 2 else 1
        test_smart_features(user_id)
    else:
        app = SmartChatApp()
        sys.exit(app.run())