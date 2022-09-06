import functools
import logging
from dataclasses import dataclass, field
from types import TracebackType
from typing import Any, List, Mapping, Optional, Tuple, Type, TypeVar, Union

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
    from appdirs import AppDirs
    from joblib import Memory

    _LOG.debug("Caching is enabled")
    _APP_DIRS = AppDirs("net.nausicaea.ylva", "nausicaea")
    MEMORY = Memory(_APP_DIRS.user_cache_dir)
except ImportError as e:
    _LOG.debug(
        f"Either package joblib or appdirs is not available, so caching is disabled: {e}"
    )

    class PassThroughMemory:
        def cache(self, func=None, ignore=None, verbose=None, mmap_mode=False):
            if func is None:
                return functools.partial(
                    self.cache,
                    ignore=ignore,
                    verbose=verbose,
                    mmap_mode=mmap_mode,
                )

            return func

    MEMORY = PassThroughMemory()


@MEMORY.cache(ignore=["session", "tokens"])
async def _rv(
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
    _session: Optional[ClientSession] = field(default=None, init=False)
    _tokens: TokenBucket = field(default_factory=TokenBucket, init=False)

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

        return await _rv(self._session, self._tokens, request, rl)

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
