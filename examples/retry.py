import asyncio

from robox import AsyncRobox, Options, Robox


async def main():
    async with AsyncRobox(
        options=Options(
            retry=True,
            retry_max_attempts=2,
        )
    ) as robox:
        await robox.open("https://httpbin.org/status/500")


asyncio.run(main())


with Robox(
    options=Options(
        retry=True,
        retry_max_attempts=2,
        raise_on_4xx_5xx=True,
    )
) as robox:
    robox.open("https://httpbin.org/status/503,200")
