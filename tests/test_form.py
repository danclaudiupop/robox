import pytest
from bs4 import BeautifulSoup

from robox._exceptions import InvalidValue
from robox._form import Form


@pytest.fixture
def parsed_select_form():
    def generate_form(multiple=False):
        select_form = """
            <form>
                <label for="pet-select">Choose a pet:</label>
                <select name="pets" id="pet-select">
                    <option value="dog">Dog</option>
                    <option value="cat">Cat</option>
                </select>
            </form>
        """
        parsed = BeautifulSoup(select_form, features="html.parser")
        if multiple:
            parsed.form.find("select")["multiple"] = "multiple"
        return parsed

    return generate_form


def test_select_multiple(parsed_select_form):
    form = Form(parsed_select_form(multiple=True))
    form.select("pets", options=["dog", "Cat"])
    assert form.to_httpx() == {"params": {"pets": ["cat", "dog"]}}


def test_select_simple(parsed_select_form):
    form = Form(parsed_select_form())
    form.select("pets", options=["dog"])
    assert form.to_httpx() == {"params": {"pets": "dog"}}


def test_select_invalid_option(parsed_select_form):
    with pytest.raises(InvalidValue) as exc:
        form = Form(parsed_select_form(multiple=True))
        form.select("pets", options=["dog", "hamster"])
    expected_message = (
        "The following options: ['hamster'] were not"
        " found on field: <Select name='pets'>"
    )
    assert exc.value.args[0] == expected_message


def test_select_cannot_select_multiple_options(parsed_select_form):
    with pytest.raises(ValueError) as exc:
        form = Form(parsed_select_form())
        form.select("pets", options=["dog", "cat"])
    assert exc.value.args[0] == "Cannot select multiple options!"


@pytest.fixture
def parsed_checkbox_form():
    checkbox_form = """
        <form>
            <div>
                <label for="dog">Dog</label>
                <input type="checkbox" name="animal" id="dog" value="dog" checked>
            </div>
            <div>
                <label for="cat">Cat</label>
                <input type="checkbox" name="animal" id="cat" value="cat">
            </div>
        </form>
    """
    return BeautifulSoup(checkbox_form, features="html.parser")


def test_checkbox(parsed_checkbox_form):
    form = Form(parsed_checkbox_form)
    form.check("animal", values=["Cat"])
    assert form.to_httpx() == {"params": {"animal": ["cat", "dog"]}}


def test_checkbox_invalid_option(parsed_checkbox_form):
    with pytest.raises(InvalidValue) as exc:
        form = Form(parsed_checkbox_form)
        form.check("animal", values=["Foo"])
    assert exc.value.args[0] == "Invalid value for <Checkbox name='animal'>"


def test_checkbox_without_value():
    checkbox_form = """
        <form>
            <div>
                <label for="dog">Dog</label>
                <input type="checkbox" name="dog" id="dog">
            </div>
        </form>
    """
    parsed = BeautifulSoup(checkbox_form, features="html.parser")
    form = Form(parsed)
    form.check("dog", values=["on"])
    assert form.to_httpx() == {"params": {"dog": "on"}}


def test_fill_in_input():
    input_form = """
        <form>
            <label for="name">Name:</label>
            <input type="text" id="name" name="name">
        </form>
    """
    parsed = BeautifulSoup(input_form, features="html.parser")
    form = Form(parsed)
    form.fill_in("Name:", value="foo")
    assert form.to_httpx() == {"params": {"name": "foo"}}


def test_fill_in_textarea():
    textarea_form = """
        <form>
            <label for="story">Tell us your story:</label>
            <textarea id="story" name="story">
                It was a dark and stormy night...
            </textarea>
        </form>
    """
    parsed = BeautifulSoup(textarea_form, features="html.parser")
    form = Form(parsed)
    form.fill_in("story", value="foo")
    assert form.to_httpx() == {"params": {"story": "foo"}}


@pytest.fixture
def parsed_input_file_form():
    def generate_form(multiple=False):
        image_form = """
            <form>
                <label for="doc">Choose a document:</label>
                <input type="file" id="doc" name="doc" accept=".txt">
            </form>
        """
        parsed = BeautifulSoup(image_form, features="html.parser")
        if multiple:
            parsed.form.find("input")["multiple"] = "multiple"
        return parsed

    return generate_form


def test_upload_file(tmp_path, parsed_input_file_form):
    foo_txt = tmp_path / "foo.txt"
    foo_txt.write_text("foo")
    form = Form(parsed_input_file_form())
    with open(foo_txt) as content:
        form.upload("doc", values=[content])
        assert len(form.to_httpx()["params"]["doc"]) == 1


def test_upload_multiple_files(tmp_path, parsed_input_file_form):
    foo_txt = tmp_path / "foo.txt"
    foo_txt.write_text("foo")
    form = Form(parsed_input_file_form(multiple=True))
    with open(foo_txt) as content:
        form.upload("doc", values=[content, content])
        assert len(form.to_httpx()["params"]["doc"]) == 2
