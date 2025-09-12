import tkinter as tk
import tkinter.messagebox as msgbox
import urllib.request as req


def main():
    # Create Window
    root = tk.Tk()
    root.title("Grocery List Generator")


    # textbox for input
    entry_ingredient = tk.Entry(root)
    entry_ingredient.pack()



    # Display Window (will stop the execution of any code after this point until the window is closed)
    root.mainloop()

main()