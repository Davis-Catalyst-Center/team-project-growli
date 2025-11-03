import urllib.request as req
try:
    import requests
except ImportError:
    requests = None

class Ingredient:
    def __init__(self, quantity, unit, name):
        self.quantity = quantity
        self.unit = unit
        self.name = name


def getHtml(url: str) -> str:
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Referer": url,
        "Connection": "keep-alive",
        "DNT": "1",
    }
    if requests:
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raiseForStatus()
        return resp.text
    else:
        request = req.Request(url, headers=headers)
        with req.urlopen(request) as response:
            data = response.read()
            return data.decode("utf-8")


def getInfo(html: str, url: str = None):
    """
    Parse ingredient triples from html and return list of Ingredient.
    Dispatches to a site-specific parser if known, else tries all parsers.
    """
    def parseSite1(html):
        # Original parser for site with data-ingredient-* attributes
        items = []
        currentIndex = 0
        while True:
            startQ = html.find('data-ingredient-quantity="true">', currentIndex)
            if startQ == -1:
                break
            startQ += len('data-ingredient-quantity="true">')
            endQ = html.find('</span>', startQ)
            if endQ == -1:
                break
            quantity = html[startQ:endQ].strip()

            startU = html.find('data-ingredient-unit="true">', endQ)
            if startU == -1:
                break
            startU += len('data-ingredient-unit="true">')
            endU = html.find('</span>', startU)
            if endU == -1:
                break
            unit = html[startU:endU].strip()

            startN = html.find('data-ingredient-name="true">', endU)
            if startN == -1:
                break
            startN += len('data-ingredient-name="true">')
            endN = html.find('</span>', startN)
            if endN == -1:
                break
            name = html[startN:endN].strip()

            items.append(Ingredient(quantity, unit, name))
            currentIndex = endN
        return items

    def parseSite2(html):
        # Example: Allrecipes.com style (li class="ingredients-item")
        import re
        items = []
        pattern = re.compile(r'<li[^>]*class="[^\"]*ingredients-item[^\"]*"[^>]*>(.*?)</li>', re.DOTALL)
        for match in pattern.finditer(html):
            li = match.group(1)
            # Try to extract quantity, unit, name from text
            text = re.sub(r'<[^>]+>', '', li).strip()
            # Naive split: e.g. "1 cup sugar" -> [1, cup, sugar]
            parts = text.split()
            if len(parts) >= 3:
                quantity, unit = parts[0], parts[1]
                name = ' '.join(parts[2:])
            elif len(parts) == 2:
                quantity, unit = parts[0], ''
                name = parts[1]
            elif len(parts) == 1:
                quantity, unit, name = '', '', parts[0]
            else:
                continue
            items.append(Ingredient(quantity, unit, name))
        return items


    def parseSite3(html):
        # tastesbetterfromscratch.com style (li class="wprm-recipe-ingredient")
        import re
        items = []
        pattern = re.compile(r'<li[^>]*class="[^"]*wprm-recipe-ingredient[^"]*"[^>]*>(.*?)</li>', re.DOTALL)
        for match in pattern.finditer(html):
            li = match.group(1)
            # Extract amount, unit, name
            amount = ''
            unit = ''
            name = ''
            mAmount = re.search(r'<span[^>]*class="[^"]*wprm-recipe-ingredient-amount[^"]*"[^>]*>(.*?)</span>', li)
            if mAmount:
                amount = mAmount.group(1).strip()
            mUnit = re.search(r'<span[^>]*class="[^"]*wprm-recipe-ingredient-unit[^"]*"[^>]*>(.*?)</span>', li)
            if mUnit:
                unit = mUnit.group(1).strip()
            mName = re.search(r'<span[^>]*class="[^"]*wprm-recipe-ingredient-name[^"]*"[^>]*>(.*?)</span>', li)
            if mName:
                name = mName.group(1).strip()
                # Remove any HTML tags from name
                import re as _re
                name = _re.sub(r'<[^>]+>', '', name)
            if name:
                items.append(Ingredient(amount, unit, name))
        return items

    # Dispatch based on URL or HTML signature
    if url:
        if 'allrecipes.' in url:
            items = parseSite2(html)
            if items:
                return items
        if 'tastesbetterfromscratch.' in url:
            items = parseSite3(html)
            if items:
                return items
        # Add more site checks here

    # Try all known parsers, return first with results
    for parser in [parseSite1, parseSite2, parseSite3]:
        items = parser(html)
        if items:
            return items
    return []
