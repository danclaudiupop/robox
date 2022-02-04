import typing as tp
from functools import lru_cache, singledispatch

from bs4.element import Tag

from robox._controls import (
    Checkbox,
    Field,
    Fields,
    File,
    Input,
    Radio,
    Select,
    Submit,
    Textarea,
)
from robox._exceptions import InvalidValue


class Form:
    def __init__(self, parsed_form: Tag) -> None:
        self.parsed_form = parsed_form

    @property
    def action(self) -> str:
        return self.parsed_form.get("action", "")

    @property
    def method(self) -> str:
        return self.parsed_form.get("method", "GET")

    def fill_in(self, locator: str, *, value: str) -> None:
        self.fields.get(locator).value = value

    def check(self, locator: str, *, values: tp.List[str]) -> None:
        assert isinstance(values, list)
        checkboxes = self.fields.filter_by(locator, Checkbox)
        checked = False
        for value in values:
            for checkbox in checkboxes:
                if value in checkbox.values() or (value == "on" and not checkbox.value):
                    checkbox.check()
                    checked = True
                    break
        if not checked:
            raise InvalidValue(f"Invalid value for {checkbox}")

    def choose(self, locator: str, *, option: str) -> None:
        radios = self.fields.filter_by(locator, Radio)
        checked = False
        for radio in radios:
            if option in radio.values():
                radio.check()
                checked = True
                break
        if not checked:
            raise InvalidValue(f"Option: '{option}' not found in {radios}")

    def select(self, locator: str, *, options: tp.List[str]) -> None:
        assert isinstance(options, list)
        select = self.fields.get(locator, Select)
        if not select.has_multiple():
            if len(options) > 1:
                raise ValueError("Cannot select multiple options!")

        available_options = {}
        for option in select.options():
            available_options[option.text] = option
            available_options[option.value] = option

        not_found_options = []
        for option in options:
            if option in available_options:
                available_options[option].select()
            else:
                not_found_options.append(option)
        if not_found_options:
            raise InvalidValue(
                f"The following options: {not_found_options} were"
                f" not found on field: {select}"
            )

    def upload(self, locator: str, *, values: tp.List[str]) -> None:
        assert isinstance(values, list)
        field = self.fields.get(locator, File)
        if not field.has_multiple():
            if len(values) > 1:
                raise ValueError("Cannot select multiple options!")
        field.value = values

    @property
    @lru_cache
    def fields(self) -> Fields:
        mapping = {
            "textarea": Textarea,
            "select": Select,
            "radio": Radio,
            "checkbox": Checkbox,
            "file": File,
        }
        fields = Fields()
        for field in self.parsed_form.find_all(
            ("input", "button", "select", "textarea")
        ):
            if not field.attrs.get("name"):
                continue

            tag_type = field.attrs.get("type")

            klass = mapping.get(field.name) or mapping.get(tag_type)
            if klass:
                fields.add(klass(field))
            elif field.name in ("input", "button"):
                if tag_type == "submit":
                    fields.add(Submit(field))
                else:
                    fields.add(Input(field))
        return fields

    def _set_default_submit(self, submit_button: tp.Union[str, Submit]) -> None:
        if isinstance(submit_button, Submit):
            if submit_button in self.fields:
                submit_button.is_default = True
            else:
                raise LookupError(
                    f"Submit button: {submit_button} not found in {self.fields}"
                )
        else:
            submit = self.fields.get(locator=submit_button, field_type=Submit)
            submit.is_default = True

    def to_httpx(
        self, submit_button: tp.Union[str, Submit] = None
    ) -> tp.Dict[str, tp.Any]:
        payload = {}
        key = "params" if self.method.lower() == "get" else "data"
        payload[key] = {}
        if submit_button:
            self._set_default_submit(submit_button)
        for field in self.fields.list():
            if not field.disabled or not field.readonly:
                serialize(field, payload, key)
        return payload


@singledispatch
def serialize(field: Field, payload: tp.Dict[str, dict], key: str) -> None:
    raise NotImplementedError(f"Field: {field} not supported")


@serialize.register(File)
def _(field: Field, payload: tp.Dict[str, dict], key="files") -> None:
    for value in field.value:
        payload[key].setdefault(field.name, []).append(value)


@serialize.register(Input)
@serialize.register(Textarea)
def _(field: Field, payload: tp.Dict[str, dict], key: str) -> None:
    payload[key].update({field.name: field.value})


@serialize.register(Radio)
def _(field: Field, payload: tp.Dict[str, dict], key: str) -> None:
    if field.is_checked():
        payload[key].update({field.name: field.value})


@serialize.register(Checkbox)
def _(field: Field, payload: tp.Dict[str, dict], key: str) -> None:
    if field.is_checked():
        if not field.value:
            payload[key].update({field.name: "on"})
        else:
            payload[key].setdefault(field.name, []).append(field.value)
            payload[key][field.name].sort()


@serialize.register(Select)
def _(field: Field, payload: tp.Dict[str, dict], key: str) -> None:
    values = [option.value for option in field.options() if option.is_selected()]
    if not field.has_multiple():
        payload[key].update({field.name: values[0]})
    else:
        for value in values:
            payload[key].setdefault(field.name, []).append(value)
        payload[key][field.name].sort()


@serialize.register(Submit)
def _(field: Field, payload: tp.Dict[str, dict], key: str) -> None:
    if field.is_default:
        payload[key].update({field.name: field.value})
