
# --- Generalized ingredient normalization and combining ---
import difflib

unitMap = {
    'teaspoon': ['teaspoon', 'teaspoons', 'tsp', 'tsps', 't', 'tsp.', 'tsps.'],
    'tablespoon': ['tablespoon', 'tablespoons', 'tbsp', 'tbsps', 'tbl', 'tbls', 'T', 'tbsp.', 'tbsps.', 'tbl.', 'tbls.'],
    'cup': ['cup', 'cups', 'c', 'c.'],
    'ounce': ['ounce', 'ounces', 'oz', 'oz.', 'fl oz', 'fl. oz.', 'fluid ounce', 'fluid ounces'],
    'pint': ['pint', 'pints', 'pt', 'pts', 'pt.', 'pts.'],
    'quart': ['quart', 'quarts', 'qt', 'qts', 'qt.', 'qts.'],
    'gallon': ['gallon', 'gallons', 'gal', 'gals', 'gal.', 'gals.'],
    'pound': ['pound', 'pounds', 'lb', 'lbs', 'lb.', 'lbs.'],
    'gram': ['gram', 'grams', 'g', 'gs', 'g.', 'gs.'],
    'kilogram': ['kilogram', 'kilograms', 'kg', 'kgs', 'kg.', 'kgs.'],
    'milliliter': ['milliliter', 'milliliters', 'ml', 'mls', 'ml.', 'mls.'],
    'liter': ['liter', 'liters', 'l', 'ls', 'l.', 'ls.'],
    'pinch': ['pinch', 'pinches'],
    'dash': ['dash', 'dashes'],
}
unitCanonical = {alias: canon for canon, aliases in unitMap.items() for alias in aliases}
unit_conversions = {
    ("tbsp", "cup"): 1/16,
    ("cup", "tbsp"): 16,
    ("tsp", "tbsp"): 1/3,
    ("tbsp", "tsp"): 3,
    ("oz", "cup"): 1/8,
    ("cup", "oz"): 8,
    ("oz", "tbsp"): 2,
    ("tbsp", "oz"): 1/2,
}

def normalize_unit(unit: str) -> str:
    if not unit:
        return ""
    u = unit.lower().strip().replace('.', '')
    u = re.sub(r"[^a-z ]", "", u)
    return unitCanonical.get(u, u)

def canonicalize_name(name: str) -> str:
    n = name.lower()
    n = re.sub(r"\(.*?\)", "", n)
    n = re.sub(r"[^a-z0-9\s]", "", n)
    descriptors = [
        "boneless", "skinless", "dry", "fresh", "extra", "low-sodium", "large", "small", "medium", "freshly", "ground", "sliced", "pieces", "breasts", "breast", "noodles", "cut into", "cubed", "diced", "chopped", "minced", "shredded", "grated", "crushed", "peeled", "seeded", "halved", "quartered", "rinsed", "drained", "rinsed and drained", "slice", "cut", "into", "thinly", "thickly", "coarsely", "finely", "prepared", "cooked", "raw", "uncooked", "frozen", "thawed", "room temperature", "softened", "melted", "warm", "cold", "hot", "divided", "for garnish", "for serving", "to taste", "as needed", "optional"
    ]
    for word in descriptors:
        n = n.replace(word, "")
    n = re.sub(r"\s+", " ", n).strip()
    # Tokenize and match by main ingredient words
    tokens = n.split()
    if not tokens:
        return n
    # Build a set of canonical ingredient names from all items seen so far
    global allThings
    seen_names = set([re.sub(r"\s+", " ", canonicalize_name(it.name)) for it in allThings])
    candidates = list(seen_names)
    # Try to find a candidate that contains all tokens (partial match)
    for cand in candidates:
        cand_tokens = cand.split()
        if all(token in cand_tokens for token in tokens):
            return cand
    # Try to find a candidate that contains the main token (first word)
    for cand in candidates:
        cand_tokens = cand.split()
        if tokens[0] in cand_tokens:
            return cand
    # Fallback to fuzzy matching
    match = difflib.get_close_matches(n, candidates, n=1, cutoff=0.8)
    if match:
        return match[0]
    return n

