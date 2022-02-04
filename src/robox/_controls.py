from typing import Generator, Iterator, List, Optional, Sequence, TypeVar, overload

import bs4

from robox._exceptions import MultipleFieldsReturned


class Field:
    def __init__(self, tag: bs4.element.Tag) -> None:
        self.tag = tag
        self._value = self.tag.get("value")

    @property
    def disabled(self) -> bool:
        return "disabled" in self.tag.attrs

    @property
    def readonly(self) -> bool:
        return "readonly" in self.tag.attrs

    @property
    def name(self) -> str:
        return self.tag.get("name")

    @property
    def id(self) -> str:
        return self.tag.get("id")

    @property
    def label(self) -> Optional[str]:
        if label := self.tag.find_previous("label"):
            return label.text.strip()

    @property
    def placeholder(self) -> str:
        return self.tag.get("placeholder")

    def has_multiple(self) -> bool:
        return self.tag.has_attr("multiple")

    @property
    def value(self) -> Optional[str]:
        return self._value or ""

    @value.setter
    def value(self, value: str) -> None:
        self._value = value

    def __repr__(self) -> str:
        return f"<{type(self).__name__} name={self.name!r}>"


class Input(Field):
    ...


class Submit(Field):
    def __init__(self, tag: bs4.element.Tag) -> None:
        super().__init__(tag)
        self.is_default = False


class Textarea(Field):
    def __init__(self, tag: bs4.element.Tag) -> None:
        super().__init__(tag)
        self.value = self.tag.text.rstrip("\r").rstrip("\n")


class Checkable:
    def is_checked(self) -> bool:
        return self.tag.has_attr("checked")

    def check(self) -> None:
        self.tag["checked"] = "checked"

    def values(self) -> List[str]:
        return list(filter(None, [self.value, self.label, self.id]))


class Checkbox(Input, Checkable):
    ...


class Radio(Input, Checkable):
    ...


class Option:
    def __init__(self, tag: bs4.element.Tag) -> None:
        self.tag = tag

    @property
    def text(self) -> str:
        return self.tag.text.strip()

    @property
    def value(self) -> Optional[str]:
        return self.tag.get("value")

    def is_selected(self) -> bool:
        return self.tag.has_attr("selected")

    def select(self) -> None:
        self.tag["selected"] = "selected"


class Select(Field):
    def options(self) -> List[Option]:
        return [Option(o) for o in self.tag.find_all("option")]


class File(Input):
    @Field.value.setter
    def value(self, values: List[str]) -> None:
        _values = []
        for value in values:
            if hasattr(value, "read"):
                _values.append(value)
            elif isinstance(value, str):
                _values.append(open(value))
            else:
                raise ValueError("Value must be a file object or file path")
        self._value = _values


T = TypeVar("T")


class Fields(Sequence[T]):
    def __init__(self) -> None:
        self._container: Sequence[T] = []

    def __iter__(self) -> Iterator[Field]:
        for field in self._container:
            yield field

    def __len__(self) -> int:
        return len(self._container)

    @overload
    def __getitem__(self, idx: int) -> T:
        ...

    @overload
    def __getitem__(self, s: slice) -> Sequence[T]:
        ...

    def __getitem__(self, index: int):
        return self._container[index]

    def add(self, field: Field) -> None:
        if not isinstance(field, Field):
            raise ValueError('Argument "field" must be an instance of Field')
        self._container.append(field)

    def get(self, locator: str, field_type: Field = None) -> Field:
        result = self.filter_by(locator, field_type)
        if len(result) > 1:
            raise MultipleFieldsReturned(f"Multiple fields returned for {field_type}")
        return result[0]

    def get_submits(self) -> List[Submit]:
        return list(self.filter_by_type(self._container, Submit))

    def filter_by(self, locator: str, field_type: Field = None) -> List[Field]:
        fields = self.filter_by_locator(self._container, locator)
        if field_type:
            fields = self.filter_by_type(fields, field_type)
        fields = list(fields)
        if not fields:
            raise LookupError(f"No fields found for {locator}")
        return fields

    @staticmethod
    def filter_by_locator(
        fields: List[Field], locator: str
    ) -> Generator[Field, None, None]:
        for field in fields:
            if locator in (field.name, field.id, field.label, field.value.strip()):
                yield field

    @staticmethod
    def filter_by_type(
        fields: List[Field], field_type: Field
    ) -> Generator[Field, None, None]:
        for field in fields:
            if isinstance(field, field_type):
                yield field

    def list(self) -> List[Field]:
        return self._container
