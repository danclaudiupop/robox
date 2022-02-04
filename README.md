[![codecov](https://codecov.io/gh/danclaudiupop/robox/branch/main/graph/badge.svg?token=2DR9K7DR0V)](https://codecov.io/gh/danclaudiupop/robox)
[![Language grade: Python](https://img.shields.io/lgtm/grade/python/g/danclaudiupop/robox.svg?logo=lgtm&logoWidth=18)](https://lgtm.com/projects/g/danclaudiupop/robox/context:python)
[![Run tests](https://github.com/danclaudiupop/robox/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/danclaudiupop/robox/actions/workflows/ci.yml)
[![view examples](https://img.shields.io/badge/learn%20by-examples-0077b3.svg)](https://github.com/danclaudiupop/robox/tree/main/examples)

## Overview
Robox is a simple library with a clean interface for exploring/scraping the web or testing a website you’re developing. Robox can fetch a page, click on links and buttons, and fill out and submit forms. Robox is built on top of two excelent libraries: [httpx](https://www.google.com) and [beautifulsoup4](https://www.crummy.com/software/BeautifulSoup/bs4/doc/).

---
Robox has all the standard features of httpx, including async, plus:
- clean api
- caching
- downloading files
- history


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
        pprint(list(page.get_links_by_text("python")))


asyncio.run(main())
```

Caching can be easily configured via [httpx-cache](https://obendidi.github.io/httpx-cache/)

```python
from robox import Robox, DictCache, FileCache


with Robox(cache=DictCache()) as robox:
    p1 = robox.open("https://httpbin.org/get")
    assert not p1.from_cache
    p2 = robox.open("https://httpbin.org/get")
    assert p2.from_cache
```
