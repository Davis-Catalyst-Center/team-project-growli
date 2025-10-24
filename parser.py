import urllib.request as req

class Ingredient:
    def __init__(self, quantity, unit, name):
        self.quantity = quantity
        self.unit = unit
        self.name = name


def get_html(url: str) -> str:
    request = req.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with req.urlopen(request) as response:
        data = response.read()
        return data.decode("utf-8")


def get_info(html: str):
    """Parse ingredient triples from html and return list of Ingredient.
    The parser is defensive: stops when markers are not found.
    """
    items = []
    current_index = 0
    while True:
        # Find Quantity
        start_q = html.find('data-ingredient-quantity="true">', current_index)
        if start_q == -1:
            break
        start_q += len('data-ingredient-quantity="true">')
        end_q = html.find('</span>', start_q)
        if end_q == -1:
            break
        quantity = html[start_q:end_q].strip()

        # Find Unit (expect it after quantity)
        start_u = html.find('data-ingredient-unit="true">', end_q)
        if start_u == -1:
            break
        start_u += len('data-ingredient-unit="true">')
        end_u = html.find('</span>', start_u)
        if end_u == -1:
            break
        unit = html[start_u:end_u].strip()

        # Find Name
        start_n = html.find('data-ingredient-name="true">', end_u)
        if start_n == -1:
            break
        start_n += len('data-ingredient-name="true">')
        end_n = html.find('</span>', start_n)
        if end_n == -1:
            break
        name = html[start_n:end_n].strip()

        items.append(Ingredient(quantity, unit, name))
        current_index = end_n

    return items
