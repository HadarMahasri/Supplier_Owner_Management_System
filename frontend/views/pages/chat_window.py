from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QTextEdit, QLineEdit, QPushButton, QLabel, QScrollArea,
    QFrame, QMessageBox, QProgressBar
)
from PySide6.QtCore import Qt, Signal, QThread, QTimer
from PySide6.QtGui import QFont, QPalette, QColor
import requests
import json
from typing import Dict
import os
import time

class FastChatRequestThread(QThread):
    """Thread מואץ לשליחת בקשות צ'אט עם נתוני משתמש"""
    response_received = Signal(dict)
    error_occurred = Signal(str)
    progress_updated = Signal(int)  # חדש: עדכון progress
    
    def __init__(self, user_id: int, message: str, api_url: str, timeout: int = 120, user_data: dict = None):
        super().__init__()
        self.user_id = user_id
        self.message = message
        self.api_url = api_url
        self.timeout = timeout  # הקטנתי מ-180 ל-120
        self.start_time = None
        self.user_data = user_data or {}

    def run(self):
        try:
            self.start_time = time.time()
            self.progress_updated.emit(10)  # התחלה
            
            # הכנת payload מובטל
            payload = {
                "user_id": self.user_id,
                "message": self.message,
                "user_context": self.user_data
            }
            
            self.progress_updated.emit(30)  # הכנת נתונים
            
            # שליחת בקשה עם headers מותאמים למהירות
            headers = {
                'Content-Type': 'application/json',
                'Accept': 'application/json',
                'Connection': 'keep-alive',
                'Accept-Encoding': 'gzip, deflate'
            }
            
            self.progress_updated.emit(50)  # שליחה
            
            response = requests.post(
                f"{self.api_url}/api/v1/gateway/chat/message",
                json=payload,
                headers=headers,
                timeout=self.timeout,
                stream=False  # ללא streaming למהירות
            )
            
            self.progress_updated.emit(80)  # קבלת תגובה
            
            if response.status_code == 200:
                response_data = response.json()
                response_data["response_time"] = round(time.time() - self.start_time, 2)
                response_data["from_cache"] = response_data.get("from_cache", False)
                
                self.progress_updated.emit(100)  # הושלם
                self.response_received.emit(response_data)
            else:
                self.error_occurred.emit(f"שגיאה בשרת: {response.status_code}")
                
        except requests.exceptions.Timeout:
            self.error_occurred.emit("התגובה לוקחת יותר מדי זמן - נסה שוב")
        except requests.exceptions.ConnectionError:
            self.error_occurred.emit("בעיית חיבור לשרת - בדוק את החיבור")
        except Exception as e:
            self.error_occurred.emit(f"שגיאת תקשורת: {str(e)}")

