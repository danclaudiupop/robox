import asyncio
import itertools
import json
import random
import time
import typing as tp
from pathlib import Path

import httpx
from httpx._client import USE_CLIENT_DEFAULT, UseClientDefault
from httpx._config import (
    DEFAULT_LIMITS,
    DEFAULT_MAX_REDIRECTS,
    DEFAULT_TIMEOUT_CONFIG,
    Limits,
    Proxy,
)
from httpx._models import URL
from httpx._types import (
    AuthTypes,
    CertTypes,
    CookieTypes,
    HeaderTypes,
    ProxiesTypes,
    QueryParamTypes,
    RequestContent,
    RequestData,
    RequestFiles,
    TimeoutTypes,
    URLTypes,
    VerifyTypes,
)
from httpx_cache import AsyncCacheControlTransport, CacheControlTransport

from robox import LOG
from robox._download import async_download_file, download_file
from robox._exceptions import ForbiddenByRobots, RoboxError
from robox._history import BrowserHistory
from robox._options import Options
from robox._page import AsyncPage, Page
from robox._retry import call_with_retry
from robox._robots import ask_robots, async_ask_robots


class RoboxMixin:
    @property
    def user_agent(self) -> str:
        return self._user_agent

    @user_agent.setter
    def user_agent(self, user_agent: str) -> None:
        self.headers["user-agent"] = user_agent

    def get_history(self) -> tp.List[tp.Union[Page, AsyncPage]]:
        return self.history.get_locations()

    @property
    def current_url(self) -> URL:
        if latest_entry := self.history.latest_entry():
            return latest_entry.url
        else:
            raise RoboxError("Not tracking history")

    def save_cookies(self, filename: str) -> None:
        cookies = {}
        for cookie in self.cookies.jar:
            cookies[cookie.name] = cookie.value
        with open(filename, "w") as f:
            json.dump(cookies, f)

    def load_cookies(self, filename: str) -> None:
        if not Path(filename).is_file():
            return None
        with open(filename, "r") as f:
            cookies = httpx.Cookies(json.load(f))
            self.cookies = cookies

    def _increment_request_counter(self) -> None:
        self.total_requests = next(self._request_counter)

    def _build_page_response(
        self, response: httpx.Response, page_cls: tp.Union[Page, AsyncPage]
    ) -> tp.Union[Page, AsyncPage]:
        self._format_response_log(response)
        if self.options.raise_on_4xx_5xx:
            try:
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:
                LOG.error(
                    f"Error response {exc.response.status_code} "
                    f"while requesting {exc.request.url!r}."
                )
                raise exc

        page = page_cls(response, robox=self)
        if self.options.history:
            self.history.location = page
        return page

    @staticmethod
    def _format_response_log(response: httpx.Response) -> None:
        def format_headers(d):
            return "\n".join(f"{k}: {v}" for k, v in d.items())

        msg = (
            f"\n----- REPORT START -----\n"
            f"Method: {response.request.method}\n"
            f"URL: {response.url}\n"
            f"Time: {response.elapsed.total_seconds():.3f}s\n"
            f"Status Code: {response.status_code}\n"
            f"---- request headers -----\n"
            f"{format_headers(response.request.headers)}\n"
            f"---- response headers -----\n"
            f"{format_headers(response.headers)}\n"
            f"----- REPORT END -----\n"
        )
        LOG.debug(msg)

    def __repr__(self) -> str:
        try:
            return f"{self.__class__.__name__} - {self.current_url}"
        except RoboxError:
            return f"{self.__class__.__name__}"


