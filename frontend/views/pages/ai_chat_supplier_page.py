# frontend/views/pages/ai_chat_supplier_page.py
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QFrame, QScrollArea, QLineEdit, QMessageBox, QProgressBar
)
from PySide6.QtCore import Qt, Signal, QThread, QTimer
from PySide6.QtGui import QFont, QPalette, QColor
import requests
import json
from typing import Dict
import os
import time

class ChatRequestThread(QThread):
    """Thread מותאם לשליחת בקשות צ'אט עם נתוני משתמש"""
    response_received = Signal(dict)
    error_occurred = Signal(str)
    progress_updated = Signal(int)
    
    def __init__(self, user_id: int, message: str, api_url: str, timeout: int = 120, user_data: dict = None):
        super().__init__()
        self.user_id = user_id
        self.message = message
        self.api_url = api_url
        self.timeout = timeout
        self.start_time = None
        self.user_data = user_data or {}

    def run(self):
        try:
            self.start_time = time.time()
            self.progress_updated.emit(10)
            
            payload = {
                "user_id": self.user_id,
                "message": self.message,
                "user_context": self.user_data
            }
            
            self.progress_updated.emit(30)
            
            headers = {
                'Content-Type': 'application/json',
                'Accept': 'application/json',
                'Connection': 'keep-alive',
                'Accept-Encoding': 'gzip, deflate'
            }
            
            self.progress_updated.emit(50)
            
            response = requests.post(
                f"{self.api_url}/api/v1/gateway/chat/message",
                json=payload,
                headers=headers,
                timeout=self.timeout,
                stream=False
            )
            
            self.progress_updated.emit(80)
            
            if response.status_code == 200:
                response_data = response.json()
                response_data["response_time"] = round(time.time() - self.start_time, 2)
                response_data["from_cache"] = response_data.get("from_cache", False)
                
                self.progress_updated.emit(100)
                self.response_received.emit(response_data)
            else:
                self.error_occurred.emit(f"שגיאה בשרת: {response.status_code}")
                
        except requests.exceptions.Timeout:
            self.error_occurred.emit("התגובה לוקחת יותר מדי זמן - נסה שוב")
        except requests.exceptions.ConnectionError:
            self.error_occurred.emit("בעיית חיבור לשרת - בדוק את החיבור")
        except Exception as e:
            self.error_occurred.emit(f"שגיאת תקשורת: {str(e)}")

