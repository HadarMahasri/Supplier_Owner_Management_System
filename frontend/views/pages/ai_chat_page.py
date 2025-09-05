# frontend/views/pages/ai_chat_page.py
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QFrame, QScrollArea, QLineEdit, QPushButton
from PySide6.QtCore import Qt, QTimer
import os

# מייבאים את רכיבי הצ'אט הקיימים מהחלון הישן
from views.pages.chat_window import ChatRequestThread, TypingIndicator, ChatBubble, ResponseTimer

class AIChatPage(QWidget):
    """
    עמוד צ'אט AI בתוך חלון יחיד (בלי כותרת חלון נפרדת).
    שומר על הסרגל העליון של StoreOwnerHome כי זה רק ה'תוכן'.
    """
    def __init__(self, user_id: int, api_url: str = None, parent=None):
        super().__init__(parent)
        self.user_id = user_id
        self.api_url = (api_url or os.getenv("API_BASE_URL", "http://localhost:8000")).rstrip("/")
        self.chat_timeout = int(os.getenv("CHAT_UI_TIMEOUT", "180"))
        self.typing_indicator = None
        self.response_timer = None
        self._setup_ui()
        self._setup_styles()
        self._add_welcome_message()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        # אזור ההודעות עם Scroll
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        self.messages_container = QWidget()
        self.messages_layout = QVBoxLayout(self.messages_container)
        self.messages_layout.setContentsMargins(4, 4, 4, 4)
        self.messages_layout.setSpacing(10)

        scroll_area.setWidget(self.messages_container)
        layout.addWidget(scroll_area, 1)

        # מונה זמן תגובה
        self.response_timer = ResponseTimer()
        layout.addWidget(self.response_timer, alignment=Qt.AlignHCenter)

        # שורת הקלט
        input_frame = QFrame(objectName="inputFrame")
        input_layout = QHBoxLayout(input_frame)
        input_layout.setContentsMargins(10, 10, 10, 10)
        input_layout.setSpacing(8)

        self.message_input = QLineEdit(objectName="messageInput")
        self.message_input.setPlaceholderText("כתוב את שאלתך כאן…")
        self.message_input.returnPressed.connect(self._send_message)

        self.send_button = QPushButton("שלח", objectName="sendButton")
        self.send_button.clicked.connect(self._send_message)

        input_layout.addWidget(self.message_input)
        input_layout.addWidget(self.send_button)

        layout.addWidget(input_frame)

    def _setup_styles(self):
        self.setStyleSheet("""
            QFrame#inputFrame { background: #fff; border: 1px solid #e5e7eb; border-radius: 10px; }
            QLineEdit#messageInput {
                border: 2px solid #e5e7eb; border-radius: 18px; padding: 10px 14px; background: #f8f9fa;
            }
            QLineEdit#messageInput:focus { border-color: #667eea; background: #fff; }
            QPushButton#sendButton {
                background: #667eea; color: #fff; border: none; border-radius: 18px; padding: 10px 20px; font-weight: 600;
            }
            QFrame[objectName="userBubble"] { background: #667eea; border-radius: 18px; }
            QFrame[objectName="botBubble"]  { background: #fff; border:1px solid #e1e8ed; border-radius:18px; }
        """)

    def _add_welcome_message(self):
        txt = ("שלום! זהו צ'אט ה-AI של המערכת.\n"
               "אפשר לשאול על הזמנות, מלאי, וקישורים עם ספקים/בעלי חנויות.")
        self.messages_layout.addWidget(ChatBubble(txt, is_user=False))

    def _send_message(self):
        message = self.message_input.text().strip()
        if not message:
            return

        # הצגת הודעת המשתמש
        self.messages_layout.addWidget(ChatBubble(message, is_user=True))
        self.message_input.clear()

        # אינדיקטור "כותב…" + מונה זמן
        typing_layout = QHBoxLayout()
        typing_frame = QFrame(objectName="botBubble")
        tf_layout = QVBoxLayout(typing_frame)
        self.typing_indicator = TypingIndicator()
        tf_layout.addWidget(self.typing_indicator)
        typing_layout.addWidget(typing_frame)
        typing_layout.addStretch()
        typing_container = QWidget(); typing_container.setLayout(typing_layout)
        self.messages_layout.addWidget(typing_container)

        self.send_button.setEnabled(False); self.send_button.setText("שולח…")
        self.response_timer.start_timer()

        # שיגור בקשה ל-Gateway (כולל user_id)
        t = ChatRequestThread(self.user_id, message, self.api_url, timeout=self.chat_timeout, user_data={})
        t.response_received.connect(self._on_response_received)
        t.error_occurred.connect(self._on_error)
        self._thread = t
        t.start()

    def _on_response_received(self, data: dict):
        # סיום “כותב…”
        self.response_timer.stop_timer()
        if self.typing_indicator:
            last_item = self.messages_layout.itemAt(self.messages_layout.count()-1)
            if last_item and last_item.widget():
                last_item.widget().setParent(None)
            self.typing_indicator.stop_animation()
            self.typing_indicator = None

        # הצגת תשובה
        response = (data or {}).get("response") or "לא התקבלה תשובה מהשרת."
        rt = (data or {}).get("response_time")
        self.messages_layout.addWidget(ChatBubble(response, is_user=False, response_time=rt))

        self.send_button.setEnabled(True); self.send_button.setText("שלח")
        QTimer.singleShot(100, self._scroll_to_bottom)

    def _on_error(self, err: str):
        self.response_timer.stop_timer()
        if self.typing_indicator:
            last_item = self.messages_layout.itemAt(self.messages_layout.count()-1)
            if last_item and last_item.widget():
                last_item.widget().setParent(None)
            self.typing_indicator.stop_animation()
            self.typing_indicator = None

        self.messages_layout.addWidget(ChatBubble(f"שגיאה בתקשורת: {err}", is_user=False))
        self.send_button.setEnabled(True); self.send_button.setText("שלח")
        QTimer.singleShot(100, self._scroll_to_bottom)

    def _scroll_to_bottom(self):
        sa = self.findChild(QScrollArea)
        if sa:
            sa.verticalScrollBar().setValue(sa.verticalScrollBar().maximum())
