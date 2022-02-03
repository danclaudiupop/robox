import asyncio
import itertools
import random
import time
import typing as tp

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
from httpx_cache.cache import BaseCache

from robox import LOG
from robox._download import async_download_file, download_file
from robox._exceptions import RoboxError
from robox._history import BrowserHistory
from robox._page import AsyncPage, Page


class RoboxMixin:
    @property
    def user_agent(self) -> str:
        return self._user_agent

    @user_agent.setter
    def user_agent(self, user_agent: str) -> None:
        self.headers["user-agent"] = user_agent

    def get_history(self) -> tp.List[tp.Union[Page, AsyncPage]]:
        return self._history.get_locations()

    @property
    def current_url(self) -> URL:
        if latest_entry := self._history.latest_entry():
            return latest_entry.url
        else:
            raise RoboxError("Not tracking history")

    def _increment_request_counter(self) -> None:
        self.total_requests = next(self._request_counter)

    def _build_page_response(
        self, response: httpx.Response, page_cls: tp.Union[Page, AsyncPage]
    ) -> tp.Union[Page, AsyncPage]:
        self._format_response_log(response)
        if self.raise_on_4xx_5xx:
            try:
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:
                LOG.error(
                    f"Error response {exc.response.status_code} "
                    f"while requesting {exc.request.url!r}."
                )
                raise exc

        page = page_cls(response, robox=self)
        if self.history:
            self._history.location = page
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
        user_agent: str = None,
        raise_on_4xx_5xx: bool = False,
        delay_between_requests: tp.Tuple[float, float] = (0.0, 0.0),
        soup_kwargs: dict = {"features": "html.parser"},
        history: bool = True,
        cache: tp.Optional[BaseCache] = None,
        cacheable_methods: tp.Tuple[str, ...] = ("GET",),
        cacheable_status_codes: tp.Tuple[int, ...] = (200, 203, 300, 301, 308),
    ) -> None:
        self._user_agent = user_agent
        self.raise_on_4xx_5xx = raise_on_4xx_5xx
        self.delay_between_requests = delay_between_requests
        self.soup_kwargs = soup_kwargs
        self.history = history
        self.cache = cache
        self.cacheable_methods = cacheable_methods
        self.cacheable_status_codes = cacheable_status_codes
        self.total_requests = 0
        self._history = BrowserHistory()
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
        if self.cache:
            if isinstance(_transport, CacheControlTransport):
                return _transport
            return CacheControlTransport(
                transport=_transport,
                cache=self.cache,
                cacheable_status_codes=self.cacheable_status_codes,
                cacheable_methods=self.cacheable_methods,
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
        if self.cache:
            return CacheControlTransport(
                transport=_transport,
                cache=self.cache,
                cacheable_status_codes=self.cacheable_status_codes,
                cacheable_methods=self.cacheable_methods,
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
        LOG.debug("Making HTTP request. URL: %s, Method: %s", url, method)
        time.sleep(random.uniform(*self.delay_between_requests))
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

    def download_file(self, *, url: str, destination_folder: str) -> str:
        return download_file(self, url, destination_folder)

    def refresh(self) -> Page:
        page = self._history.location
        return self.open(page.url)

    def forward(self, n: int = 1) -> Page:
        if not len(self.get_history()):
            raise ValueError("No history to forward")
        self._history.forward(n)
        page = self._history.location
        return self.open(page.url)

    def back(self, n: int = 1) -> Page:
        if not len(self.get_history()):
            raise ValueError("No history to back")
        self._history.back(n)
        page = self._history.location
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
        user_agent: str = None,
        raise_on_4xx_5xx: bool = False,
        delay_between_requests: tp.Tuple[float, float] = (0.0, 0.0),
        soup_kwargs: dict = {"features": "html.parser"},
        history: bool = True,
        cache: tp.Optional[BaseCache] = None,
        cacheable_methods: tp.Tuple[str, ...] = ("GET",),
        cacheable_status_codes: tp.Tuple[int, ...] = (200, 203, 300, 301, 308),
    ) -> None:
        self._user_agent = user_agent
        self.raise_on_4xx_5xx = raise_on_4xx_5xx
        self.delay_between_requests = delay_between_requests
        self.soup_kwargs = soup_kwargs
        self.history = history
        self.cache = cache
        self.cacheable_methods = cacheable_methods
        self.cacheable_status_codes = cacheable_status_codes
        self.total_requests = 0
        self._history = BrowserHistory()
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
        if self.cache:
            if isinstance(_transport, AsyncCacheControlTransport):
                return _transport
            return AsyncCacheControlTransport(
                transport=_transport,
                cache=self.cache,
                cacheable_status_codes=self.cacheable_status_codes,
                cacheable_methods=self.cacheable_methods,
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
        if self.cache:
            return AsyncCacheControlTransport(
                transport=_transport,
                cache=self.cache,
                cacheable_status_codes=self.cacheable_status_codes,
                cacheable_methods=self.cacheable_methods,
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
        LOG.debug("Making HTTP request. URL: %s, Method: %s", url, method)
        await asyncio.sleep(random.uniform(*self.delay_between_requests))
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

    async def download_file(self, *, url: str, destination_folder: str) -> str:
        return await async_download_file(self, url, destination_folder)

    async def refresh(self) -> AsyncPage:
        page = self._history.location
        return await self.open(page.url)

    async def forward(self, n: int = 1) -> AsyncPage:
        if not len(self.get_history()):
            raise ValueError("No history to forward")
        self._history.forward(n)
        page = self._history.location
        return await self.open(page.url)

    async def back(self, n: int = 1) -> AsyncPage:
        if not len(self.get_history()):
            raise ValueError("No history to back")
        self._history.back(n)
        page = self._history.location
        return await self.open(page.url)