class FastTypingIndicator(QLabel):
    """אינדיקטור כתיבה מהיר יותר עם אנימציה חלקה"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.base_text = "כותב תשובה"
        self.dots = 0
        self.max_dots = 3
        
        # Timer מהיר יותר
        self.animation_timer = QTimer()
        self.animation_timer.timeout.connect(self.update_dots)
        self.animation_timer.start(300)  # הקטנתי מ-500 ל-300
        
        self.setStyleSheet("""
            color: #6b7280;
            font-size: 14px;
            font-style: italic;
            padding: 5px;
            background-color: rgba(243, 244, 246, 0.8);
            border-radius: 8px;
        """)
        
        self.update_dots()
    
    def update_dots(self):
        self.dots = (self.dots + 1) % (self.max_dots + 1)
        dots_str = "." * self.dots
        self.setText(f"{self.base_text}{dots_str}")
    
    def stop_animation(self):
        if self.animation_timer.isActive():
            self.animation_timer.stop()

class FastProgressBar(QProgressBar):
    """Progress bar מותאם למהירות"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("""
            QProgressBar {
                border: 1px solid #e1e8ed;
                border-radius: 8px;
                text-align: center;
                background-color: #f8f9fa;
                height: 6px;
            }
            QProgressBar::chunk {
                background-color: #667eea;
                border-radius: 6px;
            }
        """)
        self.setTextVisible(False)
        self.setMaximum(100)
        self.hide()
    
    def start_progress(self):
        self.setValue(0)
        self.show()
    
    def stop_progress(self):
        self.setValue(100)
        QTimer.singleShot(500, self.hide)

class ChatBubble(QFrame):
    """בועת צ'אט מותאמת"""
    def __init__(self, message: str, is_user: bool = True, response_time: float = None, from_cache: bool = False):
        super().__init__()
        self.setup_ui(message, is_user, response_time, from_cache)
    
    def setup_ui(self, message: str, is_user: bool, response_time: float = None, from_cache: bool = False):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 5, 10, 5)
        
        bubble = QFrame()
        bubble.setMaximumWidth(500)  # הגדלתי מ-450 ל-500
        bubble.setObjectName("userBubble" if is_user else "botBubble")
        
        bubble_layout = QVBoxLayout(bubble)
        bubble_layout.setContentsMargins(15, 10, 15, 10)
        
        # תווית עם ההודעה
        message_label = QLabel(message)
        message_label.setWordWrap(True)
        message_label.setAlignment(Qt.AlignRight if is_user else Qt.AlignLeft)
        bubble_layout.addWidget(message_label)
        
        # הוספת זמן תגובה ומידע על מטמון
        if not is_user and response_time is not None:
            info_parts = [f"נענה תוך {response_time} שניות"]
            
            if from_cache:
                info_parts.append("(מטמון מהיר)")
            
            time_label = QLabel(" • ".join(info_parts))
            time_label.setStyleSheet("""
                color: #9ca3af;
                font-size: 11px;
                font-style: italic;
                margin-top: 5px;
            """)
            time_label.setAlignment(Qt.AlignLeft)
            bubble_layout.addWidget(time_label)
        
        # יישור הבועה
        if is_user:
            layout.addStretch()
            layout.addWidget(bubble)
        else:
            layout.addWidget(bubble)
            layout.addStretch()

