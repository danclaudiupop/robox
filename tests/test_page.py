from types import SimpleNamespace

import pytest
from httpcore import URL
from httpx import Response

from robox import Options
from robox._page import Form, Page


class MockResponse(Response):
    def url(self) -> URL:
        return "https://example.com"


robox = SimpleNamespace(options=Options())


@pytest.fixture
def page():
    def _page(html):
        return Page(response=MockResponse(200, html=html), robox=robox)

    return _page


def test_get_links(page):
    page = page(html='<html><a href="https://foo.bar">foo</a></html>')
    links = list(page.get_links())
    assert len(links) == 1
    assert links[0].href == "https://foo.bar"
    assert links[0].text == "foo"


def test_get_links_by_regex(page):
    page = page(html='<html><a href="https://foo.bar">foo</a></html>')
    links = list(page.get_links_by_regex(r"foo"))
    assert len(links) == 1
    assert links[0].href == "https://foo.bar"
    assert links[0].text == "foo"


def test_get_form(page):
    page = page(html="<html><form></form></html>")
    form = page.get_form()
    assert isinstance(form, Form)


def test_get_forms(page):
    page = page(html="<html><form></form><form></form></html>")
    forms = page.get_forms()
    assert len(forms) == 2
    assert isinstance(forms[0], Form)
    assert isinstance(forms[1], Form)
