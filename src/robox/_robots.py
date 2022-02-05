import typing as tp
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

robotstxt = {}


def resolve_robotstxt_url(url: str) -> str:
    url_struct = urlparse(url)
    return f"{url_struct.scheme}://{url_struct.netloc}/robots.txt"


def ask_robots(url: str, useragent: str = "*") -> tp.Tuple[bool, tp.Optional[int]]:
    r_url = resolve_robotstxt_url(url)
    if r_url not in robotstxt:
        robotstxt[r_url] = RobotFileParser()
        robotstxt[r_url].set_url(r_url)
        robotstxt[r_url].read()
    return robotstxt[r_url].can_fetch(useragent, url), robotstxt[r_url].crawl_delay(
        useragent
    )


async def async_ask_robots(
    url: str, useragent: str = "*"
) -> tp.Tuple[bool, tp.Optional[int]]:
    return ask_robots(url, useragent)