class Robox(httpx.Client, RoboxMixin):
    def __init__(
        self,
        *,
        auth: AuthTypes = None,
        params: QueryParamTypes = None,
        headers: HeaderTypes = None,
        cookies: CookieTypes = None,
        verify: VerifyTypes = True,
        cert: CertTypes = None,
        http1: bool = True,
        http2: bool = False,
        proxies: ProxiesTypes = None,
        mounts: tp.Mapping[str, httpx.BaseTransport] = None,
        timeout: TimeoutTypes = DEFAULT_TIMEOUT_CONFIG,
        follow_redirects: bool = True,
        limits: Limits = DEFAULT_LIMITS,
        max_redirects: int = DEFAULT_MAX_REDIRECTS,
        event_hooks: tp.Mapping[str, tp.List[tp.Callable]] = None,
        base_url: URLTypes = "",
        transport: httpx.BaseTransport = None,
        app: tp.Callable = None,
        trust_env: bool = True,
        options: Options = None,
    ) -> None:
        self.options = options or Options()
        self.history = BrowserHistory()
        self.total_requests = 0
        self._request_counter = itertools.count(start=1)
        super().__init__(
            auth=auth,
            params=params,
            headers=headers,
            cookies=cookies,
            timeout=timeout,
            follow_redirects=follow_redirects,
            max_redirects=max_redirects,
            event_hooks=event_hooks,
            base_url=base_url,
            trust_env=trust_env,
            verify=verify,
            cert=cert,
            http1=http1,
            http2=http2,
            proxies=proxies,
            mounts=mounts,
            limits=limits,
            transport=transport,
            app=app,
        )

    def _init_transport(
        self,
        verify: VerifyTypes = True,
        cert: CertTypes = None,
        http1: bool = True,
        http2: bool = False,
        limits: Limits = DEFAULT_LIMITS,
        transport: httpx.BaseTransport = None,
        app: tp.Callable = None,
        trust_env: bool = True,
    ) -> CacheControlTransport:
        _transport = super()._init_transport(
            verify=verify,
            cert=cert,
            http1=http1,
            http2=http2,
            limits=limits,
            transport=transport,
            app=app,
            trust_env=trust_env,
        )
        if self.options.cache:
            if isinstance(_transport, CacheControlTransport):
                return _transport
            return CacheControlTransport(
                transport=_transport,
                cache=self.options.cache,
                cacheable_status_codes=self.options.cacheable_status_codes,
                cacheable_methods=self.options.cacheable_methods,
            )
        return _transport

    def _init_proxy_transport(
        self,
        proxy: Proxy,
        verify: VerifyTypes = True,
        cert: CertTypes = None,
        http1: bool = True,
        http2: bool = False,
        limits: Limits = DEFAULT_LIMITS,
        trust_env: bool = True,
    ) -> CacheControlTransport:
        _transport = super()._init_transport(
            verify=verify,
            cert=cert,
            http1=http1,
            http2=http2,
            limits=limits,
            trust_env=trust_env,
            proxy=proxy,
        )
        if self.options.cache:
            return CacheControlTransport(
                transport=_transport,
                cache=self.options.cache,
                cacheable_status_codes=self.options.cacheable_status_codes,
                cacheable_methods=self.options.cacheable_methods,
            )
        return _transport

    def open(
        self,
        url: str,
        method="GET",
        *,
        content: RequestContent = None,
        data: RequestData = None,
        files: RequestFiles = None,
        json: tp.Any = None,
        params: QueryParamTypes = None,
        headers: HeaderTypes = None,
        cookies: CookieTypes = None,
        auth: tp.Union[AuthTypes, UseClientDefault] = USE_CLIENT_DEFAULT,
        follow_redirects: tp.Union[bool, UseClientDefault] = USE_CLIENT_DEFAULT,
        timeout: tp.Union[TimeoutTypes, UseClientDefault] = USE_CLIENT_DEFAULT,
        extensions: dict = None,
    ) -> Page:
        def _open():
            LOG.debug("Making HTTP request. URL: %s, Method: %s", url, method)
            if self.options.obey_robotstxt:
                can_fetch, crawl_delay = ask_robots(url)
                if not can_fetch:
                    msg = "Forbidden by robots.txt"
                    LOG.debug(msg)
                    raise ForbiddenByRobots(msg)

                if crawl_delay:
                    LOG.debug(
                        "Waiting %s seconds before next request b/c of crawl-delay",
                        crawl_delay,
                    )
                    time.sleep(crawl_delay)

            time.sleep(random.uniform(*self.options.delay_between_requests))
            response = self.request(
                method=method,
                url=url,
                content=content,
                data=data,
                files=files,
                json=json,
                params=params,
                headers=headers,
                cookies=cookies,
                auth=auth,
                follow_redirects=follow_redirects,
                timeout=timeout,
                extensions=extensions,
            )
            self._increment_request_counter()
            return self._build_page_response(response, Page)

        _open.method = method
        return call_with_retry(_open, self.options)()

    def download_file(self, *, url: str, destination_folder: str) -> str:
        return download_file(self, url, destination_folder)

    def refresh(self) -> Page:
        page = self.history.location
        return self.open(page.url)

    def forward(self, n: int = 1) -> Page:
        if not len(self.get_history()):
            raise ValueError("No history to forward")
        self.history.forward(n)
        page = self.history.location
        return self.open(page.url)

    def back(self, n: int = 1) -> Page:
        if not len(self.get_history()):
            raise ValueError("No history to back")
        self.history.back(n)
        page = self.history.location
        return self.open(page.url)


