import typing as tp

from bs4 import BeautifulSoup, Tag


class Link(tp.NamedTuple):
    href: str
    text: str

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} text={self.text} href={self.href}>"


def find_all_a_tags_with_href(
    parsed: BeautifulSoup, *args: tp.Any, **kwargs: tp.Any
) -> tp.List[Tag]:
    for a in parsed.find_all("a", href=True, *args, **kwargs):
        href = a.get("href")
        if href:
            yield href, a.text


def remove_page_jumps_from_links(
    links: tp.Iterator[Link],
) -> tp.Generator[Link, None, None]:
    for href, text in links:
        yield href.split("#")[0], text


def remove_duplicate_links(links: tp.Iterator[Link]) -> tp.Generator[Link, None, None]:
    seen = set()
    seen_add = seen.add
    for href, text in links:
        if not (href in seen or seen_add(href)):
            yield href, text


def only_internal_links(
    links: tp.Iterator[Link], host: str
) -> tp.Generator[Link, None, None]:
    for href, text in links:
        if host in href:
            yield href, text
