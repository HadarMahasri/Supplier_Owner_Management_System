from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QTextEdit, QLineEdit, QPushButton, QLabel, QScrollArea,
    QFrame, QMessageBox
)
from PySide6.QtCore import Qt, Signal, QThread, QTimer
from PySide6.QtGui import QFont, QPalette, QColor
import requests
import json
from typing import Dict
import os
import time

class ChatRequestThread(QThread):
    """Thread לשליחת בקשות צ'אט עם נתוני משתמש"""
    response_received = Signal(dict)
    error_occurred = Signal(str)
    
    def __init__(self, user_id: int, message: str, api_url: str, timeout: int = 180, user_data: dict = None):
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
            # שליחת בקשה עם נתוני המשתמש
            payload = {
                "user_id": self.user_id,
                "message": self.message,
                "user_context": self.user_data  # נתוני המשתמש המלאים
            }
            
            response = requests.post(
                f"{self.api_url}/api/v1/gateway/chat/message",
                json=payload,
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                # הוספת זמן תגובה לנתונים
                response_data = response.json()
                response_data["response_time"] = round(time.time() - self.start_time, 2)
                self.response_received.emit(response_data)
            else:
                self.error_occurred.emit(f"שגיאה בשרת: {response.status_code}")
                
        except Exception as e:
            self.error_occurred.emit(f"שגיאת תקשורת: {str(e)}")

class TypingIndicator(QLabel):
    """אינדיקטור כתיבה עם 3 נקודות מתנועעות"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.base_text = "כותב תשובה"
        self.dots = 0
        self.max_dots = 3
        
        # Timer לאנימציה
        self.animation_timer = QTimer()
        self.animation_timer.timeout.connect(self.update_dots)
        self.animation_timer.start(500)  # עדכון כל חצי שנייה
        
        # הגדרת סטיילינג
        self.setStyleSheet("""
            color: #6b7280;
            font-size: 14px;
            font-style: italic;
            padding: 5px;
        """)
        
        self.update_dots()
    
    def update_dots(self):
        """עדכון מספר הנקודות"""
        self.dots = (self.dots + 1) % (self.max_dots + 1)
        dots_str = "." * self.dots
        self.setText(f"{self.base_text}{dots_str}")
    
    def stop_animation(self):
        """עצירת האנימציה"""
        if self.animation_timer.isActive():
            self.animation_timer.stop()

class ChatBubble(QFrame):
    """בועת צ'אט"""
    def __init__(self, message: str, is_user: bool = True, response_time: float = None):
        super().__init__()
        self.setup_ui(message, is_user, response_time)
    
    def setup_ui(self, message: str, is_user: bool, response_time: float = None):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 5, 10, 5)
        
        # יצירת הבועה
        bubble = QFrame()
        bubble.setMaximumWidth(450)  # הגדלתי קצת לטקסט ארוך יותר
        bubble.setObjectName("userBubble" if is_user else "botBubble")
        
        bubble_layout = QVBoxLayout(bubble)
        bubble_layout.setContentsMargins(15, 10, 15, 10)
        
        # תווית עם ההודעה
        message_label = QLabel(message)
        message_label.setWordWrap(True)
        message_label.setAlignment(Qt.AlignRight if is_user else Qt.AlignLeft)
        bubble_layout.addWidget(message_label)
        
        # הוספת זמן תגובה אם זה הודעת בוט
        if not is_user and response_time is not None:
            time_label = QLabel(f"נענה תוך {response_time} שניות")
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

