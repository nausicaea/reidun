from dataclasses import dataclass
from typing import Any, Type

import pytest
from aiohttp import ClientTimeout, FormData
from aiohttp.helpers import sentinel
from mashumaro.mixins.json import DataClassJSONMixin
from yarl import URL

from reidun.endpoint import ApiEndpoint, ParamsBuilder
from reidun.request import ApiRequest, ApiRequestBuilder, ApiRequestVerbatim
from reidun.request_method import RequestMethod


def test_api_request_builder_requires_host() -> None:
    ApiRequestBuilder(URL("https://does-not-require-a-valid-host.com"))


def test_api_request_builder_accepts_custom_string_method() -> None:
    ApiRequestBuilder(
        URL("https://does-not-require-a-valid-host.com")
    ).with_method("POST")


def test_api_request_builder_accepts_enum_method() -> None:
    ApiRequestBuilder(
        URL("https://does-not-require-a-valid-host.com")
    ).with_method(RequestMethod.POST)


def test_api_request_builder_accepts_custom_params() -> None:
    ApiRequestBuilder(
        URL("https://does-not-require-a-valid-host.com")
    ).with_params({"key": "value"})


@dataclass
class Td(DataClassJSONMixin):
    a: str
    b: bool


@pytest.mark.parametrize(
    "data",
    [
        ({"var_a": "Hello, World!", "var_b": "1.0"}),
        (Td(a="Hello, World!", b=False)),
    ],
)
def test_api_request_builder_accepts_custom_data(data: Any) -> None:
    ApiRequestBuilder(
        URL("https://does-not-require-a-valid-host.com")
    ).with_data(data)


def test_api_request_builder_accepts_custom_timeout() -> None:
    ApiRequestBuilder(
        URL("https://does-not-require-a-valid-host.com")
    ).with_timeout(ClientTimeout(total=60))


def test_api_request_builder_builds_verbatim_request_with_defaults() -> None:
    r: ApiRequestVerbatim = ApiRequestBuilder(
        URL("https://does-not-require-a-valid-host.com")
    ).build("/any-endpoint")

    assert r.host == URL("https://does-not-require-a-valid-host.com")
    assert r.method == RequestMethod.GET
    assert r.endpoint == "/any-endpoint"
    assert r.params is None
    assert r.payload is None
    assert r.timeout is None


def test_api_request_builder_builds_request_with_defaults() -> None:
    @dataclass
    class TestResponseData(DataClassJSONMixin):
        pass

    class TestEndpoint(ApiEndpoint):
        def params(self) -> ParamsBuilder:
            raise NotImplementedError()

        def request_data_type(self) -> Type[DataClassJSONMixin]:
            raise NotImplementedError()

        def response_data_type(self) -> Type[TestResponseData]:
            return TestResponseData

        def path(self) -> str:
            return "/api/te"

    r: ApiRequest[TestEndpoint] = ApiRequestBuilder(
        URL("https://does-not-require-a-valid-host.com")
    ).build(TestEndpoint())

    assert r.host == URL("https://does-not-require-a-valid-host.com")
    assert r.method == RequestMethod.GET
    assert isinstance(r.endpoint, TestEndpoint)
    assert r.params is None
    assert r.payload is None
    assert r.timeout is None


def test_verbatim_api_request_provides_string_request_method() -> None:
    r: ApiRequestVerbatim = (
        ApiRequestBuilder(URL("https://does-not-require-a-valid-host.com"))
        .with_method(RequestMethod.GET)
        .build("/api/info")
    )

    assert r.request_method() == "GET"

    r = (
        ApiRequestBuilder(URL("https://does-not-require-a-valid-host.com"))
        .with_method("GET")
        .build("/api/info")
    )

    assert r.request_method() == "GET"


def test_api_request_provides_string_request_method() -> None:
    @dataclass
    class TestResponseData(DataClassJSONMixin):
        pass

    class TestEndpoint(ApiEndpoint):
        def params(self) -> ParamsBuilder:
            raise NotImplementedError()

        def request_data_type(self) -> Type[DataClassJSONMixin]:
            raise NotImplementedError()

        def response_data_type(self) -> Type[TestResponseData]:
            return TestResponseData

        def path(self) -> str:
            return "/api/te"

    r: ApiRequest[TestEndpoint] = (
        ApiRequestBuilder(URL("https://does-not-require-a-valid-host.com"))
        .with_method(RequestMethod.GET)
        .build(TestEndpoint())
    )

    assert r.request_method() == "GET"

    r = (
        ApiRequestBuilder(URL("https://does-not-require-a-valid-host.com"))
        .with_method("GET")
        .build(TestEndpoint())
    )

    assert r.request_method() == "GET"


def test_verbatim_api_request_provides_request_timeout_method() -> None:
    r: ApiRequestVerbatim = ApiRequestBuilder(
        URL("https://example.com")
    ).build("/api/info")

    assert r.request_timeout() == sentinel


def test_api_request_provides_request_timeout_method() -> None:
    @dataclass
    class TestResponseData(DataClassJSONMixin):
        pass

    class TestEndpoint(ApiEndpoint):
        def params(self) -> ParamsBuilder:
            raise NotImplementedError()

        def request_data_type(self) -> Type[DataClassJSONMixin]:
            raise NotImplementedError()

        def response_data_type(self) -> Type[TestResponseData]:
            return TestResponseData

        def path(self) -> str:
            return "/api/te"

    r: ApiRequest[TestEndpoint] = ApiRequestBuilder(
        URL("https://example.com")
    ).build(TestEndpoint())

    assert r.request_timeout() == sentinel


def test_verbatim_api_request_provides_full_endpoint_url_for_endpoints() -> None:
    r: ApiRequestVerbatim = ApiRequestBuilder(
        URL("https://example.com")
    ).build("/api/info")

    assert r.endpoint_url() == URL("https://example.com/api/info")


def test_api_request_provides_full_endpoint_url_for_endpoints() -> None:
    @dataclass
    class TestResponseData(DataClassJSONMixin):
        pass

    class TestEndpoint(ApiEndpoint):
        def params(self) -> ParamsBuilder:
            raise NotImplementedError()

        def request_data_type(self) -> Type[DataClassJSONMixin]:
            raise NotImplementedError()

        def response_data_type(self) -> Type[TestResponseData]:
            return TestResponseData

        def path(self) -> str:
            return "/api/te"

    r: ApiRequest[TestEndpoint] = ApiRequestBuilder(
        URL("https://example.com")
    ).build(TestEndpoint())

    assert r.endpoint_url() == URL("https://example.com/api/te")


def test_api_request_can_be_converted_to_verbatim_api_request() -> None:
    @dataclass
    class TestResponseData(DataClassJSONMixin):
        pass

    class TestEndpoint(ApiEndpoint):
        def params(self) -> ParamsBuilder:
            raise NotImplementedError()

        def request_data_type(self) -> Type[DataClassJSONMixin]:
            raise NotImplementedError()

        def response_data_type(self) -> Type[TestResponseData]:
            return TestResponseData

        def path(self) -> str:
            return "/api/te"

    er: ApiRequest[TestEndpoint] = ApiRequest(
        URL("https://example.com"),
        RequestMethod.GET,
        TestEndpoint(),
        None,
        None,
        None,
    )

    rv: ApiRequestVerbatim = er.to_verbatim()
    assert rv.host == er.host
    assert rv.method == er.method
    assert rv.endpoint == TestEndpoint().path()
    assert rv.params == er.params
    assert rv.payload == er.payload
    assert rv.timeout == er.timeout
