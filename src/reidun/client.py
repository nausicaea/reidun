import logging
from dataclasses import dataclass, field
from pathlib import Path
from types import TracebackType
from typing import Mapping, Optional, Tuple, Type, TypeVar, Union

from aiohttp import ClientSession, ClientTimeout
from aiohttp.helpers import sentinel
from mashumaro.mixins.json import DataClassJSONMixin
from yarl import URL

from .auth_method import AuthMethod
from .endpoint import ApiEndpoint
from .request import ApiRequest, ApiRequestBuilder, ApiRequestVerbatim
from .request_method import RequestMethod
from .token_bucket import TokenBucket

_LOG: logging.Logger = logging.getLogger(__name__)
I = TypeVar("I", bound=DataClassJSONMixin)
O = TypeVar("O", bound=DataClassJSONMixin)

try:
    from aiohttp_client_cache.backends.sqlite import SQLiteBackend
    from aiohttp_client_cache.session import CachedSession
    from appdirs import AppDirs

    _LOG.debug("Caching is enabled")
    _APP_DIRS = AppDirs("net.nausicaea.reidun", "nausicaea")
except ImportError as e:
    _LOG.info(f"Caching cannot be enabled: {e}")
    CachedSession = None
    SQLiteBackend = None
    _APP_DIRS = None


async def _rv(
    *,
    session: ClientSession,
    tokens: TokenBucket,
    request: ApiRequestVerbatim,
    rate_limit: Optional[float] = None,
) -> Tuple[bytes, int]:
    await tokens.take(rate_limit)

    endpoint_url = request.endpoint_url()
    _LOG.debug(
        f"Issuing a {request.method} request to {endpoint_url} with {request.params} parameters and {request.payload.size if request.payload is not None else 0} bytes payload"
    )
    async with session.request(
        request.request_method(),
        endpoint_url,
        params=request.params,
        data=request.payload,
        timeout=request.request_timeout(),
    ) as response:
        # FIXME: This is dangerous for large responses, as it loads everything into memory; [aiohttp](https://docs.aiohttp.org/en/stable/client_quickstart.html#streaming-response-content)
        response_data = await response.read()
        _LOG.debug(
            f"Received a response with {len(response_data)} bytes of data"
        )

        if not response.ok:
            _LOG.error(
                f"Received an error response from {response.host} with code {response.status}, headers {response.headers}, and data {response_data}"
            )
            raise ValueError(
                f"The server responded with HTTP status code {response.status}: {response_data}"
            )

    return response_data.strip(), response.status


@dataclass
class ApiClient:
    host: Union[URL, str]
    encoding: str = field(default="utf8")
    timeout: Optional[ClientTimeout] = field(default=None)
    rate_limit: Optional[float] = field(default=None)
    auth: Optional[AuthMethod] = field(default=None)
    _tokens: TokenBucket = field(default_factory=TokenBucket, init=False)
    _session: Optional[ClientSession] = field(default=None, init=False)

    def request_builder(self) -> ApiRequestBuilder:
        if isinstance(self.host, URL):
            return ApiRequestBuilder(self.host)
        elif isinstance(self.host, str):
            return ApiRequestBuilder(URL(self.host))
        else:
            raise TypeError("The host parameter is neither yarl.URL nor str")

    async def request_verbatim(
        self, request: ApiRequestVerbatim, rate_limit: Optional[float] = None
    ) -> Tuple[bytes, int]:
        if rate_limit is not None:
            rl = rate_limit
        elif self.rate_limit is not None:
            rl = self.rate_limit
        else:
            rl = None

        if self._session is None:
            raise ValueError(
                "You can only issue requests within an async context manager"
            )

        return await _rv(
            session=self._session,
            tokens=self._tokens,
            request=request,
            rate_limit=rl,
        )

    async def request(
        self, request: ApiRequest[ApiEndpoint]
    ) -> Tuple[Optional[DataClassJSONMixin], int]:
        _LOG.debug(
            f"Preparing a request to API endpoint {type(request.endpoint)}"
        )

        verbatim_request: ApiRequestVerbatim = request.to_verbatim()
        response_data, response_status = await self.request_verbatim(
            verbatim_request, rate_limit=request.endpoint.rate_limit()
        )
        if len(response_data) == 0:
            return None, response_status

        response_data_decoded: str = response_data.decode(self.encoding)
        response_data_type: Type[
            DataClassJSONMixin
        ] = request.endpoint.response_data_type()
        response_data_deserialized = response_data_type.from_json(
            response_data_decoded
        )
        return response_data_deserialized, response_status

    async def get(
        self, endpoint: ApiEndpoint, params: Optional[Mapping[str, str]] = None
    ) -> Tuple[Optional[DataClassJSONMixin], int]:
        req: ApiRequest[ApiEndpoint] = (
            self.request_builder()
            .with_method(RequestMethod.GET)
            .with_params(params)
            .build(endpoint)
        )

        return await self.request(req)

    async def post(
        self,
        endpoint: ApiEndpoint,
        data: DataClassJSONMixin,
        params: Optional[Mapping[str, str]] = None,
    ) -> Tuple[Optional[DataClassJSONMixin], int]:
        req: ApiRequest[ApiEndpoint] = (
            self.request_builder()
            .with_method(RequestMethod.POST)
            .with_params(params)
            .with_data(data)
            .build(endpoint)
        )

        return await self.request(req)

    async def put(
        self,
        endpoint: ApiEndpoint,
        data: DataClassJSONMixin,
        params: Optional[Mapping[str, str]] = None,
    ) -> Tuple[Optional[DataClassJSONMixin], int]:
        req: ApiRequest[ApiEndpoint] = (
            self.request_builder()
            .with_method(RequestMethod.PUT)
            .with_params(params)
            .with_data(data)
            .build(endpoint)
        )

        return await self.request(req)

    async def __aenter__(self) -> "ApiClient":
        timeout = self.timeout if self.timeout is not None else sentinel
        headers = self.auth.headers() if self.auth is not None else None

        if (
            CachedSession is not None
            and SQLiteBackend is not None
            and _APP_DIRS is not None
        ):
            self._session = CachedSession(
                timeout=timeout,
                headers=headers,
                cache=SQLiteBackend(
                    str(
                        Path(_APP_DIRS.user_cache_dir).joinpath("cache.sqlite")
                    )
                ),
            )
        else:
            self._session = ClientSession(timeout=timeout, headers=headers)

        await self._session.__aenter__()
        return self

    async def __aexit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> None:
        if self._session is not None:
            await self._session.__aexit__(exc_type, exc_val, exc_tb)
            self._session = None