def parse_quantity(q: str) -> Fraction | None:
    if not q:
        return None
    s = q.strip()
    if not s:
        return None
    uni = {'½':'1/2','¼':'1/4','¾':'3/4','⅓':'1/3','⅔':'2/3','⅛':'1/8'}
    for k,v in uni.items():
        s = s.replace(k, v)
    s = s.replace('-', ' ')
    parts = s.split()
    total = Fraction(0)
    for part in parts:
        try:
            if '/' in part:
                total += Fraction(part)
            else:
                try:
                    total += Fraction(int(part))
                except Exception:
                    total += Fraction(float(part))
        except Exception:
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

def convert_unit(qty, from_unit, to_unit):
    if from_unit == to_unit:
        return qty
    key = (from_unit, to_unit)
    if key in unit_conversions:
        return qty * unit_conversions[key]
    return None

def get_canonical_unit(name_key, unit_key):
    # For now, just use the most common unit among all items with this name
    # Could be improved with a static map or more logic
    return unit_key

def combineIngredients(items: list) -> list:
    agg = {}
    for it in items:
        name_key = canonicalize_name(it.name)
        unit_key = normalize_unit(it.unit)
        qty = parse_quantity(it.quantity)
        if qty is None:
            continue
        canon_unit = get_canonical_unit(name_key, unit_key)
        qty_in_canon = convert_unit(qty, unit_key, canon_unit)
        if qty_in_canon is None and unit_key == canon_unit:
            qty_in_canon = qty
        key = (name_key, canon_unit)
        if key not in agg:
            agg[key] = {'qty': Fraction(0), 'unit': canon_unit, 'display_name': it.name}
        agg[key]['qty'] += qty_in_canon
        if len(it.name) > len(agg[key]['display_name']):
            agg[key]['display_name'] = it.name
    return [
        Ingredient(
            name=agg[key]['display_name'],
            quantity=format_quantity(agg[key]['qty']),
            unit=agg[key]['unit']
        )
        for key in agg
    ]
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
allLinks = []
buttons = []

# Parsing lives in a separate module to make it easy to test without importing tkinter

from parser_1 import Ingredient, getHtml, getInfo

# Simple in-memory user store: username -> password_hash
USER_STORE = {}

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()

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
            saveUserStore()
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
    global entryLink, labelList, allThings, allLinks
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

def linkButtonClicked(buttonUrl):
    global allLinks
    # Remove the items associated with the URL, then remove the URL
    itemsToRemove = []
    for i in range(len(allThings)):
        if allThings[i].url == buttonUrl:
            itemsToRemove.append(allThings[i])
   
    for item in itemsToRemove:
        allThings.remove(item)

    allLinks = [link for link in allLinks if link != buttonUrl]

    # Update everything so the display is up to date
    removeButton(buttonUrl)
    makeButton()
    displayButtons()
    alphabetizedThings = alphabetizeList(allThings)
    combined = combineIngredients(alphabetizedThings)
    lines = [f"{it.quantity} {it.unit} {it.name}".strip() for it in combined]
    labelList.configure(text="\n".join(lines))


def removeButton(removeUrl):
    for button in buttons:
        if removeUrl == button['text']:
            button.pack_forget()
            button.destroy()

def makeButton():
    global buttons
    for button in buttons:
        button.pack_forget()
        button.destroy()
    buttons = []
    for i in range(len(allLinks)):
        buttonText = allLinks[i]
        buttons.append(tk.Button(text=buttonText, command=lambda t=buttonText: linkButtonClicked(t)))

def displayButtons():
    for button in buttons:
        button.pack(pady=6)

def alphabetizeList(list):
    return sorted(list, key=lambda ingredient: ingredient.name.lower())


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