class FastChatWindow(QMainWindow):
    """חלון הצ'אט הראשי - גרסה מואצת"""
    
    def __init__(self, user_id: int, api_url: str = "http://localhost:8000"):
        super().__init__()
        self.user_id = user_id
        self.api_url = api_url
        self.typing_indicator = None
        self.progress_bar = None
        self.chat_thread = None
        
        # הגדרות מהירות
        self.api_url = api_url or os.getenv("API_BASE_URL", "http://localhost:8000").rstrip("/")
        self.chat_timeout = int(os.getenv("CHAT_UI_TIMEOUT", "120"))  # הקטנתי מ-180 ל-120
        
        # מטמון הודעות למהירות
        self.message_cache = {}
        
        self.setup_ui()
        self.setup_styles()
        self.load_user_info()
        
        # חימום חיבור
        self.warm_up_connection()
    
    def warm_up_connection(self):
        """חימום חיבור לשרת למהירות"""
        try:
            requests.get(f"{self.api_url}/health", timeout=3)
        except:
            pass  # לא משנה אם נכשל
    
    def setup_ui(self):
        """הגדרת ממשק המשתמש מותאם למהירות"""
        self.setWindowTitle("צ'אט עם העוזר הדיגיטלי - מהיר")
        self.setMinimumSize(550, 650)
        self.resize(700, 800)
        
        # Widget מרכזי
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # כותרת מותאמת
        header = QFrame()
        header.setObjectName("header")
        header.setFixedHeight(90)
        
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(20, 10, 20, 10)
        
        self.title_label = QLabel("🚀 העוזר הדיגיטלי המהיר שלך")
        self.title_label.setObjectName("titleLabel")
        
        self.user_info_label = QLabel("טוען מידע...")
        self.user_info_label.setObjectName("userInfoLabel")
        
        # Progress bar
        self.progress_bar = FastProgressBar()
        
        header_layout.addWidget(self.title_label)
        header_layout.addWidget(self.user_info_label)
        header_layout.addWidget(self.progress_bar)
        
        main_layout.addWidget(header)
        
        # אזור ההודעות עם אופטימיזציה
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        
        # אופטימיזציה לביצועים
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area.viewport().setAutoFillBackground(False)
        
        self.messages_container = QWidget()
        self.messages_layout = QVBoxLayout(self.messages_container)
        self.messages_layout.setContentsMargins(10, 10, 10, 10)
        self.messages_layout.setSpacing(8)  # הקטנתי מ-12 ל-8
        
        scroll_area.setWidget(self.messages_container)
        main_layout.addWidget(scroll_area, 1)
        
        # אזור הכתיבה מותאם
        input_frame = QFrame()
        input_frame.setObjectName("inputFrame")
        input_frame.setFixedHeight(70)  # הקטנתי מ-80 ל-70
        
        input_layout = QHBoxLayout(input_frame)
        input_layout.setContentsMargins(15, 10, 15, 10)
        input_layout.setSpacing(10)
        
        self.message_input = QLineEdit()
        self.message_input.setObjectName("messageInput")
        self.message_input.setPlaceholderText("כתוב את שאלתך כאן... (Enter לשליחה)")
        self.message_input.returnPressed.connect(self.send_message_fast)
        
        self.send_button = QPushButton("שלח")
        self.send_button.setObjectName("sendButton")
        self.send_button.clicked.connect(self.send_message_fast)
        
        # כפתור ניקוי מטמון
        self.clear_cache_button = QPushButton("נקה")
        self.clear_cache_button.setObjectName("clearButton")
        self.clear_cache_button.clicked.connect(self.clear_chat_cache)
        self.clear_cache_button.setMaximumWidth(60)
        
        input_layout.addWidget(self.message_input)
        input_layout.addWidget(self.clear_cache_button)
        input_layout.addWidget(self.send_button)
        
        main_layout.addWidget(input_frame)
        
        # הוספת הודעת ברוכים הבאים
        self.add_welcome_message()
    
    def setup_styles(self):
        """הגדרת העיצוב עם אופטימיזציה"""
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f5f7fa;
            }
            
            QFrame#header {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #4f46e5, stop:1 #7c3aed);
                border: none;
            }
            
            QLabel#titleLabel {
                color: white;
                font-size: 18px;
                font-weight: bold;
            }
            
            QLabel#userInfoLabel {
                color: #e8f4fd;
                font-size: 11px;
            }
            
            QFrame#inputFrame {
                background-color: white;
                border-top: 1px solid #e1e8ed;
                border-radius: 8px;
                margin: 3px;
            }
            
            QLineEdit#messageInput {
                border: 2px solid #e1e8ed;
                border-radius: 16px;
                padding: 10px 16px;
                font-size: 14px;
                background-color: #f8f9fa;
            }
            
            QLineEdit#messageInput:focus {
                border-color: #4f46e5;
                background-color: white;
                outline: none;
            }
            
            QPushButton#sendButton {
                background-color: #4f46e5;
                color: white;
                border: none;
                border-radius: 16px;
                padding: 10px 20px;
                font-weight: bold;
                font-size: 14px;
                min-width: 70px;
            }
            
            QPushButton#sendButton:hover {
                background-color: #4338ca;
            }
            
            QPushButton#sendButton:pressed {
                background-color: #3730a3;
            }
            
            QPushButton#sendButton:disabled {
                background-color: #9ca3af;
            }
            
            QPushButton#clearButton {
                background-color: #ef4444;
                color: white;
                border: none;
                border-radius: 16px;
                padding: 10px;
                font-size: 12px;
            }
            
            QPushButton#clearButton:hover {
                background-color: #dc2626;
            }
            
            QFrame[objectName="userBubble"] {
                background-color: #4f46e5;
                border-radius: 16px;
                margin: 2px;
            }
            
            QFrame[objectName="userBubble"] QLabel {
                color: white;
                font-size: 14px;
                line-height: 1.4;
            }
            
            QFrame[objectName="botBubble"] {
                background-color: white;
                border: 1px solid #e1e8ed;
                border-radius: 16px;
                margin: 2px;
            }
            
            QFrame[objectName="botBubble"] QLabel {
                color: #1a202c;
                font-size: 14px;
                line-height: 1.4;
            }
            
            QScrollArea {
                border: none;
                background-color: transparent;
            }
        """)
    
    def load_user_info(self):
        """טעינת מידע המשתמש"""
        try:
            self.user_info_label.setText(f"משתמש ID: {self.user_id} • מצב: מוכן")
        except Exception:
            self.user_info_label.setText("משתמש לא מזוהה")
    
    def add_welcome_message(self):
        """הוספת הודעת ברוכים הבאים מקוצרת"""
        welcome_text = """שלום! אני העוזר הדיגיטלי המהיר שלך במערכת הספקים.

