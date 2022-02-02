import re
import tempfile
import typing as tp
import webbrowser
from functools import cached_property
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


class BasePage:
    def __init__(self, response: httpx.Response, robox) -> None:
        self.response = response
        self.content = self.response.content
        self.url = self.response.url
        self.robox = robox

    @cached_property
    def parsed(self) -> BeautifulSoup:
        return BeautifulSoup(self.content, **self.robox.soup_kwargs)

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
        if form:
            return Form(form)

    def get_forms(self, *args, **kwargs) -> tp.List[Form]:
        forms = self.find_all(name="form", *args, **kwargs)
        return [Form(form) for form in forms]

    def _prepare_referer_header(self) -> tp.Dict[str, str]:
        headers = {}
        if "Referer" not in self.response.headers:
            headers["Referer"] = str(self.response.url)
        return headers

    def get_links(
        self, only_internal_links: bool = False, *args, **kwargs
    ) -> tp.Generator[Link, None, None]:
        links = find_all_a_tags_with_href(self.parsed, *args, **kwargs)
        links = remove_page_jumps_from_links(links)
        links = remove_duplicate_links(links)
        if only_internal_links:
            links = only_internal_links(links, self.url.host)
        for href, text in links:
            yield Link(href=href, text=text.strip())

    def get_links_by_regex(self, regex: str, *args, **kwargs) -> tp.List[Link]:
        return [
            link
            for link in self.get_links(*args, **kwargs)
            if re.search(regex, link.href)
        ]

    def get_links_by_text(self, text: str, *args, **kwargs) -> tp.List[Link]:
        return [
            link
            for link in self.get_links(*args, **kwargs)
            if link.text.lower() == text.lower()
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
            url = "file://" + f.name
            f.write(str(self.parsed))
        webbrowser.open(url)

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
        link = self._prepare_link_text(text)
        return self.follow_link(link)


class AsyncPage(BasePage):
    async def submit_form(
        self, form: Form, submit_button: tp.Union[str, Submit] = None
    ) -> "AsyncPage":
        payload = form.to_httpx(submit_button)
        headers = self._get_referer_header()
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
