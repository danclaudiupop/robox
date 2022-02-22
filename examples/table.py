from pprint import pprint

from robox import Robox

with Robox() as robox:
    page = robox.open("https://html.com/tables/rowspan-colspan/")
    tables = page.get_tables()
    for table in tables:
        pprint(table.get_rows())
