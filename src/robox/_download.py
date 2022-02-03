import asyncio
import functools
import mimetypes
from pathlib import Path
from typing import Callable

import aiofiles
import httpx

from robox import LOG


def get_filename_from_url(response: httpx.Response) -> str:
    url = response.request.url
    filename = url.path.split("/")[-1]

    if Path(filename).suffix:
        return filename

    content_type = response.headers.get("content-type")
    if content_type is None:
        return filename

    extension = mimetypes.guess_extension(content_type)
    if extension is None:
        return filename

    return f'{filename.rstrip(".")}{extension}'


def setup_destination(url, destination_folder: str) -> str:
    destination = Path(destination_folder).expanduser()
    if (destination / url.split("/")[-1]).is_file():
        return

    destination.mkdir(parents=True, exist_ok=True)
    return destination


def handle_error(func: Callable) -> Callable:
    @functools.wraps(func)
    def wrapper(client, url, destination_folder):
        destination = setup_destination(url, destination_folder)
        try:
            if asyncio.iscoroutinefunction(func):

                async def _():
                    return await func(client, url, destination)

                return _()
            else:
                return func(client, url, destination)
        except Exception as e:
            LOG.error(
                f"Downloading from {url} has failed!\nThe exception thrown is {e}"
            )
            raise

    return wrapper


@handle_error
def download_file(client: httpx.Client, url: str, destination_folder: str) -> str:
    with client.stream("GET", url) as response:
        response.raise_for_status()
        filename = get_filename_from_url(response)
        file = destination_folder / filename

        with file.open("wb") as out_file:
            for chunk in response.iter_raw():
                out_file.write(chunk)
    return filename


@handle_error
async def async_download_file(
    client: httpx.AsyncClient, url: str, destination_folder: str
) -> str:
    async with client.stream("GET", url) as response:
        response.raise_for_status()
        filename = get_filename_from_url(response)
        file = destination_folder / filename

        async with aiofiles.open(file, "wb") as out_file:
            async for data in response.aiter_bytes():
                if data:
                    await out_file.write(data)
    return filename
