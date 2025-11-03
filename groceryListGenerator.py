import os
import csv
import hashlib
import urllib.request as req
import tkinter as tk
from tkinter import messagebox
from fractions import Fraction
import re

# NOTE: if you need to set DISPLAY for headless environments, set it outside the script.
# os.environ["DISPLAY"] = ":0"

URL = ""

entryLink = None
labelList = None
allThings = []

# Parsing lives in a separate module to make it easy to test without importing tkinter

from parser import Ingredient, getHtml, getInfo

# Simple in-memory user store: username -> password_hash
USER_STORE = {}

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()

def normalize_name(name: str) -> str:
    if not name:
        return ""
    n = name.lower()
    n = re.sub(r"\(.*?)", "", n) 
    n = re.sub(r"[^a-z0-9\s]", "", n)
    n = re.sub(r"\s+", " ", n).strip()
    return n

unitMap = {
    # canonical : [aliases]
    'teaspoon': ['teaspoon', 'teaspoons', 'tsp', 'tsps', 't'],
    'tablespoon': ['tablespoon', 'tablespoons', 'tbsp', 'tbsps', 'tbl', 'tbls', 'T'],
    'cup': ['cup', 'cups'],
    'ounce': ['ounce', 'ounces', 'oz', 'oz.'],
    'pint': ['pint', 'pints', 'pt', 'pts'],
    'quart': ['quart', 'quarts', 'qt', 'qts'],
    'gallon': ['gallon', 'gallons', 'gal', 'gals'],
    'pound': ['pound', 'pounds', 'lb', 'lbs'],
    'gram': ['gram', 'grams', 'g', 'gs'],
    'kilogram': ['kilogram', 'kilograms', 'kg', 'kgs'],
    'milliliter': ['milliliter', 'milliliters', 'ml', 'mls'],
    'liter': ['liter', 'liters', 'l', 'ls'],
    'pinch': ['pinch', 'pinches'],
    'dash': ['dash', 'dashes'],
    'clove': ['clove', 'cloves'],
    'can': ['can', 'cans'],
    'package': ['package', 'packages', 'pkg', 'pkgs'],
    'stick': ['stick', 'sticks'],
    'slice': ['slice', 'slices'],
    'piece': ['piece', 'pieces'],
    'filet': ['filet', 'filets'],
    'bag': ['bag', 'bags'],
    'bunch': ['bunch', 'bunches'],
    'head': ['head', 'heads'],
    'rib': ['rib', 'ribs'],
    'sprig': ['sprig', 'sprigs'],
    'leaf': ['leaf', 'leaves'],
    'large': ['large'],
    'small': ['small'],
    'medium': ['medium'],
}

unitCanonical = {alias: canon for canon, aliases in unitMap.items() for alias in aliases}

def normalize_unit(unit: str) -> str:
    if not unit:
        return ""
    u = unit.lower().strip().replace('.', '')
    u = re.sub(r"[^a-z]", "", u)
    return unitCanonical.get(u, u)


def parse_quantity(q: str) -> Fraction | None:
    if not q:
        return None
    s = q.strip()
    if not s:
        return None
    # replace unicode fractions
    uni = {'½':'1/2','¼':'1/4','¾':'3/4','⅓':'1/3','⅔':'2/3','⅛':'1/8'}
    for k,v in uni.items():
        s = s.replace(k, v)
    # replace hyphens with space
    s = s.replace('-', ' ')
    parts = s.split()
    total = Fraction(0)
    for part in parts:
        try:
            if '/' in part:
                total += Fraction(part)
            else:
                # try integer then float
                try:
                    total += Fraction(int(part))
                except Exception:
                    total += Fraction(float(part))
        except Exception:
            # not a number (e.g., 'to', 'taste') -> cannot parse
            return None
    return total


def format_quantity(frac: Fraction) -> str:
    if frac is None:
        return ""
    if frac == 0:
        return "0"
    if frac.denominator == 1:
        return str(frac.numerator)
    whole = frac.numerator // frac.denominator
    rem = Fraction(frac.numerator % frac.denominator, frac.denominator)
    if whole:
        if rem:
            return f"{whole} {rem}"
        return str(whole)
    return str(rem)


