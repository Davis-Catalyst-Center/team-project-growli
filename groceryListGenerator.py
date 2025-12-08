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
entryIngredient = None
labelList = None
allThings = []
allLinks = []
buttons = []

# Parsing lives in a separate module to make it easy to test without importing tkinter

from parser_1 import Ingredient, getHtml, getInfo

# Simple in-memory user store: username -> password_hash
USER_STORE = {}

def hashPassword(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()

def normalizeName(name: str) -> str:
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
unitConversions = {
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

def normalizeUnit(unit: str) -> str:
    if not unit:
        return ""
    u = unit.lower().strip().replace('.', '')
    u = re.sub(r"[^a-z ]", "", u)
    u = u.replace('fluid ounce', 'fl oz')  # handle 'fluid ounce' as 'fl oz'
    u = u.replace('fl oz', 'fl oz')
    u = u.strip()
    return unitCanonical.get(u, u)


def parseQuantity(q: str) -> Fraction | None:
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


def formatQuantity(frac: Fraction) -> str:
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
def canonicalizeName(name: str) -> str:
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
ingredientUnitType = {
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
def getCanonicalUnit(ingredient: str) -> str:
    return ingredientUnitType.get(ingredient, None)
def convertUnit(qty, fromUnit, toUnit):
    if fromUnit == toUnit:
        return qty
    key = (fromUnit, toUnit)
    if key in unitConversions:
        return qty * unitConversions[key]
    return None  # can't convert
ingredientCountToWeight = {
    "chicken": 4,  # 1 chicken breast ≈ 4 oz
    "fettuccine": 2,  # 1 cup dry ≈ 2 oz (approximate)
}

def combineIngredients(items: list) -> list:
    """Combine ingredients with improved fuzzy name and canonical unit logic."""
    agg = {}
    nonNumeric = []
    for it in items:
        nameKey = canonicalizeName(it.name)
        unitKey = normalizeUnit(it.unit)
        qty = parseQuantity(it.quantity)
        if qty is None:
            nonNumeric.append((nameKey, unitKey, it))
            continue
        canonUnit = getCanonicalUnit(nameKey)
        if canonUnit is None:
            canonUnit = unitKey  # fallback: use as-is
        # Handle count-to-weight for chicken and fettuccine
        if unitKey in ["piece", "breast", "breasts", ""] and nameKey in ingredientCountToWeight:
            qty = qty * ingredientCountToWeight[nameKey]
            unitKey = canonUnit
        qtyInCanon = convertUnit(qty, unitKey, canonUnit)
        if qtyInCanon is None and unitKey == canonUnit:
            qtyInCanon = qty
        if qtyInCanon is None:
            # can't convert, treat as separate
            key = (nameKey, unitKey)
            if key not in agg:
                agg[key] = {'qty': Fraction(0), 'unit': it.unit, 'displayName': it.name}
            agg[key]['qty'] += qty
            if len(it.name) > len(agg[key]['displayName']):
                agg[key]['displayName'] = it.name
            continue
        key = (nameKey, canonUnit)
        if key not in agg:
            agg[key] = {'qty': Fraction(0), 'unit': canonUnit, 'displayName': it.name}
        agg[key]['qty'] += qtyInCanon
        if len(it.name) > len(agg[key]['displayName']):
            agg[key]['displayName'] = it.name
    return [
        Ingredient(
            name=agg[key]['displayName'],
            quantity=formatQuantity(agg[key]['qty']),
            unit=agg[key]['unit']
        )
        for key in agg
    ]
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

def entered(canvas):
    global entryLink, labelList, allThings, allLinks
    url = entryLink.get().strip()
    ingredient = entryIngredient.get().strip()
    if not url and not entryIngredient:
        messagebox.showwarning("Input Error", "Please enter a URL or ingredient")
        return
    
    if not url and ingredient:
        enteredIngredient(ingredient)
        entryIngredient.delete(0, "end")
        # Configure the canvas everytime the user enters, so it matches the content
        innerFrame.bind("<Configure>", lambda e: canvas.config(scrollregion=canvas.bbox(tk.ALL)))
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

    makeButton(indexOfUrl, canvas)
    displayButtons()
    alphabetizedThings = alphabetizeList(allThings)
    combined = combineIngredients(alphabetizedThings)
    lines = [f"{it.quantity} {it.unit} {it.name}".strip() for it in combined]
    labelList.configure(text="\n".join(lines))
    entryLink.delete(0, "end")

    # Configure the canvas everytime the user enters, so it matches the content
    innerFrame.bind("<Configure>", lambda e: canvas.config(scrollregion=canvas.bbox(tk.ALL)))

def enteredIngredient(ingredientName):
    foundThing = False
    itemsToRemove = []
    for i in range(len(allThings)):
        if ingredientName.lower() == allThings[i].name.lower():
            itemsToRemove.append(allThings[i])
            foundThing = True
    if foundThing == False:
        messagebox.showinfo("Could Not Find", "The ingredient entered could not be found, please try again.")
        return
    for item in itemsToRemove:
        allThings.remove(item)

    # Update List
    alphabetizedThings = alphabetizeList(allThings)
    combined = combineIngredients(alphabetizedThings)
    lines = [f"{it.quantity} {it.unit} {it.name}".strip() for it in combined]
    labelList.configure(text="\n".join(lines))



def linkButtonClicked(buttonUrl, linkIndex, canvas):
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
    combined = combineIngredients(alphabetizedThings)
    lines = [f"{it.quantity} {it.unit} {it.name}".strip() for it in combined]
    labelList.configure(text="\n".join(lines))

    # Configure the canvas everytime the user clicks a button, so it matches the content
    innerFrame.bind("<Configure>", lambda e: canvas.config(scrollregion=canvas.bbox(tk.ALL)))


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

def makeButton(urlIndex, canvas):
    global buttons
    buttonText = allLinks[urlIndex]
    buttons.append(tk.Button(innerFrame, text=f"{buttonText}, ({urlIndex})", command=lambda t = buttonText, i=urlIndex: linkButtonClicked(t, i, canvas)))
    


def displayButtons():
    for button in buttons:
        button.pack(pady=6)

def alphabetizeList(list):
    return sorted(list, key=lambda ingredient: ingredient.name.lower())


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
    global entryLink, labelList, innerFrame, entryIngredient

    mainFrame = tk.Frame(root, borderwidth=0, highlightthickness=0)
    mainFrame.pack(fill=tk.BOTH, expand=True)

    canvas = tk.Canvas(mainFrame, borderwidth=0, highlightthickness=0)
    canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    scrollbar = tk.Scrollbar(mainFrame, orient=tk.VERTICAL, command=canvas.yview)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    canvas.config(yscrollcommand=scrollbar.set)

    innerFrame = tk.Frame(canvas, pady=10, padx=15, borderwidth=0, highlightthickness=0)
    canvas.create_window((0,0), window=innerFrame, anchor="nw")

    innerFrame.bind("<Configure>", lambda e: canvas.config(scrollregion=canvas.bbox(tk.ALL)))

    # label for instructions
    labelInstructions = tk.Label(innerFrame, text="Please enter a link to a recipe page and press Enter")
    labelInstructions.pack(pady=6)

    # textbox for input
    entryLink = tk.Entry(innerFrame, width=80)
    entryLink.pack(pady=6)

    # label for second instructions
    labelInstruct2 = tk.Label(innerFrame, text="Already have an ingredient? Type its name below to remove it!", font=("TkDefaultFont", 8))
    labelInstruct2.pack(pady=3)

    # textbox for ingredient input
    entryIngredient = tk.Entry(innerFrame, width=50, font=("TkDefaultFont", 10))
    entryIngredient.pack(pady=3)

    # List
    labelList = tk.Label(innerFrame, text="", justify=tk.LEFT, anchor="w")
    labelList.pack(fill=tk.BOTH, expand=True, padx=10, pady=6)
    

    root.bind("<Return>", lambda event: entered(canvas))


if __name__ == "__main__":
    main()

    #:)