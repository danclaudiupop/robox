import pytest

from robox._table import Table

test_data = [
    (
        """
    <table border="1">
        <thead>
            <tr>
                <th colspan="2">The table header</th>
            </tr>
        </thead>
        <tbody>
            <tr>
                <td>The table body</td>
                <td>with two columns</td>
            </tr>
        </tbody>
    </table>
    """,
        [
            ["The table header", "The table header"],
            ["The table body", "with two columns"],
        ],
    ),
    (
        """
    <table border="1">
    <tr>
        <th>A</th>
        <th>B</th>
    </tr>
    <tr>
        <td rowspan="2">C</td>
        <td rowspan="2">D</td>
    </tr>
    <tr>
        <td>E</td>
        <td>F</td>
    </tr>
    <tr>
        <td>G</td>
        <td>H</td>
    </tr>
    </table>
    """,
        [
            ["A", "B", None, None],
            ["C", "D", None, None],
            ["C", "D", "E", "F"],
            ["G", "H", None, None],
        ],
    ),
    (
        """
<table border="1">
    <tr>
        <td rowspan="3" colspan="3">A</td>
        <td>B</td>
        <td>C</td>
        <td>D</td>
    </tr>
    <tr>
        <td colspan="3">E</td>
    </tr>
    <tr>
        <td colspan="1">E</td>
        <td>C</td>
        <td>C</td>
    </tr>
    <tr>
        <td colspan="1">E</td>
        <td>C</td>
        <td>C</td>
        <td>C</td>
        <td>C</td>
        <td>C</td>
    </tr>
</table>
""",
        [
            ["A", "A", "A", "B", "C", "D"],
            ["A", "A", "A", "E", "E", "E"],
            ["A", "A", "A", "E", "C", "C"],
            ["E", "C", "C", "C", "C", "C"],
        ],
    ),
]


@pytest.mark.parametrize(
    "table_html, expected_result", test_data, ids=["t1", "t2", "t3"]
)
def test_table(beautiful_soup, table_html, expected_result):
    parsed = beautiful_soup(table_html)
    table = Table(parsed)
    assert table.get_rows() == expected_result
