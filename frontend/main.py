# frontend/main.py
import sys
from PySide6.QtWidgets import QApplication, QMessageBox
from PySide6.QtCore import Qt
from views.login_dialog import LoginDialog
from views.signup_dialog import SignUpDialog
from views.main_window import MainWindow

def main():
    app = QApplication(sys.argv)
    
    # הגדרת כיוון RTL
    app.setLayoutDirection(Qt.RightToLeft)
    
    # הגדרת סגנון (אופציונלי)
    app.setStyle('Fusion')
    
    while True:
        # פתיחת דיאלוג התחברות
        login = LoginDialog()
        result = login.exec()
        
        if result == LoginDialog.Accepted and login.user:
            # התחברות הצליחה
            try:
                w = MainWindow(current_user=login.user)
                w.show()
                sys.exit(app.exec())
            except Exception as e:
                QMessageBox.critical(None, "שגיאה", f"שגיאה בטעינת החלון הראשי:\n{str(e)}")
                continue
                
        elif result == LoginDialog.Rejected:
            # בדיקה אם המשתמש רוצה להירשם
            reply = QMessageBox.question(
                None,
                "רישום למערכת",
                "האם ברצונך להירשם למערכת?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                # פתיחת דיאלוג הרשמה
                signup = SignUpDialog()
                if signup.exec() == SignUpDialog.Accepted:
                    QMessageBox.information(None, "הרשמה הצליחה", "ההרשמה הושלמה בהצלחה!\nאנא התחבר עם הפרטים שהזנת.")
                    continue  # חזרה לדיאלוג התחברות
            else:
                # יציאה מהאפליקציה
                sys.exit(0)
        else:
            # המשתמש סגר את החלון
            sys.exit(0)

if __name__ == "__main__":
    main()