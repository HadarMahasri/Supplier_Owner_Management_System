from PySide6.QtWidgets import QApplication
import sys

# ייבוא העמוד שבנית
from frontend.views.pages.owner_links_page import OwnerLinksPage

def main():
    app = QApplication(sys.argv)

    # יוצרים את הדף עם owner_id=6
    win = OwnerLinksPage(owner_id=6)
    win.show()

    sys.exit(app.exec())

if __name__ == "__main__":
    main()
