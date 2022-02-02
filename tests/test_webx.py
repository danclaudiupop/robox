import pytest
from bs4 import BeautifulSoup

from robox._controls import Checkbox, Option, Select


class TestCheckboxField:
    def test_checkbox_values(self):
        html = """
            <label for="foo">Bar</label>
            <input type="checkbox" name="foo" value="bar">
        """
        checkbox = Checkbox(BeautifulSoup(html, features="html.parser").find("input"))
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
    def test_is_checked(self, html, is_checked):
        checkbox = Checkbox(BeautifulSoup(html, features="html.parser").find("input"))
        assert checkbox.is_checked() is is_checked

    def test_check(self):
        html = '<input type="checkbox"></input>'
        checkbox = Checkbox(BeautifulSoup(html, features="html.parser").find("input"))
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
    def test_select_with_multiple(self, html, is_multiple):
        select = Select(BeautifulSoup(html, features="html.parser").find("select"))
        assert select.has_multiple() is is_multiple

    def test_select_with_options(self):
        html = """
            <select name="pets">
                <option value="cat">Cat</option>
            </select>
        """
        select = Select(BeautifulSoup(html, features="html.parser").find("select"))
        assert len(select.options()) == 1
        assert isinstance(select.options()[0], Option)

    def test_option(self):
        html = '<option value="cat">Cat</option>'
        option = Option(BeautifulSoup(html, features="html.parser").find("option"))
        assert option.text == "Cat"
        assert option.value == "cat"

    def test_option_is_selected(self):
        html = '<option value="cat" selected>Cat</option>'
        option = Option(BeautifulSoup(html, features="html.parser").find("option"))
        assert option.is_selected()

    def test_select_option(self):
        html = '<option value="cat">Cat</option>'
        option = Option(BeautifulSoup(html, features="html.parser").find("option"))
        option.select()
        assert option.tag.has_attr("selected")
