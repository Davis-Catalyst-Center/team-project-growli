import tkinter as tk
import tkinter.messagebox as msgbox
import urllib.request as req
import os


os.environ["DISPLAY"] = ":0"

# Having issues with DISPLAY that are only occuring when using GitHub

entryIngredient = None
labelList = None

def entered():
    global entryIngredient
    ingredient = entryIngredient.get()
    labelListText = labelList.cget("text")
    if labelListText != "":
        labelList.configure(text=labelListText + "\n" + ingredient)
    else:
        labelList.configure(text=ingredient)

    entryIngredient.delete(0, "end")

def main():
    # Create Window
    root = tk.Tk()
    root.title("Grocery List Generator")
    root.geometry("1000x500")

    # label for instructions
    labelInstructions = tk.Label(root, text="Please enter your ingredients")
    labelInstructions.pack()

    # textbox for input
    global entryIngredient
    entryIngredient = tk.Entry(root)
    entryIngredient.pack()

    # List
    global labelList
    labelList = tk.Label(root, text="")
    labelList.pack()


    root.bind(("<Return>") ,lambda event:entered())

    # Display Window (will stop the execution of any code after this point until the window is closed)
    root.mainloop()

main()