import reprlib
import typing as tp
from itertools import product

from bs4.element import Tag


class Table:
    def __init__(self, parsed_table: Tag) -> None:
        self.parsed_table = parsed_table

    def _parse_tr(self) -> tp.List[Tag]:
        return self.parsed_table.find_all("tr")

    def get_rows(self) -> tp.List[tp.List[str]]:
        rowspans = []  # track pending rowspans
        rows = self._parse_tr()

        # first scan, see how many columns we need
        colcount = 0
        for r, row in enumerate(rows):
            cells = row.find_all(["td", "th"], recursive=False)
            colcount = max(
                colcount,
                sum(int(c.get("colspan", 1)) or 1 for c in cells[:-1])
                + len(cells[-1:])
                + len(rowspans),
            )
            rowspans += [int(c.get("rowspan", 1)) or len(rows) - r for c in cells]
            rowspans = [s - 1 for s in rowspans if s > 1]

        table = [[None] * colcount for _ in rows]

        # fill matrix from row data
        rowspans = {}
        for row, row_elem in enumerate(rows):
            span_offset = 0
            for col, cell in enumerate(
                row_elem.find_all(["td", "th"], recursive=False)
            ):
                col += span_offset
                while rowspans.get(col, 0):
                    span_offset += 1
                    col += 1

                # fill table data
                rowspan = rowspans[col] = int(cell.get("rowspan", 1)) or len(rows) - row
                colspan = int(cell.get("colspan", 1)) or colcount - col
                # next column is offset by the colspan
                span_offset += colspan - 1
                value = cell.get_text()
                for drow, dcol in product(range(rowspan), range(colspan)):
                    try:
                        table[row + drow][col + dcol] = value
                        rowspans[col + dcol] = rowspan
                    except IndexError:
                        pass

            # update rowspan bookkeeping
            rowspans = {c: s - 1 for c, s in rowspans.items() if s > 1}

        return table

    def __repr__(self) -> str:
        return reprlib.repr(self.get_rows())
