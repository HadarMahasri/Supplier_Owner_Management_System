import tkinter as tk
from tkinter import ttk
from views.pages.supplier_links_page import SupplierLinksPage

def main():
    root = tk.Tk()
    root.title("חיבורים – דף ספק")
    root.geometry("900x520")
    page = SupplierLinksPage(root, supplier_id=1)  # ספק לדוגמה
    page.pack(fill="both", expand=True)
    root.mainloop()

if __name__ == "__main__":
    main()