class AsyncRobox(httpx.AsyncClient, RoboxMixin):
    def __init__(
        self,
        *,
        auth: AuthTypes = None,
        params: QueryParamTypes = None,
        headers: HeaderTypes = None,
        cookies: CookieTypes = None,
        verify: VerifyTypes = True,
        cert: CertTypes = None,
        http1: bool = True,
        http2: bool = False,
        proxies: ProxiesTypes = None,
        mounts: tp.Mapping[str, httpx.AsyncBaseTransport] = None,
        timeout: TimeoutTypes = DEFAULT_TIMEOUT_CONFIG,
        follow_redirects: bool = False,
        limits: Limits = DEFAULT_LIMITS,
        max_redirects: int = DEFAULT_MAX_REDIRECTS,
        event_hooks: tp.Mapping[str, tp.List[tp.Callable]] = None,
        base_url: URLTypes = "",
        transport: httpx.AsyncBaseTransport = None,
        app: tp.Callable = None,
        trust_env: bool = True,
        options: Options = None,
    ) -> None:
        self.options = options or Options()
        self.history = BrowserHistory()
        self.total_requests = 0
        self._request_counter = itertools.count(start=1)
        super().__init__(
            auth=auth,
            params=params,
            headers=headers,
            cookies=cookies,
            timeout=timeout,
            follow_redirects=follow_redirects,
            max_redirects=max_redirects,
            event_hooks=event_hooks,
            base_url=base_url,
            trust_env=trust_env,
            verify=verify,
            cert=cert,
            http1=http1,
            http2=http2,
            proxies=proxies,
            mounts=mounts,
            limits=limits,
            transport=transport,
            app=app,
        )

    def _init_transport(
        self,
        verify: VerifyTypes = True,
        cert: CertTypes = None,
        http1: bool = True,
        http2: bool = False,
        limits: Limits = DEFAULT_LIMITS,
        transport: httpx.AsyncBaseTransport = None,
        app: tp.Callable = None,
        trust_env: bool = True,
    ) -> AsyncCacheControlTransport:
        _transport = super()._init_transport(
            verify=verify,
            cert=cert,
            http1=http1,
            http2=http2,
            limits=limits,
            transport=transport,
            app=app,
            trust_env=trust_env,
        )
        if self.options.cache:
            if isinstance(_transport, AsyncCacheControlTransport):
                return _transport
            return AsyncCacheControlTransport(
                transport=_transport,
                cache=self.options.cache,
                cacheable_status_codes=self.options.cacheable_status_codes,
                cacheable_methods=self.options.cacheable_methods,
            )
        return _transport

    def _init_proxy_transport(
        self,
        proxy: Proxy,
        verify: VerifyTypes = True,
        cert: CertTypes = None,
        http1: bool = True,
        http2: bool = False,
        limits: Limits = DEFAULT_LIMITS,
        trust_env: bool = True,
    ) -> AsyncCacheControlTransport:
        _transport = super()._init_transport(
            verify=verify,
            cert=cert,
            http1=http1,
            http2=http2,
            limits=limits,
            trust_env=trust_env,
            proxy=proxy,
        )
        if self.options.cache:
            return AsyncCacheControlTransport(
                transport=_transport,
                cache=self.options.cache,
                cacheable_status_codes=self.options.cacheable_status_codes,
                cacheable_methods=self.options.cacheable_methods,
            )
        return _transport

    async def open(
        self,
        url: str,
        method="GET",
        *,
        content: RequestContent = None,
        data: RequestData = None,
        files: RequestFiles = None,
        json: tp.Any = None,
        params: QueryParamTypes = None,
        headers: HeaderTypes = None,
        cookies: CookieTypes = None,
        auth: tp.Union[AuthTypes, UseClientDefault] = USE_CLIENT_DEFAULT,
        follow_redirects: tp.Union[bool, UseClientDefault] = USE_CLIENT_DEFAULT,
        timeout: tp.Union[TimeoutTypes, UseClientDefault] = USE_CLIENT_DEFAULT,
        extensions: dict = None,
    ) -> AsyncPage:
        async def _open():
            LOG.debug("Making HTTP request. URL: %s, Method: %s", url, method)
            if self.options.obey_robotstxt:
                can_fetch, crawl_delay = await async_ask_robots(url)
                if not can_fetch:
                    msg = "Forbidden by robots.txt"
                    LOG.debug(msg)
                    raise ForbiddenByRobots(msg)

                if crawl_delay:
                    LOG.debug(
                        "Waiting %s seconds before next request b/c of crawl-delay",
                        crawl_delay,
                    )
                    await asyncio.sleep(crawl_delay)

            await asyncio.sleep(random.uniform(*self.options.delay_between_requests))
            response = await self.request(
                method=method,
                url=url,
                content=content,
                data=data,
                files=files,
                json=json,
                params=params,
                headers=headers,
                cookies=cookies,
                auth=auth,
                follow_redirects=follow_redirects,
                timeout=timeout,
                extensions=extensions,
            )
            self._increment_request_counter()
            return self._build_page_response(response, AsyncPage)

        _open.method = method
        return await call_with_retry(_open, self.options)()

    async def download_file(self, *, url: str, destination_folder: str) -> str:
        return await async_download_file(self, url, destination_folder)

    async def refresh(self) -> AsyncPage:
        page = self.history.location
        return await self.open(page.url)

    async def forward(self, n: int = 1) -> AsyncPage:
        if not len(self.get_history()):
            raise ValueError("No history to forward")
        self.history.forward(n)
        page = self.history.location
        return await self.open(page.url)

    async def back(self, n: int = 1) -> AsyncPage:
        if not len(self.get_history()):
            raise ValueError("No history to back")
        self.history.back(n)
        page = self.history.location
        return await self.open(page.url)