class ResponseTimer(QLabel):
    """מונה זמן תגובה"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.start_time = None
        self.elapsed_seconds = 0
        
        # Timer לעדכון הזמן
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_time)
        
        # הגדרת סטיילינג
        self.setStyleSheet("""
            background-color: #f3f4f6;
            color: #4b5563;
            border: 1px solid #e5e7eb;
            border-radius: 15px;
            padding: 5px 10px;
            font-size: 12px;
            font-weight: 500;
        """)
        
        self.setAlignment(Qt.AlignCenter)
        self.hide()  # מוסתר בתחילה
    
    def start_timer(self):
        """התחלת מדידת הזמן"""
        self.start_time = time.time()
        self.elapsed_seconds = 0
        self.show()
        self.timer.start(100)  # עדכון כל עשירית שנייה
        self.update_time()
    
    def stop_timer(self):
        """עצירת המדידה"""
        if self.timer.isActive():
            self.timer.stop()
        self.hide()
    
    def update_time(self):
        """עדכון התצוגה"""
        if self.start_time:
            self.elapsed_seconds = time.time() - self.start_time
            self.setText(f"⏱️ {self.elapsed_seconds:.1f} שניות")

class ChatWindow(QMainWindow):
    """חלון הצ'אט הראשי"""
    
    def __init__(self, user_id: int, api_url: str = "http://localhost:8000"):
        super().__init__()
        self.user_id = user_id
        self.api_url = api_url
        self.typing_indicator = None
        self.response_timer = None
        
        self.setup_ui()
        self.setup_styles()
        self.load_user_info()
        
        # הגדרות API
        self.api_url = api_url or os.getenv("API_BASE_URL", "http://localhost:8000").rstrip("/")
        self.chat_timeout = int(os.getenv("CHAT_UI_TIMEOUT", "180"))
    
    def setup_ui(self):
        """הגדרת ממשק המשתמש"""
        self.setWindowTitle("צ'אט עם העוזר הדיגיטלי")
        self.setMinimumSize(500, 600)
        self.resize(650, 750)
        
        # Widget מרכזי
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # כותרת
        header = QFrame()
        header.setObjectName("header")
        header.setFixedHeight(80)
        
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(20, 10, 20, 10)
        
        self.title_label = QLabel("💬 העוזר הדיגיטלי שלך")
        self.title_label.setObjectName("titleLabel")
        
        self.user_info_label = QLabel("טוען מידע...")
        self.user_info_label.setObjectName("userInfoLabel")
        
        header_layout.addWidget(self.title_label)
        header_layout.addWidget(self.user_info_label)
        
        main_layout.addWidget(header)
        
        # אזור ההודעות
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        
        self.messages_container = QWidget()
        self.messages_layout = QVBoxLayout(self.messages_container)
        self.messages_layout.setContentsMargins(10, 10, 10, 10)
        self.messages_layout.setSpacing(12)
        
        scroll_area.setWidget(self.messages_container)
        main_layout.addWidget(scroll_area, 1)
        
        # אזור הכתיבה עם מונה זמן
        input_section = QVBoxLayout()
        input_section.setSpacing(5)
        
        # מונה זמן תגובה
        self.response_timer = ResponseTimer()
        timer_layout = QHBoxLayout()
        timer_layout.addStretch()
        timer_layout.addWidget(self.response_timer)
        timer_layout.addStretch()
        input_section.addLayout(timer_layout)
        
        # שורת הקלט
        input_frame = QFrame()
        input_frame.setObjectName("inputFrame")
        input_frame.setFixedHeight(80)
        
        input_layout = QHBoxLayout(input_frame)
        input_layout.setContentsMargins(15, 15, 15, 15)
        input_layout.setSpacing(10)
        
        self.message_input = QLineEdit()
        self.message_input.setObjectName("messageInput")
        self.message_input.setPlaceholderText("כתוב את שאלתך כאן...")
        self.message_input.returnPressed.connect(self.send_message)
        
        self.send_button = QPushButton("שלח")
        self.send_button.setObjectName("sendButton")
        self.send_button.clicked.connect(self.send_message)
        
        input_layout.addWidget(self.message_input)
        input_layout.addWidget(self.send_button)
        
        input_section.addWidget(input_frame)
        main_layout.addLayout(input_section)
        
        # הוספת הודעת ברוכים הבאים
        self.add_welcome_message()
    
    def setup_styles(self):
        """הגדרת העיצוב"""
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f5f7fa;
            }
            
            QFrame#header {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #667eea, stop:1 #764ba2);
                border: none;
            }
            
            QLabel#titleLabel {
                color: white;
                font-size: 20px;
                font-weight: bold;
            }
            
            QLabel#userInfoLabel {
                color: #e8f4fd;
                font-size: 12px;
            }
            
            QFrame#inputFrame {
                background-color: white;
                border-top: 1px solid #e1e8ed;
                border-radius: 10px;
                margin: 5px;
            }
            
            QLineEdit#messageInput {
                border: 2px solid #e1e8ed;
                border-radius: 20px;
                padding: 12px 18px;
                font-size: 14px;
                background-color: #f8f9fa;
            }
            
            QLineEdit#messageInput:focus {
                border-color: #667eea;
                background-color: white;
                outline: none;
            }
            
            QPushButton#sendButton {
                background-color: #667eea;
                color: white;
                border: none;
                border-radius: 20px;
                padding: 12px 24px;
                font-weight: bold;
                font-size: 14px;
                min-width: 80px;
            }
            
            QPushButton#sendButton:hover {
                background-color: #5a67d8;
            }
            
            QPushButton#sendButton:pressed {
                background-color: #4c51bf;
            }
            
            QPushButton#sendButton:disabled {
                background-color: #9ca3af;
            }
            
            QFrame[objectName="userBubble"] {
                background-color: #667eea;
                border-radius: 18px;
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
                border-radius: 18px;
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
            self.user_info_label.setText(f"משתמש ID: {self.user_id}")
        except Exception as e:
            self.user_info_label.setText("משתמש לא מזוהה")
    
    def add_welcome_message(self):
        """הוספת הודעת ברוכים הבאים"""
        welcome_text = """שלום! אני העוזר הדיגיטלי שלך במערכת הספקים.

אני כאן כדי לענות על שאלותיך ולעזור לך עם:
• ניהול מוצרים ומלאי
• ביצוע והזמנות ומעקב
• יצירת קשרים עם ספקים/בעלי חנויות
• שאלות כלליות על המערכת

פשוט כתוב את שאלתך ואני אעזור לך!"""
        
        bubble = ChatBubble(welcome_text.strip(), is_user=False)
        self.messages_layout.addWidget(bubble)
    
    def send_message(self):
        """שליחת הודעה"""
        message = self.message_input.text().strip()
        if not message:
            return
        
        # הוספת ההודעה למממשק
        user_bubble = ChatBubble(message, is_user=True)
        self.messages_layout.addWidget(user_bubble)
        
        # ניקוי שדה הקלט
        self.message_input.clear()
        
        # נעילת הכפתור בזמן השליחה
        self.send_button.setEnabled(False)
        self.send_button.setText("שולח...")
        
        # הוספת אינדיקטור כתיבה
        typing_layout = QHBoxLayout()
        typing_frame = QFrame()
        typing_frame.setObjectName("botBubble")
        typing_frame.setMaximumWidth(200)
        
        frame_layout = QVBoxLayout(typing_frame)
        frame_layout.setContentsMargins(15, 10, 15, 10)
        
        self.typing_indicator = TypingIndicator()
        frame_layout.addWidget(self.typing_indicator)
        
        typing_layout.addWidget(typing_frame)
        typing_layout.addStretch()
        
        typing_container = QWidget()
        typing_container.setLayout(typing_layout)
        self.messages_layout.addWidget(typing_container)
        
        # התחלת מונה הזמן
        self.response_timer.start_timer()
        
        # גלילה למטה
        self.scroll_to_bottom()
        
        # שליחת הבקשה לשרת
        self.chat_thread = ChatRequestThread(self.user_id, message, self.api_url, timeout=self.chat_timeout)
        self.chat_thread.response_received.connect(self.on_response_received)
        self.chat_thread.error_occurred.connect(self.on_error_occurred)
        self.chat_thread.start()
    
    def on_response_received(self, response: dict):
        """טיפול בתגובה מהשרת"""
        # עצירת מונה הזמן
        self.response_timer.stop_timer()
        
        # הסרת אינדיקטור הכתיבה
        if self.typing_indicator:
            # מחיקת הwidget האחרון (אינדיקטור הכתיבה)
            last_item = self.messages_layout.itemAt(self.messages_layout.count() - 1)
            if last_item:
                widget = last_item.widget()
                if widget:
                    self.messages_layout.removeWidget(widget)
                    widget.setParent(None)
            
            self.typing_indicator.stop_animation()
            self.typing_indicator = None
        
        # הוספת התשובה
        if response.get("success"):
            bot_response = response.get("response", "מצטער, לא קיבלתי תשובה.")
            response_time = response.get("response_time", 0)
            dynamic_used = response.get("dynamic_context_used", False)  # חדש
            
            # אפשר להוסיף אינדיקטור ויזואלי
            if dynamic_used:
                bot_response += "\n💡 *תשובה מותאמת אישית עם נתוניך העדכניים*"
            
            bot_bubble = ChatBubble(bot_response, is_user=False, response_time=response_time)
            self.messages_layout.addWidget(bot_bubble)
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
        # עצירת מונה הזמן
        self.response_timer.stop_timer()
        
        # הסרת אינדיקטור הכתיבה
        if self.typing_indicator:
            last_item = self.messages_layout.itemAt(self.messages_layout.count() - 1)
            if last_item:
                widget = last_item.widget()
                if widget:
                    self.messages_layout.removeWidget(widget)
                    widget.setParent(None)
            
            self.typing_indicator.stop_animation()
            self.typing_indicator = None
        
        # הוספת הודעת שגיאה
        error_message = f"שגיאה בתקשורת: {error}"
        error_bubble = ChatBubble(error_message, is_user=False)
        self.messages_layout.addWidget(error_bubble)
        
        # החזרת הכפתור למצב רגיל
        self.send_button.setEnabled(True)
        self.send_button.setText("שלח")
        
        # גלילה למטה
        self.scroll_to_bottom()
    
    def scroll_to_bottom(self):
        """גלילה לתחתית הצ'אט"""
        QTimer.singleShot(100, lambda: self._do_scroll())
    
    def _do_scroll(self):
        scroll_area = self.centralWidget().findChild(QScrollArea)
        if scroll_area:
            scroll_bar = scroll_area.verticalScrollBar()
            scroll_bar.setValue(scroll_bar.maximum())

# דוגמה לשימוש
if __name__ == "__main__":
    from PySide6.QtWidgets import QApplication
    import sys
    
    app = QApplication(sys.argv)
    
    # בדיקה פשוטה - צריך לקבל user_id אמיתי
    chat_window = ChatWindow(user_id=1)
    chat_window.show()
    
    sys.exit(app.exec())