class TypingIndicator(QLabel):
    """אינדיקטור כתיבה מהיר יותר עם אנימציה חלקה"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.base_text = "כותב תשובה"
        self.dots = 0
        self.max_dots = 3
        
        self.animation_timer = QTimer()
        self.animation_timer.timeout.connect(self.update_dots)
        self.animation_timer.start(300)
        
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

class ChatProgressBar(QProgressBar):
    """Progress bar מותאם למהירות"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("""
            QProgressBar {
                border: 1px solid #dcfce7;
                border-radius: 8px;
                text-align: center;
                background-color: #f0fdf4;
                height: 6px;
            }
            QProgressBar::chunk {
                background-color: #10b981;
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
        bubble.setMaximumWidth(500)
        bubble.setObjectName("userBubble" if is_user else "botBubble")
        
        bubble_layout = QVBoxLayout(bubble)
        bubble_layout.setContentsMargins(15, 10, 15, 10)
        
        message_label = QLabel(message)
        message_label.setWordWrap(True)
        message_label.setAlignment(Qt.AlignRight if is_user else Qt.AlignLeft)
        bubble_layout.addWidget(message_label)
        
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
        
        if is_user:
            layout.addStretch()
            layout.addWidget(bubble)
        else:
            layout.addWidget(bubble)
            layout.addStretch()

class AIChatSupplierPage(QWidget):
    """עמוד צ'אט AI בעיצוב ירוק לספק"""
    
    def __init__(self, user_data: Dict, api_url: str = None):
        super().__init__()
        self.user_data = user_data
        self.user_id = user_data.get('id', 1)
        self.api_url = api_url or os.getenv("API_BASE_URL", "http://localhost:8000")
        self.typing_indicator = None
        self.progress_bar = None
        self.chat_thread = None
        self.chat_timeout = int(os.getenv("CHAT_UI_TIMEOUT", "120"))
        self.message_cache = {}
        
        self.setup_ui()
        self.setup_styles()
        self.add_welcome_message()
        QTimer.singleShot(0, self.warm_up_connection)  # להריץ אחרי שהמסך עלה

    
    def warm_up_connection(self):
        """חימום חיבור לשרת למהירות"""
        try:
            requests.get(f"{self.api_url}/health", timeout=3)
        except:
            pass
    
    def setup_ui(self):
        """הגדרת ממשק המשתמש מותאם למהירות"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(16)
        
        # כותרת העמוד
        header = QFrame()
        header.setObjectName("chatHeader")
        header.setFixedHeight(80)
        
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(20, 10, 20, 10)
        
        title_label = QLabel("🤖 שיחה עם העוזר הדיגיטלי")
        title_label.setObjectName("chatTitle")
        
        user_name = self.user_data.get('contact_name', 'ספק')
        company_name = self.user_data.get('company_name', '')
        info_text = f"שלום {user_name}"
        if company_name:
            info_text += f" מ{company_name}"
        
        info_label = QLabel(info_text)
        info_label.setObjectName("chatInfo")
        
        # Progress bar
        self.progress_bar = ChatProgressBar()
        
        header_layout.addWidget(title_label)
        header_layout.addWidget(info_label)
        header_layout.addWidget(self.progress_bar)
        
        main_layout.addWidget(header)
        
        # אזור ההודעות עם אופטימיזציה
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.viewport().setAutoFillBackground(False)
        
        self.messages_container = QWidget()
        self.messages_layout = QVBoxLayout(self.messages_container)
        self.messages_layout.setContentsMargins(10, 10, 10, 10)
        self.messages_layout.setSpacing(8)
        
        scroll_area.setWidget(self.messages_container)
        main_layout.addWidget(scroll_area, 1)
        
        # אזור הכתיבה מותאם
        input_frame = QFrame()
        input_frame.setObjectName("inputFrame")
        input_frame.setFixedHeight(70)
        
        input_layout = QHBoxLayout(input_frame)
        input_layout.setContentsMargins(15, 10, 15, 10)
        input_layout.setSpacing(10)
        
        self.message_input = QLineEdit()
        self.message_input.setObjectName("messageInput")
        self.message_input.setPlaceholderText("כתוב את שאלתך כאן... (Enter לשליחה)")
        self.message_input.returnPressed.connect(self.send_message)
        
        self.send_button = QPushButton("שלח")
        self.send_button.setObjectName("sendButton")
        self.send_button.clicked.connect(self.send_message)
        
        # כפתור ניקוי מטמון
        self.clear_cache_button = QPushButton("נקה")
        self.clear_cache_button.setObjectName("clearButton")
        self.clear_cache_button.clicked.connect(self.clear_chat_cache)
        self.clear_cache_button.setMaximumWidth(60)
        
        input_layout.addWidget(self.message_input)
        input_layout.addWidget(self.clear_cache_button)
        input_layout.addWidget(self.send_button)
        
        main_layout.addWidget(input_frame)
    
    def setup_styles(self):
        """הגדרת העיצוב עם גווני ירוק לספק"""
        self.setStyleSheet("""
            AIChatSupplierPage {
                background-color: #f0fdf4;
            }
            
            QFrame#chatHeader {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #10b981, stop:1 #047857);
                border: none;
                border-radius: 12px;
            }
            
            QLabel#chatTitle {
                color: white;
                font-size: 18px;
                font-weight: bold;
            }
            
            QLabel#chatInfo {
                color: #a7f3d0;
                font-size: 12px;
            }
            
            QFrame#inputFrame {
                background-color: white;
                border: 1px solid #dcfce7;
                border-radius: 12px;
                margin: 3px;
            }
            
            QLineEdit#messageInput {
                border: 2px solid #dcfce7;
                border-radius: 16px;
                padding: 10px 16px;
                font-size: 14px;
                background-color: #f0fdf4;
            }
            
            QLineEdit#messageInput:focus {
                border-color: #10b981;
                background-color: white;
                outline: none;
            }
            
            QPushButton#sendButton {
                background-color: #10b981;
                color: white;
                border: none;
                border-radius: 16px;
                padding: 10px 20px;
                font-weight: bold;
                font-size: 14px;
                min-width: 70px;
            }
            
            QPushButton#sendButton:hover {
                background-color: #059669;
            }
            
            QPushButton#sendButton:pressed {
                background-color: #047857;
            }
            
            QPushButton#sendButton:disabled {
                background-color: #9ca3af;
            }
            
            QPushButton#clearButton {
                background-color: #dc2626;
                color: white;
                border: none;
                border-radius: 16px;
                padding: 10px;
                font-size: 12px;
            }
            
            QPushButton#clearButton:hover {
                background-color: #b91c1c;
            }
            
            QFrame[objectName="userBubble"] {
                background-color: #10b981;
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
                border: 1px solid #dcfce7;
                border-radius: 16px;
                margin: 2px;
            }
            
            QFrame[objectName="botBubble"] QLabel {
                color: #1e293b;
                font-size: 14px;
                line-height: 1.4;
            }
            
            QScrollArea {
                border: none;
                background-color: transparent;
            }
        """)
    
    def add_welcome_message(self):
        """הוספת הודעת ברוכים הבאים מקוצרת לספק"""
        user_name = self.user_data.get('contact_name', 'ספק')
        welcome_text = f"""שלום {user_name}! אני העוזר הדיגיטלי המהיר שלך במערכת הספקים.

