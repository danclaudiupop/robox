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