🚀 אני כאן כדי לעזור עם:
• ניהול מוצרים ומלאי
• ביצוע והזמנות ומעקב
• יצירת קשרים עם ספקים/בעלי חנויות
• שאלות כלליות על המערכת

פשוט כתוב את שאלתך ואני אענה במהירות!"""
        
        bubble = ChatBubble(welcome_text.strip(), is_user=False)
        self.messages_layout.addWidget(bubble)
    
    def send_message_fast(self):
        """שליחת הודעה מהירה"""
        message = self.message_input.text().strip()
        if not message:
            return
        
        # בדיקת מטמון מקומי
        cache_key = f"{self.user_id}:{hash(message.lower())}"
        if cache_key in self.message_cache:
            cached_response = self.message_cache[cache_key]
            if time.time() - cached_response["timestamp"] < 300:  # 5 דקות
                self.show_cached_response(message, cached_response["response"])
                return
        
        # הוספת ההודעה למערכת
        user_bubble = ChatBubble(message, is_user=True)
        self.messages_layout.addWidget(user_bubble)
        
        # ניקוי שדה הקלט
        self.message_input.clear()
        
        # נעילת הכפתור בזמן השליחה
        self.send_button.setEnabled(False)
        self.send_button.setText("שולח...")
        
        # התחלת progress bar
        self.progress_bar.start_progress()
        
        # הוספת אינדיקטור כתיבה
        self.add_typing_indicator()
        
        # גלילה למטה
        self.scroll_to_bottom_fast()
        
        # שליחת הבקשה
        self.chat_thread = FastChatRequestThread(
            self.user_id, 
            message, 
            self.api_url, 
            timeout=self.chat_timeout
        )
        self.chat_thread.response_received.connect(self.on_response_received_fast)
        self.chat_thread.error_occurred.connect(self.on_error_occurred_fast)
        self.chat_thread.progress_updated.connect(self.progress_bar.setValue)
        self.chat_thread.start()
    
    def add_typing_indicator(self):
        """הוספת אינדיקטור כתיבה"""
        typing_layout = QHBoxLayout()
        typing_frame = QFrame()
        typing_frame.setObjectName("botBubble")
        typing_frame.setMaximumWidth(180)
        
        frame_layout = QVBoxLayout(typing_frame)
        frame_layout.setContentsMargins(15, 8, 15, 8)
        
        self.typing_indicator = FastTypingIndicator()
        frame_layout.addWidget(self.typing_indicator)
        
        typing_layout.addWidget(typing_frame)
        typing_layout.addStretch()
        
        typing_container = QWidget()
        typing_container.setLayout(typing_layout)
        self.messages_layout.addWidget(typing_container)
    
    def show_cached_response(self, message: str, response: str):
        """הצגת תשובה מהמטמון"""
        user_bubble = ChatBubble(message, is_user=True)
        self.messages_layout.addWidget(user_bubble)
        
        cached_bubble = ChatBubble(f"{response}\n\n💡 תשובה מהמטמון המהיר", 
                                 is_user=False, response_time=0.1, from_cache=True)
        self.messages_layout.addWidget(cached_bubble)
        
        self.scroll_to_bottom_fast()
    
    def on_response_received_fast(self, response: dict):
        """טיפול בתגובה מהשרת"""
        # עצירת progress bar
        self.progress_bar.stop_progress()
        
        # הסרת אינדיקטור הכתיבה
        self.remove_typing_indicator()
        
        # הוספת התשובה
        if response.get("success"):
            bot_response = response.get("response", "מצטער, לא קיבלתי תשובה.")
            response_time = response.get("response_time", 0)
            from_cache = response.get("from_cache", False)
            
            # הוספת אינדיקטור מטמון
            if from_cache:
                bot_response += "\n\n⚡ תשובה מהמטמון"
            
            bot_bubble = ChatBubble(bot_response, is_user=False, 
                                  response_time=response_time, from_cache=from_cache)
            self.messages_layout.addWidget(bot_bubble)
            
            # שמירה במטמון מקומי
            if not from_cache:  # רק אם זה לא בא ממטמון כבר
                cache_key = f"{self.user_id}:{hash(self.message_input.text().lower() if hasattr(self, 'last_message') else '')}"
                self.message_cache[cache_key] = {
                    "response": bot_response,
                    "timestamp": time.time()
                }
        else:
            error_message = f"שגיאה: {response.get('message', 'שגיאה לא ידועה')}"
            error_bubble = ChatBubble(error_message, is_user=False)
            self.messages_layout.addWidget(error_bubble)
        
        # החזרת הכפתור למצב רגיל
        self.send_button.setEnabled(True)
        self.send_button.setText("שלח")
        
        # גלילה למטה
        self.scroll_to_bottom_fast()
    
    def on_error_occurred_fast(self, error: str):
        """טיפול בשגיאה"""
        # עצירת progress bar
        self.progress_bar.stop_progress()
        
        # הסרת אינדיקטור הכתיבה
        self.remove_typing_indicator()
        
        # הוספת הודעת שגיאה
        error_message = f"שגיאה בתקשורת: {error}\n\nנסה שוב או פנה לתמיכה."
        error_bubble = ChatBubble(error_message, is_user=False)
        self.messages_layout.addWidget(error_bubble)
        
        # החזרת הכפתור למצב רגיל
        self.send_button.setEnabled(True)
        self.send_button.setText("שלח")
        
        # גלילה למטה
        self.scroll_to_bottom_fast()
    
    def remove_typing_indicator(self):
        """הסרת אינדיקטור הכתיבה"""
        if self.typing_indicator:
            last_item = self.messages_layout.itemAt(self.messages_layout.count() - 1)
            if last_item:
                widget = last_item.widget()
                if widget:
                    self.messages_layout.removeWidget(widget)
                    widget.setParent(None)
            
            self.typing_indicator.stop_animation()
            self.typing_indicator = None
    
    def clear_chat_cache(self):
        """ניקוי מטמון הצ'אט"""
        self.message_cache.clear()
        
        # הוספת הודעה על ניקוי
        clear_bubble = ChatBubble("🗑️ המטמון נוקה בהצלחה", is_user=False, response_time=0.0)
        self.messages_layout.addWidget(clear_bubble)
        
        self.scroll_to_bottom_fast()
    
    def scroll_to_bottom_fast(self):
        """גלילה מהירה למטה"""
        QTimer.singleShot(50, self._do_scroll_fast)  # הקטנתי מ-100 ל-50
    
    def _do_scroll_fast(self):
        scroll_area = self.centralWidget().findChild(QScrollArea)
        if scroll_area:
            scroll_bar = scroll_area.verticalScrollBar()
            scroll_bar.setValue(scroll_bar.maximum())

# שינוי שם הקלאס לתאימות לאחור
ChatWindow = FastChatWindow

# דוגמה לשימוש
if __name__ == "__main__":
    from PySide6.QtWidgets import QApplication
    import sys
    
    app = QApplication(sys.argv)
    
    # בדיקה פשוטה - צריך לקבל user_id אמיתי
    chat_window = FastChatWindow(user_id=1)
    chat_window.show()
    
    sys.exit(app.exec())