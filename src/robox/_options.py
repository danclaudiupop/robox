import logging
import typing as tp
from dataclasses import dataclass, field

import tenacity
from httpx import HTTPStatusError, NetworkError, TimeoutException
from httpx_cache.cache import BaseCache

from robox import LOG
from robox._exceptions import RetryError

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

    def _init_retry(self, open_func: tp.Callable) -> tp.Callable:
        if self.retry and open_func.method in RETRY_METHOD_WHITELIST:
            retry_strategy = (
                retry_if_code_in_retry_status_forcelist()
                | tenacity.retry_if_exception_type(self.retry_on_exceptions)
            )
            return tenacity.retry(
                retry=retry_strategy,
                stop=tenacity.stop_after_attempt(self.retry_max_attempts),
                retry_error_callback=raise_retry_error,
                wait=tenacity.wait_exponential(
                    multiplier=self.retry_multiplier,
                    max=self.retry_max_delay,
                ),
                before=tenacity.before_log(LOG, logging.DEBUG),
                after=tenacity.after_log(LOG, logging.DEBUG),
                reraise=True,
            )(open_func)
        return open_func


def raise_retry_error(retry_state: tenacity.RetryCallState) -> None:
    outcome = retry_state.outcome
    msg = "Retry failed on {} after {} attempts"
    if outcome.failed:
        url = outcome.exception().request.url
        raise RetryError(msg.format(url, outcome.attempt_number))
    page = outcome.result()
    if page.status_code in RETRY_STATUS_FORCELIST:
        raise RetryError(msg.format(page.response.request.url, outcome.attempt_number))


def is_exception_with_retry_status_forcelist(e: Exception) -> bool:
    return (
        isinstance(e, HTTPStatusError)
        and e.response.status_code in RETRY_STATUS_FORCELIST
    )


class retry_if_code_in_retry_status_forcelist(tenacity.retry_base):
    def __call__(self, retry_state: tenacity.RetryCallState) -> bool:
        if retry_state.outcome.failed:
            exception = retry_state.outcome.exception()
            return is_exception_with_retry_status_forcelist(exception)
        page = retry_state.outcome.result()
        return page.status_code in RETRY_STATUS_FORCELIST
