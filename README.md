[![codecov](https://codecov.io/gh/danclaudiupop/robox/branch/main/graph/badge.svg?token=2DR9K7DR0V)](https://codecov.io/gh/danclaudiupop/robox)
[![Language grade: Python](https://img.shields.io/lgtm/grade/python/g/danclaudiupop/robox.svg?logo=lgtm&logoWidth=18)](https://lgtm.com/projects/g/danclaudiupop/robox/context:python)
[![Run tests](https://github.com/danclaudiupop/robox/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/danclaudiupop/robox/actions/workflows/ci.yml)
[![view examples](https://img.shields.io/badge/learn%20by-examples-0077b3.svg)](https://github.com/danclaudiupop/robox/tree/main/examples)
[![PyPI version](https://badge.fury.io/py/robox.svg)](https://badge.fury.io/py/robox)

## Overview
Robox is a simple library with a clean interface for exploring/scraping the web or testing a website you’re developing. Robox can fetch a page, click on links and buttons, and fill out and submit forms. Robox is built on top of two excelent libraries: [httpx](https://www.python-httpx.org/) and [beautifulsoup4](https://www.crummy.com/software/BeautifulSoup/bs4/doc/).

---
Robox has all the standard features of httpx, including async, plus:
- clean api
- caching
- downloading files
- history
- retry
- parsing tables
- understands robots.txt


## Examples

```python
from robox import Robox


with Robox() as robox:
    page = robox.open("https://httpbin.org/forms/post")
    form = page.get_form()
    form.fill_in("custname", value="foo")
    form.check("topping", values=["Onion"])
    form.choose("size", option="Medium")
    form.fill_in("comments", value="all good in the hood")
    form.fill_in("delivery", value="13:37")
    page = page.submit_form(form)
    assert page.url == "https://httpbin.org/post"
```

or use async version:

```python
import asyncio

from pprint import pprint
from robox import AsyncRobox


async def main():
    async with AsyncRobox(follow_redirects=True) as robox:
        page = await robox.open("https://www.google.com")
        form = page.get_form()
        form.fill_in("q", value="python")
        consent_page = await page.submit_form(form)
        form = consent_page.get_form()
        page = await consent_page.submit_form(form)
        links = page.get_links()
        pprint([link for link in links if "Python" in link.text])


asyncio.run(main())
```

Caching can be easily configured via [httpx-cache](https://obendidi.github.io/httpx-cache/)

```python
from robox import Robox, DictCache, FileCache


with Robox(options=Options(cache=DictCache())) as robox:
    p1 = robox.open("https://httpbin.org/get")
    assert not p1.from_cache
    p2 = robox.open("https://httpbin.org/get")
    assert p2.from_cache
```

Failed requests that are potentially caused by temporary problems such as a connection timeout or HTTP 500 error can be retried:

```python
with Robox(
    options=Options(
        retry=True,
        retry_max_attempts=2,
        raise_on_4xx_5xx=True,
    )
) as robox:
    page = robox.open("https://httpbin.org/status/503,200")
    assert page.status_code == 200
```

Parse tables with rowspan and colspan:
```python
with Robox() as robox:
    page = robox.open("https://html.com/tables/rowspan-colspan/")
    tables = page.get_tables()
    for table in tables:
        pprint(table.get_rows())
```
```bash
[['65', '65', '40', '40', '20', '20'],
 ['Men', 'Women', 'Men', 'Women', 'Men', 'Women'],
 ['82', '85', '78', '82', '77', '81']]
 ...
```

An example on how to reuse authentication state with cookies:
```python
with Robox() as robox:
    page = robox.open("https://news.ycombinator.com/login")
    form = page.get_forms()[0]
    form.fill_in("acct", value=os.getenv("PASSWORD"))
    form.fill_in("pw", value=os.getenv("USERNAME"))
    page.submit_form(form)
    robox.save_cookies("cookies.json")


with Robox() as robox:
    robox.load_cookies("cookies.json")
    page = robox.open("https://news.ycombinator.com/")
    assert page.parsed.find("a", attrs={"id": "logout"})
```

See [examples](https://github.com/danclaudiupop/robox/tree/main/examples) folder for more detailed examples.

## Installation

Using pip:

```sh
pip install robox
```

Robox requires Python 3.8+.
See [Changelog](https://github.com/danclaudiupop/robox/blob/main/CHANGELOG.md) for changes.
