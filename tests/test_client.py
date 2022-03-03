import json
from http.cookiejar import Cookie, CookieJar
from unittest.mock import MagicMock, patch

import httpx
import pytest
import respx

from robox import AsyncRobox, DictCache, Options, Robox
from robox._exceptions import ForbiddenByRobots, RetryError

TEST_URL = "https://foo.bar"


def test_open(respx_mock):
    respx_mock.get(TEST_URL).respond(200)
    with Robox() as robox:
        page = robox.open(TEST_URL)
        assert page.status_code == 200


@pytest.mark.asyncio
async def test_async_open(respx_mock):
    async with AsyncRobox() as robox:
        respx_mock.get(TEST_URL).respond(200)
        page = await robox.open(TEST_URL)
        assert page.status_code == 200


def test_refresh(respx_mock):
    respx_mock.get(TEST_URL).respond(200)
    with Robox() as robox:
        robox.open(TEST_URL)
        assert robox.total_requests == 1
        robox.refresh()
        assert robox.total_requests == 2
        assert len(robox.get_history()) == 1


def test_back_without_history():
    with pytest.raises(ValueError):
        with Robox() as robox:
            robox.back()


def test_forward_without_history():
    with pytest.raises(ValueError):
        with Robox() as robox:
            robox.forward()


@respx.mock(base_url=TEST_URL)
def test_back_and_forward(respx_mock):
    first_url = f"{TEST_URL}/1"
    second_url = f"{TEST_URL}/2"
    respx_mock.get("/1").respond(200)
    respx_mock.get("/2").respond(200)
    with Robox() as robox:
        robox.open(first_url)
        robox.open(second_url)
        robox.back()
        robox.current_url == first_url
        robox.forward()
        robox.current_url == second_url


def test_download(respx_mock, tmpdir):
    download_url = f"{TEST_URL}/foo.bin"
    respx_mock.get(download_url).respond(200, text="Foo")
    with Robox() as robox:
        robox.download_file(url=download_url, destination_folder=tmpdir)
        assert (tmpdir / "foo.bin").exists()


@pytest.mark.asyncio
async def test_async_download(respx_mock, tmpdir):
    download_url = f"{TEST_URL}/foo.bin"
    respx_mock.get(download_url).respond(200, text="Foo")
    async with AsyncRobox() as robox:
        await robox.download_file(url=download_url, destination_folder=tmpdir)
    assert (tmpdir / "foo.bin").exists()


def test_raise_on_4xx_5xx(respx_mock):
    respx_mock.get(TEST_URL).respond(400)
    with pytest.raises(httpx.HTTPStatusError):
        Robox(options=Options(raise_on_4xx_5xx=True)).open(TEST_URL)


def test_cache(respx_mock):
    respx_mock.get(TEST_URL).respond(200, html="<html>foo</html>")
    with Robox(options=Options(cache=DictCache())) as robox:
        p1 = robox.open(TEST_URL)
        assert not p1.from_cache
        p2 = robox.open(TEST_URL)
        assert p2.from_cache


@pytest.mark.asyncio
async def test_async_cache(respx_mock):
    respx_mock.get(TEST_URL).respond(200, html="<html>foo</html>")
    async with AsyncRobox(options=Options(cache=DictCache())) as robox:
        p1 = await robox.open(TEST_URL)
        assert not p1.from_cache
        p2 = await robox.open(TEST_URL)
        assert p2.from_cache


def test_robots(respx_mock):
    cm = MagicMock()
    cm.getcode.return_value = 200
    cm.read.return_value = b"User-agent: *\nDisallow: /"
    with patch("urllib.request.urlopen", return_value=cm):
        respx_mock.get(TEST_URL).respond(200)
        with pytest.raises(ForbiddenByRobots):
            with Robox(options=Options(obey_robotstxt=True)) as robox:
                robox.open(TEST_URL)


def test_retry(respx_mock):
    respx_mock.get(TEST_URL).mock(side_effect=httpx.ConnectError)
    with pytest.raises(RetryError):
        with Robox(options=Options(retry=True, retry_max_attempts=1)) as robox:
            robox.open(TEST_URL)


def test_retry_raise_on_4xx_5xx(respx_mock):
    respx_mock.get(TEST_URL).respond(500)
    with pytest.raises(RetryError):
        with Robox(
            options=Options(retry=True, retry_max_attempts=1, raise_on_4xx_5xx=True)
        ) as robox:
            robox.open(TEST_URL)


@pytest.mark.asyncio
async def test_async_retry(respx_mock):
    respx_mock.get(TEST_URL).respond(500)
    with pytest.raises(RetryError):
        async with AsyncRobox(
            options=Options(retry=True, retry_max_attempts=1)
        ) as robox:
            await robox.open(TEST_URL)


def test_retry_recovarable(respx_mock):
    route = respx_mock.get(TEST_URL)
    route.side_effect = [
        httpx.Response(500),
        httpx.Response(200),
    ]
    with Robox(options=Options(retry=True, retry_max_attempts=2)) as robox:
        page = robox.open(TEST_URL)
        assert page.status_code == 200


def test_save_and_load_cookies(respx_mock, tmp_path):
    cookies = CookieJar()
    cookie = Cookie(
        version=0,
        name="example-name",
        value="example-value",
        port=None,
        port_specified=False,
        domain="",
        domain_specified=False,
        domain_initial_dot=False,
        path="/",
        path_specified=True,
        secure=False,
        expires=None,
        discard=True,
        comment=None,
        comment_url=None,
        rest={"HttpOnly": ""},
        rfc2109=False,
    )
    cookies.set_cookie(cookie)

    respx_mock.get(TEST_URL).respond(200)
    with Robox(cookies=cookies) as robox:
        robox.open(TEST_URL)
        robox.save_cookies(tmp_path / "cookies.json")
        with open(tmp_path / "cookies.json") as f:
            loaded_cookies = json.load(f)
        assert loaded_cookies == {"example-name": "example-value"}
        assert len(robox.cookies) == 1

    with Robox() as robox:
        robox.load_cookies(tmp_path / "cookies.json")
        robox.open(TEST_URL)
        assert robox.cookies
        assert len(robox.cookies) == 1
