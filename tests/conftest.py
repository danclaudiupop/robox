import pytest

from bs4 import BeautifulSoup


@pytest.fixture
def beautiful_soup():
    def _(html):
        return BeautifulSoup(html, features="html.parser")
    return _