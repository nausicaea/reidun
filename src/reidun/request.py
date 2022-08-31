from dataclasses import dataclass, field
from typing import Generic, Mapping, Optional, TypeVar, Union, cast, overload

from aiohttp import ClientTimeout, FormData, Payload, JsonPayload
from aiohttp.helpers import sentinel
from yarl import URL
from mashumaro.mixins.json import DataClassJSONMixin

from .endpoint import ApiEndpoint
from .request_method import RequestMethod

E = TypeVar("E", bound=ApiEndpoint)
ApiRequestVerbatimDataType = Union[None, Mapping[str, str], bytes, str, FormData]
ApiRequestDataType = Union[ApiRequestVerbatimDataType, DataClassJSONMixin]


@dataclass(frozen=True)
class ApiRequestVerbatim:
    host: URL
    method: Union[str, RequestMethod]
    endpoint: str
    params: Optional[Mapping[str, str]]
    payload: Optional[Payload]
    timeout: Optional[ClientTimeout]

    def endpoint_url(self) -> URL:
        return self.host.with_path(self.endpoint)

    def request_method(self) -> str:
        if isinstance(self.method, str):
            return self.method
        elif isinstance(self.method, RequestMethod):
            return self.method.name
        else:
            raise TypeError(
                f"Expected either a string or a RequestMethod instance, got: {type(self.method)} (value: {self.method})"
            )

    def request_timeout(self) -> Union[object, ClientTimeout]:
        if self.timeout is None:
            return cast(object, sentinel)

        return self.timeout


@dataclass(frozen=True)
class ApiRequest(Generic[E]):
    host: URL
    method: Union[str, RequestMethod]
    endpoint: E
    params: Optional[Mapping[str, str]]
    payload: Optional[Payload]
    timeout: Optional[ClientTimeout]

    def to_verbatim(self) -> ApiRequestVerbatim:
        path = self.endpoint.path()

        return ApiRequestVerbatim(
            self.host,
            self.method,
            path,
            self.params,
            self.payload,
            self.timeout,
        )

    def endpoint_url(self) -> URL:
        return self.host.with_path(self.endpoint.path())

    def request_method(self) -> str:
        if isinstance(self.method, str):
            return self.method
        elif isinstance(self.method, RequestMethod):
            return self.method.name
        else:
            raise TypeError(
                f"Expected either a string or a RequestMethod instance, got: {type(self.method)} (value: {self.method})"
            )

    def request_timeout(self) -> Union[object, ClientTimeout]:
        if self.timeout is None:
            return cast(object, sentinel)

        return self.timeout


@dataclass
class ApiRequestBuilder:
    host: URL
    method: Union[str, RequestMethod] = field(default=RequestMethod.GET, init=False)
    params: Optional[Mapping[str, str]] = field(default=None, init=False)
    data: Optional[DataClassJSONMixin] = field(default=None, init=False)
    timeout: Optional[ClientTimeout] = field(default=None, init=False)

    def with_method(self, method: Union[str, RequestMethod]) -> "ApiRequestBuilder":
        if not isinstance(method, (str, RequestMethod)):
            raise TypeError(
                f"Expected either a string or a RequestMethod instance, got: {type(method)} (value: {method})"
            )
        self.method = method
        return self

    def with_params(self, params: Optional[Mapping[str, str]]) -> "ApiRequestBuilder":
        self.params = params
        return self

    def with_data(
        self,
        data: DataClassJSONMixin,
    ) -> "ApiRequestBuilder":
        self.data = data
        return self

    def with_timeout(self, timeout: Optional[ClientTimeout]) -> "ApiRequestBuilder":
        self.timeout = timeout
        return self

    @overload
    def build(self, endpoint: str) -> ApiRequestVerbatim:
        ...

    @overload
    def build(self, endpoint: E) -> ApiRequest[E]:
        ...

    def build(
        self, endpoint: Union[str, E]
    ) -> Union[ApiRequestVerbatim, ApiRequest[E]]:
        payload: Optional[Payload] = None
        if self.data is not None:
            payload = JsonPayload(self.data.to_json())

        if isinstance(endpoint, str):
            return ApiRequestVerbatim(
                self.host,
                self.method,
                endpoint,
                self.params,
                payload,
                self.timeout,
            )
        elif isinstance(endpoint, ApiEndpoint):
            return ApiRequest(
                self.host,
                self.method,
                endpoint,
                self.params,
                payload,
                self.timeout,
            )
        else:
            raise TypeError(
                f"Parameter endpoint must be a string or an instance of ApiEndpoint, got {endpoint} (type: {type(endpoint)}) instead"
            )
