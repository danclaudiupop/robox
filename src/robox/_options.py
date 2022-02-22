import typing as tp
from dataclasses import dataclass, field

from httpx import NetworkError, TimeoutException
from httpx_cache.cache import BaseCache

RETRY_STATUS_FORCELIST = (429, 500, 502, 503, 504)
RETRY_METHOD_WHITELIST = ("HEAD", "GET", "OPTIONS")


@dataclass(frozen=True)
class Options:
    user_agent: str = None
    raise_on_4xx_5xx: bool = False
    delay_between_requests: tp.Tuple[float, float] = (0.0, 0.0)
    soup_kwargs: dict = field(default_factory=dict)
    obey_robotstxt: bool = False
    history: bool = True
    cache: tp.Optional[BaseCache] = None
    cacheable_methods: tp.Tuple[str, ...] = ("GET",)
    cacheable_status_codes: tp.Tuple[int, ...] = (200, 203, 300, 301, 308)
    retry: bool = False
    retry_max_attempts: int = 3
    retry_status_forcelist: tp.Tuple[int, ...] = RETRY_STATUS_FORCELIST
    retry_method_whitelist: tp.Tuple[str, ...] = RETRY_METHOD_WHITELIST
    retry_on_exceptions: tp.Tuple[Exception, ...] = (TimeoutException, NetworkError)
    retry_multiplier: int = 1
    retry_max_delay: int = 100

    def __post_init__(self):
        self.soup_kwargs.setdefault("features", "html.parser")
