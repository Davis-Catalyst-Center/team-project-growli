import os
import csv
import hashlib
import urllib.request as req
import tkinter as tk
from tkinter import messagebox
from fractions import Fraction
import re

URL = ""

innerFrame = None
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

def normalize_name(name: str) -> str:
    if not name:
        return ""
    n = name.lower()
    n = re.sub(r"\(.*?\)", "", n) 
    n = re.sub(r"[^a-z0-9\s]", "", n)
    n = re.sub(r"\s+", " ", n).strip()
    return n

# Expanded unit map for robust normalization
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
    'clove': ['clove', 'cloves'],
    'can': ['can', 'cans'],
    'package': ['package', 'packages', 'pkg', 'pkgs', 'pkg.', 'pkgs.'],
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
unit_conversions = {
    ("lb", "oz"): 16,
    ("oz", "lb"): 1/16,
    ("cup", "oz"): 8,      # for cheese, butter, etc. (approximate)
    ("oz", "cup"): 1/8,
    ("tbsp", "tsp"): 3,
    ("tsp", "tbsp"): 1/3,
    ("cup", "tbsp"): 16,
    ("tbsp", "cup"): 1/16,
    ("cup", "ml"): 237,
    ("ml", "cup"): 1/237,
    ("quart", "cup"): 4,
    ("cup", "quart"): 1/4,
    ("pint", "cup"): 2,
    ("cup", "pint"): 1/2,
    ("gallon", "quart"): 4,
    ("quart", "gallon"): 1/4,
    ("pound", "oz"): 16,
    ("oz", "pound"): 1/16,
}
unitCanonical = {alias: canon for canon, aliases in unitMap.items() for alias in aliases}

def normalize_unit(unit: str) -> str:
    if not unit:
        return ""
    u = unit.lower().strip().replace('.', '')
    u = re.sub(r"[^a-z ]", "", u)
    u = u.replace('fluid ounce', 'fl oz')  # handle 'fluid ounce' as 'fl oz'
    u = u.replace('fl oz', 'fl oz')
    u = u.strip()
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


# --- Improved fuzzy ingredient name normalization ---
def canonicalize_name(name: str) -> str:
    mapping = [
        (r"fettuccine.*", "fettuccine"),
        (r"chicken breast[s]?", "chicken"),
        (r"parmesan.*cheese", "parmesan cheese"),
        (r"olive oil", "olive oil"),
        (r"cream cheese", "cream cheese"),
        (r"heavy cream", "heavy cream"),
        (r"garlic", "garlic"),
        (r"butter", "butter"),
        (r"noodle[s]?", "fettuccine"),
        (r"parsley", "parsley"),
        (r"lemon juice", "lemon juice"),
        (r"chicken broth", "chicken broth"),
    ]
    n = name.lower()
    n = re.sub(r"\(.*?\)", "", n)
    n = re.sub(r"[^a-z0-9\s]", "", n)
    n = re.sub(r"\s+", " ", n).strip()
    for pat, canon in mapping:
        if re.search(pat, n):
            return canon
    blacklist = [
        "boneless", "skinless", "dry", "fresh", "extra",
        "low-sodium", "large", "small", "medium", "freshly", "ground", "sliced", "pieces", "breasts", "breast", "noodles", "beat", "beaten"
    ]
    for word in blacklist:
        n = n.replace(word, "")
    n = re.sub(r"\s+", " ", n).strip()
    return n
ingredient_unit_type = {
    "chicken": "oz",
    "fettuccine": "oz",
    "parmesan cheese": "oz",
    "olive oil": "tbsp",
    "butter": "tbsp",
    "cream cheese": "oz",
    "heavy cream": "cup",
    "garlic": "clove",
    "parsley": "tbsp",
    "lemon juice": "tbsp",
    "chicken broth": "cup",
}
def get_canonical_unit(ingredient: str) -> str:
    return ingredient_unit_type.get(ingredient, None)
def convert_unit(qty, from_unit, to_unit):
    if from_unit == to_unit:
        return qty
    key = (from_unit, to_unit)
    if key in unit_conversions:
        return qty * unit_conversions[key]
    return None  # can't convert
ingredient_count_to_weight = {
    "chicken": 4,  # 1 chicken breast ≈ 4 oz
    "fettuccine": 2,  # 1 cup dry ≈ 2 oz (approximate)
}