def combine_ingredients(items: list[Ingredient]) -> list[Ingredient]:
    """Combine ingredients with same normalized name and unit, summing quantities when numeric.
    Non-numeric quantities are appended as separate entries if they cannot be parsed.
    """
    agg = {}
    nonNumeric = []
    for it in items:
        nameKey = normalize_name(it.name)
        unitKey = normalize_unit(it.unit)
        qty = parse_quantity(it.quantity)
        if qty is None:
            # store as-is but attempt to merge exact same name+unit non-numeric
            nonNumeric.append((nameKey, unitKey, it))
            continue
        key = (nameKey, unitKey)
        if key not in agg:
            agg[key] = {'qty': Fraction(0), 'unit': it.unit, 'display_name': it.name}
        agg[key]['qty'] += qty
        # prefer longer display name (heuristic)
        if len(it.name) > len(agg[key]['display_name']):
            agg[key]['display_name'] = it.name

    results = []
    for (nameKey, unitKey), data in agg.items():
        qstr = format_quantity(data['qty'])
        results.append(Ingredient(qstr, data['unit'], data['display_name']))

    # merge non-numeric: group exact normalized name+unit
    seen = {}
    for nameKey, unitKey, it in nonNumeric:
        key = (nameKey, unitKey)
        if key not in seen:
            seen[key] = it
        else:
            # if duplicate non-numeric, append the extra text to the name
            prev = seen[key]
            prev.name = prev.name + "; " + it.name
    results.extend(seen.values())
    return results


def save_user_store(path: str = None):
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

def load_user_store(path: str = None):
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




def show_register_dialog(parent) -> None:
    dlg = tk.Toplevel(parent)
    dlg.title("Register")
    dlg.grab_set()

    tk.Label(dlg, text="Username:").pack(pady=2)
    user_ent = tk.Entry(dlg)
    user_ent.pack(pady=2)

    tk.Label(dlg, text="Password:").pack(pady=2)
    pass_ent = tk.Entry(dlg, show="*")
    pass_ent.pack(pady=2)

    def do_register():
        username = user_ent.get().strip()
        password = pass_ent.get()
        if not username or not password:
            messagebox.showwarning("Input Error", "Please enter both username and password.")
            return
        if username in USER_STORE:
            messagebox.showerror("Error", "Username already exists")
            return
        USER_STORE[username] = hash_password(password)
        messagebox.showinfo("Success", f"Registered {username}")
        # persist the user store after successful registration
        try:
            save_user_store()
        except Exception:
            # non-fatal; warn on console
            print("Warning: failed to save user store after registration")
        dlg.destroy()

    tk.Button(dlg, text="Register", command=do_register).pack(pady=6)
    parent.wait_window(dlg)

def show_login_dialog(parent) -> bool:
    dlg = tk.Toplevel(parent)
    dlg.title("Login")
    dlg.grab_set()

    tk.Label(dlg, text="Username:").pack(pady=2)
    user_ent = tk.Entry(dlg)
    user_ent.pack(pady=2)

    tk.Label(dlg, text="Password:").pack(pady=2)
    pass_ent = tk.Entry(dlg, show="*")
    pass_ent.pack(pady=2)

    result = {"ok": False}

    def do_login():
        username = user_ent.get().strip()
        password = pass_ent.get()
        if username not in USER_STORE:
            messagebox.showerror("Error", "Invalid Username or Password")
            return
        if USER_STORE[username] != hash_password(password):
            messagebox.showerror("Error", "Invalid Username or Password")
            return
        messagebox.showinfo("Success", "Login successful")
        result["ok"] = True
        dlg.destroy()

    tk.Button(dlg, text="Login", command=do_login).pack(pady=6)
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
    combined = combine_ingredients(allThings)
    lines = [f"{it.quantity} {it.unit} {it.name}".strip() for it in combined]
    labelList.configure(text="\n".join(lines))
    entryLink.delete(0, "end")

def main():
    # load persisted users (if any)
    load_user_store()

    root = tk.Tk()
    root.title("Grocery List Generator")
    root.geometry("800x400")

    # Ask user to register or login first
    frame = tk.Frame(root)
    frame.pack(pady=10)

    tk.Label(frame, text="Please register or login to continue").pack()
    btn_frame = tk.Frame(frame)
    btn_frame.pack(pady=6)

    def on_register():
        show_register_dialog(root)

    def on_login():
        ok = show_login_dialog(root)
        if ok:
            # Destroy auth frame and continue to main UI
            frame.destroy()
            build_main_ui(root)

    tk.Button(btn_frame, text="Register", command=on_register).pack(side=tk.LEFT, padx=6)
    tk.Button(btn_frame, text="Login", command=on_login).pack(side=tk.LEFT, padx=6)

    root.mainloop()

def build_main_ui(root):
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