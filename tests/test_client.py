import httpx
import pytest
import respx

from robox import AsyncRobox, Robox

TEST_URL = "https://foo.bar"


def test_open(respx_mock):
    respx_mock.get(TEST_URL).respond(200)
    robox = Robox()
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
    robox = Robox()
    robox.open(TEST_URL)
    assert robox.total_requests == 1
    robox.refresh()
    assert robox.total_requests == 2
    assert len(robox.get_history()) == 1


def test_back_without_history():
    with pytest.raises(ValueError):
        robox = Robox()
        robox.back()


def test_forward_without_history():
    with pytest.raises(ValueError):
        robox = Robox()
        robox.forward()


@respx.mock(base_url=TEST_URL)
def test_back_and_forward(respx_mock):
    first_url = f"{TEST_URL}/1"
    second_url = f"{TEST_URL}/2"
    respx_mock.get("/1").respond(200)
    respx_mock.get("/2").respond(200)
    robox = Robox()
    robox.open(first_url)
    robox.open(second_url)
    robox.back()
    robox.current_url == first_url
    robox.forward()
    robox.current_url == second_url


def test_download(respx_mock, tmpdir):
    download_url = f"{TEST_URL}/foo.bin"
    respx_mock.get(download_url).respond(200, text="Foo")
    robox = Robox()
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
        Robox(raise_on_4xx_5xx=True).open(TEST_URL)
