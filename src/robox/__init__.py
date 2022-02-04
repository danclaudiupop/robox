import logging
from pathlib import Path

LOG_DIR = Path("./log")
if not LOG_DIR.exists():
    LOG_DIR.mkdir(parents=True, exist_ok=True)


LOG_FILE = LOG_DIR / f"{__name__.split('.')[-1]}.log"
FILE_HANDLER = logging.FileHandler(LOG_FILE, mode="w", encoding="utf-8")
FILEFORMAT = logging.Formatter(
    "%(asctime)s:[%(threadName)-12.12s]:%(levelname)s:%(name)s:%(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
FILE_HANDLER.setFormatter(FILEFORMAT)

STREAM_HANDLER = logging.StreamHandler()
STREAM_HANDLER.setLevel(logging.DEBUG)
STREAMFORMAT = logging.Formatter("%(asctime)s : %(levelname)s : %(message)s")
STREAM_HANDLER.setFormatter(STREAMFORMAT)

LOG = logging.getLogger(__name__)
LOG.addHandler(FILE_HANDLER)
LOG.addHandler(STREAM_HANDLER)
LOG.setLevel(logging.DEBUG)

from httpx_cache import DictCache, FileCache  # noqa: E402

from robox._client import AsyncRobox, Robox  # noqa: E402

__all__ = ["Robox", "AsyncRobox", "FileCache", "DictCache"]
