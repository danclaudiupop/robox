import logging
import typing as tp

import tenacity
from httpx import HTTPStatusError

from robox import LOG
from robox._exceptions import RetryError
from robox._options import RETRY_METHOD_WHITELIST, RETRY_STATUS_FORCELIST, Options


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


def call_with_retry(open_func: tp.Callable, options: Options) -> tp.Callable:
    if options.retry and open_func.method in RETRY_METHOD_WHITELIST:
        retry_strategy = (
            retry_if_code_in_retry_status_forcelist()
            | tenacity.retry_if_exception_type(options.retry_on_exceptions)
        )
        return tenacity.retry(
            retry=retry_strategy,
            stop=tenacity.stop_after_attempt(options.retry_max_attempts),
            retry_error_callback=raise_retry_error,
            wait=tenacity.wait_exponential(
                multiplier=options.retry_multiplier,
                max=options.retry_max_delay,
            ),
            before=tenacity.before_log(LOG, logging.DEBUG),
            after=tenacity.after_log(LOG, logging.DEBUG),
            reraise=True,
        )(open_func)
    return open_func
