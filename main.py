import tkinter as tk
from gui.app import ImageProcessorApp

def main():
    root = tk.Tk()
    app = ImageProcessorApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()