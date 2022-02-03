import pytest
from bs4 import BeautifulSoup

from robox._controls import Checkbox, Option, Select


class TestCheckboxField:
    def test_checkbox_values(self, beautiful_soup):
        html = """
            <label for="foo">Bar</label>
            <input type="checkbox" name="foo" value="bar">
        """
        tag = beautiful_soup(html).find("input")
        checkbox = Checkbox(tag)
        assert list(checkbox.values()) == ["bar", "Bar"]

    def test_checkbox_without_value_attribute(self):
        html = '<input type="checkbox" name="foo"></input>'
        checkbox = Checkbox(BeautifulSoup(html, features="html.parser").find("input"))
        assert list(checkbox.values()) == []

    @pytest.mark.parametrize(
        "html, is_checked",
        [
            ('<input type="checkbox"></input>', False),
            ('<input type="checkbox" checked></input>', True),
        ],
    )
    def test_is_checked(self, html, is_checked, beautiful_soup):
        tag = beautiful_soup(html).find("input")
        checkbox = Checkbox(tag)
        assert checkbox.is_checked() is is_checked

    def test_check(self, beautiful_soup):
        html = '<input type="checkbox"></input>'
        tag = beautiful_soup(html).find("input")
        checkbox = Checkbox(tag)
        checkbox.check()
        assert checkbox.tag.has_attr("checked")


class TestSelectField:
    @pytest.mark.parametrize(
        "html, is_multiple",
        [
            ('<select name="pets"></select>', False),
            ('<select name="pets" multiple></select>', True),
        ],
    )
    def test_select_with_multiple(self, html, is_multiple, beautiful_soup):
        tag = beautiful_soup(html).find("select")
        select = Select(tag)
        assert select.has_multiple() is is_multiple

    def test_select_with_options(self, beautiful_soup):
        html = """
            <select name="pets">
                <option value="cat">Cat</option>
            </select>
        """
        tag = beautiful_soup(html).find("select")
        select = Select(tag)
        assert len(select.options()) == 1
        assert isinstance(select.options()[0], Option)

    def test_option(self, beautiful_soup):
        html = '<option value="cat">Cat</option>'
        tag = beautiful_soup(html).find("option")
        option = Option(tag)
        assert option.text == "Cat"
        assert option.value == "cat"

    def test_option_is_selected(self, beautiful_soup):
        html = '<option value="cat" selected>Cat</option>'
        tag = beautiful_soup(html).find("option")
        option = Option(tag)
        assert option.is_selected()

    def test_select_option(self, beautiful_soup):
        html = '<option value="cat">Cat</option>'
        tag = beautiful_soup(html).find("option")
        option = Option(tag)
        option.select()
        assert option.tag.has_attr("selected")
