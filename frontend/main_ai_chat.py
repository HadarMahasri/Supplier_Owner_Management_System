import os, sys
from PySide6.QtWidgets import QApplication
from views.widgets.ai_consultant import AIConsultant

def main():
    # קחי user_id זמני לבדיקות (אפשר לשנות בפרמטר שורת־פקודה)
    user_id = int(sys.argv[1]) if len(sys.argv) > 1 else int(os.getenv("CHAT_USER_ID", "1"))
    app = QApplication(sys.argv)
    w = AIConsultant(user_id=user_id)
    w.setWindowTitle(f"AI Chat (user_id={user_id})")
    w.resize(600, 500)
    w.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
