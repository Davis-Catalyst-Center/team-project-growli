import os
import csv
import hashlib
import urllib.request as req
import tkinter as tk
from tkinter import messagebox
from fractions import Fraction
import re

URL = ""

entryLink = None
labelList = None
allThings = []

# Parsing lives in a separate module to make it easy to test without importing tkinter

from parser import Ingredient, getHtml, getInfo

# Simple in-memory user store: username -> password_hash
USER_STORE = {}

def hashPassword(password: str) -> str:
    return hashPassword(password)

def saveUserStore(path: str = None):
    """Persist USER_STORE to CSV file. Overwrites existing file.
    Each row: username, password_hash
    """
    if path is None:
        path = os.path.join(os.getcwd(), "Users.csv")
    try:
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            for user, pwdhash in USER_STORE.items():
                writer.writerow([user, pwdhash])
    except Exception as e:
        # don't crash the app for persistence errors; show a warning instead
        print(f"Warning: could not save users to {path}: {e}")

def loadUserStore(path: str = None):
    if path is None:
        path = os.path.join(os.getcwd(), "Users.csv")
    if not os.path.exists(path):
        return
    try:
        with open(path, "r", newline="", encoding="utf-8") as f:
            reader = csv.reader(f)
            for row in reader:
                if not row:
                    continue
                user = row[0]
                pwdhash = row[1] if len(row) > 1 else ""
                USER_STORE[user] = pwdhash
    except Exception as e:
        print(f"Warning: could not load users from {path}: {e}")


def showRegisterDialog(parent) -> None:
    dlg = tk.Toplevel(parent)
    dlg.title("Register")
    dlg.grab_set()

    tk.Label(dlg, text="Username:").pack(pady=2)
    userEnt = tk.Entry(dlg)
    userEnt.pack(pady=2)

    tk.Label(dlg, text="Password:").pack(pady=2)
    passEnt = tk.Entry(dlg, show="*")
    passEnt.pack(pady=2)

    def doRegister():
        username = userEnt.get().strip()
        password = passEnt.get()
        if not username or not password:
            messagebox.showwarning("Input Error", "Please enter both username and password.")
            return
        if username in USER_STORE:
            messagebox.showerror("Error", "Username already exists")
            return
        USER_STORE[username] = hashPassword(password)
        messagebox.showinfo("Success", f"Registered {username}")
        # persist the user store after successful registration
        try:
            saveUserStore()
        except Exception:
            # non-fatal; warn on console
            print("Warning: failed to save user store after registration")
        dlg.destroy()

    tk.Button(dlg, text="Register", command=doRegister).pack(pady=6)
    parent.wait_window(dlg)

def showLoginDialog(parent) -> bool:
    dlg = tk.Toplevel(parent)
    dlg.title("Login")
    dlg.grab_set()

    tk.Label(dlg, text="Username:").pack(pady=2)
    userEnt = tk.Entry(dlg)
    userEnt.pack(pady=2)

    tk.Label(dlg, text="Password:").pack(pady=2)
    passEnt = tk.Entry(dlg, show="*")
    passEnt.pack(pady=2)

    result = {"ok": False}

    def doLogin():
        username = userEnt.get().strip()
        password = passEnt.get()
        if username not in USER_STORE:
            messagebox.showerror("Error", "Invalid Username or Password")
            return
        if USER_STORE[username] != hashPassword(password):
            messagebox.showerror("Error", "Invalid Username or Password")
            return
        messagebox.showinfo("Success", "Login successful")
        result["ok"] = True
        dlg.destroy()

    tk.Button(dlg, text="Login", command=doLogin).pack(pady=6)
    parent.wait_window(dlg)
    return result["ok"]

def entered():
    global entryLink, labelList, allThings
    url = entryLink.get().strip()
    if not url:
        messagebox.showwarning("Input Error", "Please enter a URL")
        return
    try:
        html = getHtml(url)
    except Exception as e:
        messagebox.showerror("Network Error", f"Could not fetch URL: {e}")
        return

    # parse
    items = getInfo(html, url)
    if not items:
        messagebox.showinfo("No ingredients", "No ingredients were found on that page.")
        return

    # append parsed items to allThings and update label
    allThings.extend(items)
    combined = combineIngredients(allThings)
    lines = [f"{it.quantity} {it.unit} {it.name}".strip() for it in combined]
    labelList.configure(text="\n".join(lines))
    entryLink.delete(0, "end")

def main():
    # load persisted users (if any)
    loadUserStore()

    root = tk.Tk()
    root.title("Grocery List Generator")
    root.geometry("800x400")

    # Ask user to register or login first
    frame = tk.Frame(root)
    frame.pack(pady=10)

    tk.Label(frame, text="Please register or login to continue").pack()
    btnFrame = tk.Frame(frame)
    btnFrame.pack(pady=6)

    def onRegister():
        showRegisterDialog(root)

    def onLogin():
        ok = showLoginDialog(root)
        if ok:
            # Destroy auth frame and continue to main UI
            frame.destroy()
            buildMainUi(root)

    tk.Button(btnFrame, text="Register", command=onRegister).pack(side=tk.LEFT, padx=6)
    tk.Button(btnFrame, text="Login", command=onLogin).pack(side=tk.LEFT, padx=6)

    root.mainloop()

def buildMainUi(root):
    global entryLink, labelList
    # label for instructions
    labelInstructions = tk.Label(root, text="Please enter a link to a recipe page and press Enter")
    labelInstructions.pack(pady=6)

    # textbox for input
    entryLink = tk.Entry(root, width=80)
    entryLink.pack(pady=6)

    # List
    labelList = tk.Label(root, text="", justify=tk.LEFT, anchor="w")
    labelList.pack(fill=tk.BOTH, expand=True, padx=10, pady=6)

    root.bind("<Return>", lambda event: entered())


if __name__ == "__main__":
    main()