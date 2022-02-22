import re
import tempfile
import typing as tp
import webbrowser
from functools import cached_property
from typing import TYPE_CHECKING
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup, Tag

from robox._controls import Submit
from robox._form import Form
from robox._link import (
    Link,
    find_all_a_tags_with_href,
    remove_duplicate_links,
    remove_page_jumps_from_links,
)
from robox._table import Table

if TYPE_CHECKING:
    from robox import Robox

T = tp.TypeVar("T", bound="Robox")


class BasePage:
    def __init__(self, response: httpx.Response, robox: T) -> None:
        self.response = response
        self.content = self.response.content
        self.url = self.response.url
        self.robox = robox

    @property
    def status_code(self) -> int:
        return self.response.status_code

    @property
    def from_cache(self) -> bool:
        try:
            return self.response.from_cache
        except AttributeError:
            return False

    @cached_property
    def parsed(self) -> BeautifulSoup:
        return BeautifulSoup(self.content, **self.robox.options.soup_kwargs)

    @cached_property
    def title(self) -> str:
        title = self.parsed.title
        if title:
            return title.text

    @cached_property
    def description(self) -> tp.Optional[str]:
        description = self.parsed.find("meta", {"name": "description"})
        if description:
            return description["content"]

    def get_form(self, *args: tp.Any, **kwargs: tp.Any) -> tp.Optional[Form]:
        form = self.parsed.find(name="form", *args, **kwargs)
        if not form:
            raise ValueError("No form found")
        return Form(form)

    def get_forms(self, *args: tp.Any, **kwargs: tp.Any) -> tp.List[Form]:
        forms = self.parsed.find_all(name="form", *args, **kwargs)
        if not forms:
            raise ValueError("No forms found")
        return [Form(form) for form in forms]

    def get_tables(self, *args: tp.Any, **kwargs: tp.Any) -> tp.List[Table]:
        tables = self.parsed.find_all(name="table", *args, **kwargs)
        if not tables:
            raise ValueError("No tables found")
        return [Table(table) for table in tables]

    def _prepare_referer_header(self) -> tp.Dict[str, str]:
        headers = {}
        if "Referer" not in self.response.headers:
            headers["Referer"] = str(self.response.url)
        return headers

    def get_links(
        self, only_internal_links: bool = False, *args: tp.Any, **kwargs: tp.Any
    ) -> tp.Generator[Link, None, None]:
        links = find_all_a_tags_with_href(self.parsed, *args, **kwargs)
        links = remove_page_jumps_from_links(links)
        links = remove_duplicate_links(links)
        if only_internal_links:
            links = only_internal_links(links, self.url.host)
        for href, text in links:
            yield Link(href=href, text=text.strip())

    def get_links_by_regex(
        self, regex: str, *args: tp.Any, **kwargs: tp.Any
    ) -> tp.List[Link]:
        return [
            link
            for link in self.get_links(*args, **kwargs)
            if re.search(regex, link.href)
        ]

    def _get_links_by_text(
        self, text: str, *args: tp.Any, **kwargs: tp.Any
    ) -> tp.List[Link]:
        return [
            link
            for link in self.get_links(*args, **kwargs)
            if text.lower() == link.text.lower()
        ]

    def _get_link_text(self, text: str) -> Link:
        links = self.get_links_by_text(text)
        if not links:
            raise ValueError(f"No link with text {text} found")
        if len(links) > 1:
            raise ValueError(f"Multiple links with text {text} found")
        return links[0]

    def debug_page(self) -> None:
        with tempfile.NamedTemporaryFile("w", delete=False, suffix=".html") as f:
            url = f"file://{f.name}"
            f.write(str(self.parsed))
        webbrowser.open(url)

    def __hash__(self) -> int:
        return hash(tuple([self.parsed, self.url]))

    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, BasePage)
            and self.parsed == other.parsed
            and self.url == other.url
        )

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} url={self.url}>"


class Page(BasePage):
    def submit_form(
        self, form: Form, submit_button: tp.Union[str, Submit] = None
    ) -> "Page":
        payload = form.to_httpx(submit_button)
        headers = self._prepare_referer_header()
        return self.robox.open(
            url=self.response.url.join(form.action),
            method=form.method,
            headers=headers,
            **payload,
        )

    def follow_link(self, link: Link) -> "Page":
        return self.robox.open(urljoin(str(self.url), link.href))

    def follow_link_by_tag(self, tag: Tag) -> "Page":
        return self.robox.open(urljoin(str(self.url), tag["href"]))

    def follow_link_by_text(self, text: str) -> "Page":
        link = self._get_link_text(text)
        return self.follow_link(link)


class AsyncPage(BasePage):
    async def submit_form(
        self, form: Form, submit_button: tp.Union[str, Submit] = None
    ) -> "AsyncPage":
        payload = form.to_httpx(submit_button)
        headers = self._prepare_referer_header()
        return await self.robox.open(
            url=self.response.url.join(form.action),
            method=form.method,
            headers=headers,
            **payload,
        )

    async def follow_link(self, link: Link) -> "AsyncPage":
        return await self.robox.open(urljoin(str(self.url), link.href))

    async def follow_link_by_tag(self, tag: Tag) -> "AsyncPage":
        return await self.robox.open(urljoin(str(self.url), tag["href"]))

    async def follow_link_by_text(self, text: str) -> "AsyncPage":
        link = self._get_link_text(text)
        return await self.follow_link(link)