🚀 אני כאן כדי לעזור עם:
• ניהול הזמנות ומעקב סטטוס
• ניהול מוצרים ומלאי
• יצירת קשרים עם בעלי חנויות
• דוחות מכירות ומעקב
• שאלות כלליות על המערכת

פשוט כתוב את שאלתך ואני אענה במהירות!"""
        
        bubble = ChatBubble(welcome_text.strip(), is_user=False)
        self.messages_layout.addWidget(bubble)
    
    def send_message(self):
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
        self.scroll_to_bottom()
        
        # שליחת הבקשה
        self.chat_thread = ChatRequestThread(
            self.user_id, 
            message, 
            self.api_url, 
            timeout=self.chat_timeout,
            user_data=self.user_data
        )
        self.chat_thread.response_received.connect(self.on_response_received)
        self.chat_thread.error_occurred.connect(self.on_error_occurred)
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
        
        self.typing_indicator = TypingIndicator()
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
        
        self.scroll_to_bottom()
    
    def on_response_received(self, response: dict):
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
            if not from_cache:
                cache_key = f"{self.user_id}:{hash(self.last_message.lower() if hasattr(self, 'last_message') else '')}"
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
        self.scroll_to_bottom()
    
    def on_error_occurred(self, error: str):
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
        self.scroll_to_bottom()
    
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
        
        self.scroll_to_bottom()
    
    def scroll_to_bottom(self):
        """גלילה מהירה למטה"""
        QTimer.singleShot(50, self._do_scroll)
    
    def _do_scroll(self):
        scroll_area = self.parent()
        while scroll_area and not isinstance(scroll_area, QScrollArea):
            scroll_area = scroll_area.parent()
        
        if scroll_area and isinstance(scroll_area, QScrollArea):
            scroll_bar = scroll_area.verticalScrollBar()
            scroll_bar.setValue(scroll_bar.maximum())