def combine_ingredients(items: list) -> list:
    """Combine ingredients with improved fuzzy name and canonical unit logic."""
    agg = {}
    non_numeric = []
    for it in items:
        name_key = canonicalize_name(it.name)
        unit_key = normalize_unit(it.unit)
        qty = parse_quantity(it.quantity)
        if qty is None:
            non_numeric.append((name_key, unit_key, it))
            continue
        canon_unit = get_canonical_unit(name_key)
        if canon_unit is None:
            canon_unit = unit_key  # fallback: use as-is
        # Handle count-to-weight for chicken and fettuccine
        if unit_key in ["piece", "breast", "breasts", ""] and name_key in ingredient_count_to_weight:
            qty = qty * ingredient_count_to_weight[name_key]
            unit_key = canon_unit
        qty_in_canon = convert_unit(qty, unit_key, canon_unit)
        if qty_in_canon is None and unit_key == canon_unit:
            qty_in_canon = qty
        if qty_in_canon is None:
            # can't convert, treat as separate
            key = (name_key, unit_key)
            if key not in agg:
                agg[key] = {'qty': Fraction(0), 'unit': it.unit, 'display_name': it.name}
            agg[key]['qty'] += qty
            if len(it.name) > len(agg[key]['display_name']):
                agg[key]['display_name'] = it.name
            continue
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
    
    # Add link to allLinks here so the index can be added into the class
    allLinks.append(url)
    indexOfUrl = len(allLinks) - 1

    # parse
    items = getInfo(html, indexOfUrl, url)
    if not items:
        messagebox.showinfo("No ingredients", "No ingredients were found on that page.")
        return

    # append parsed items to allThings and update label
    allThings.extend(items)

    makeButton(indexOfUrl)
    displayButtons()
    alphabetizedThings = alphabetizeList(allThings)
    combined = combine_ingredients(alphabetizedThings)
    lines = [f"{it.quantity} {it.unit} {it.name}".strip() for it in combined]
    labelList.configure(text="\n".join(lines))
    entryLink.delete(0, "end")

def linkButtonClicked(buttonUrl, linkIndex):
    global allLinks
    # Remove the items associated with the URL, then remove the URL
    itemsToRemove = []
    for i in range(len(allThings)):
        if allThings[i].url == buttonUrl and allThings[i].index == linkIndex:
            itemsToRemove.append(allThings[i])
   
    for item in itemsToRemove:
        allThings.remove(item)

    # make allLinks at the specified index = None instead of removing it so the indexes don't get messed up
    allLinks[linkIndex] = None

    # Update everything so the display is up to date
    removeButton(buttonUrl, linkIndex)          
    displayButtons()
    alphabetizedThings = alphabetizeList(allThings)
    combined = combine_ingredients(alphabetizedThings)
    lines = [f"{it.quantity} {it.unit} {it.name}".strip() for it in combined]
    labelList.configure(text="\n".join(lines))


def removeButton(removeUrl, removeIndex):
    global index
    for i in range(len(buttons)):
        button = buttons[i]
        endUrlIndex = button['text'].find(", (")
        buttonUrl = button['text'][:endUrlIndex]
        endIndexIndex = button['text'].find(")", endUrlIndex)
        buttonIndex = button['text'][endUrlIndex + len(", ("):endIndexIndex]
        if removeIndex == int(buttonIndex) and removeUrl == buttonUrl:
            button.pack_forget()
            button.destroy()
            buttons.pop(i)
            break

def makeButton(urlIndex):
    global buttons
    """
    for button in buttons:
        button.pack_forget()
        button.destroy()
    buttons = []
    for i in range(len(allLinks)):
        if allLinks[i] != None:
            buttonText = allLinks[i]
            buttons.append(tk.Button(text=buttonText, command=lambda t=buttonText: linkButtonClicked(t)))
            """
    buttonText = allLinks[urlIndex]
    buttons.append(tk.Button(innerFrame, text=f"{buttonText}, ({urlIndex})", command=lambda t = buttonText, i=urlIndex: linkButtonClicked(t, i)))
    


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

    # Instructions and entry at the top
    labelInstructions = tk.Label(root, text="Please enter a link to a recipe page and press Enter", anchor="w", justify=tk.LEFT)
    labelInstructions.pack(fill=tk.X, padx=10, pady=(10,2))

    entryLink = tk.Entry(root, width=80)
    entryLink.pack(fill=tk.X, padx=10, pady=(0,10))

    # Scrollable ingredient list below
    list_frame = tk.Frame(root)
    list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0,10))

    canvas_height = 300  # Set a reasonable height for the scrollable area
    canvas = tk.Canvas(list_frame, borderwidth=0, highlightthickness=0, height=canvas_height)
    scrollbar = tk.Scrollbar(list_frame, orient="vertical", command=canvas.yview)
    scrollable_frame = tk.Frame(canvas)

    def _on_frame_configure(event):
        canvas.configure(scrollregion=canvas.bbox("all"))

    scrollable_frame.bind("<Configure>", _on_frame_configure)

    canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)

    canvas.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")

    # Ingredient label (inside scrollable frame)
    labelList = tk.Label(scrollable_frame, text="", justify=tk.LEFT, anchor="w", wraplength=700)
    labelList.pack(fill=tk.BOTH, anchor="w", expand=True)

    root.bind("<Return>", lambda event: entered())


if __name__ == "__main__":
    main()