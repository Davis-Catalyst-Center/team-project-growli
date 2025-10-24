import tkinter as tk
import tkinter.messagebox as msgbox
import urllib.request as req
import os
from tkinter import messagebox
import hashlib
os.environ["DISPLAY"] = ":0"

# Having issues with DISPLAY that are only occuring when using GitHub
VALID_USERS = []
PASSWORD = []
# Use Visual Studio Code
# Install GitHub Pull Requests and Git

URL = ""

entryLink = None
labelList = None
allThings = []

class Ingredients:
    def __init__(self, quantity, unit, name):
        self.quantity = quantity
        self.unit = unit
        self.name = name

def register_user():
    """Function to handle user registration when the button is clicked."""
    username = username_entry.get()
    password = password_entry.get()

    if username and password:
        VALID_USERS.append(username)
        PASSWORD.append(password)
        messagebox.showinfo("Success", f"User '{username}' registered successfully!")
        # Clear the entry fields after registration
        username_entry.delete(0, tk.END)
        password_entry.delete(0, tk.END)
        print("Registered Users:", VALID_USERS)
        print("Passwords:", PASSWORD)
    else:
        messagebox.showwarning("Input Error", "Please enter both username and password.")
    root.destroy()
root = tk.Tk()
root.title("User Registration")

# Create and place username label and entry
username_label = tk.Label(root, text="Enter a username:")
username_label.pack(pady=5)
username_entry = tk.Entry(root, width=30)
username_entry.pack(pady=5)

# Create and place password label and entry
password_label = tk.Label(root, text="Enter a password:")
password_label.pack(pady=5)
password_entry = tk.Entry(root, width=30, show="*") # show="*" hides password input
password_entry.pack(pady=5)

# Create and place the register button
register_button = tk.Button(root, text="Register", command=register_user)
register_button.pack(pady=10)

# Start the Tkinter event loop
root.mainloop()

def getHtml():
    request = req.Request(URL, headers= {"User-Agent": "Mozilla/5.0"})
    with req.urlopen(request) as response:
        htmlAsBytes = response.read()
        html = htmlAsBytes.decode("utf-8")
        print(html)
        return html

def getInfo(html):
    global allThings
    currentIndex = 0
    while currentIndex >= 0:
        # Find Quantity
        startIndexQuant = html.find("data-ingredient-quantity=\"true\">", currentIndex)
        garbage = len("data-ingredient-quantity=\"true\">")
        endIndexQuant = html.find("</span> <span data-ingredient-unit=\"true\">", startIndexQuant)
        quantity = html[startIndexQuant + garbage:endIndexQuant]

        # Find Unit
        startIndexUnit = html.find("data-ingredient-unit=\"true\">", currentIndex)
        garbage = len("data-ingredient-unit=\"true\">")
        endIndexUnit = html.find("</span> <span data-ingredient-name=\"true\">", startIndexUnit)
        unit = html[startIndexUnit + garbage:endIndexUnit]

        # Find Ingredient Name
        startIndexName = html.find("data-ingredient-name=\"true\">", currentIndex)
        garbage = len("data-ingredient-name=\"true\">")
        endIndexName = html.find("</span></p>", startIndexName)
        name = html[startIndexName + garbage:endIndexName]

        currentIndex = endIndexName
        
        allThings.append(Ingredients(quantity, unit, name))
        

def entered():
    global entryLink, URL
    URL = entryLink.get()
    labelListText = labelList.cget("text")
    getInfo(getHtml())
    if labelListText != "":
        labelList.configure(text=labelListText + "\n" + allThings[-1].quantity + " " + allThings[-1].unit + " " + allThings[-1].name)
    else:
        labelList.configure(text=allThings[-1].quantity + " " + allThings[-1].unit + " " + allThings[-1].name)

    entryLink.delete(0, "end")

def validate_login():
    username = username_entry.get()
    password = password_entry.get()

    if username in VALID_USERS and password in PASSWORD:
        messagebox.showinfo("Success", "Login Successful!")
        
    else:
        messagebox.showerror("Error", "Invalid Username or Password")
    root.destroy()

root = tk.Tk()
root.title("Login Form")
root.geometry("300x200")

username_label = tk.Label(root, text="Username:")
username_label.pack(pady=5)
username_entry = tk.Entry(root)
username_entry.pack(pady=5)

password_label = tk.Label(root, text="Password:")
password_label.pack(pady=5)
password_entry = tk.Entry(root, show="*")
password_entry.pack(pady=5)

login_button = tk.Button(root, text="Login", command=validate_login)
login_button.pack(pady=10)
root.mainloop()
def main():
    root = tk.Tk()
    root.title("Login Form")
    root.geometry("300x200") # Set window size
    root.destroy()
    # Create Window
    root = tk.Tk()
    root.title("Grocery List Generator")
    root.geometry("1000x500")
    



    # label for instructions
    labelInstructions = tk.Label(root, text="Please enter your link")
    labelInstructions.pack()

    # textbox for input
    global entryLink
    entryLink = tk.Entry(root)
    entryLink.pack()

    # List
    global labelList
    labelList = tk.Label(root, text="")
    labelList.pack()


    root.bind(("<Return>") ,lambda event:entered())

    # Display Window (will stop the execution of any code after this point until the window is closed)
    root.mainloop()
    

main()