import asyncio
from typing import Dict, Optional, Tuple, Type, cast

import pytest
from aiohttp import ClientConnectorError, ClientTimeout
from flask import Response, abort, make_response, request
from flask_httpauth import HTTPBasicAuth
from http_server_mock import HttpServerMock
from marshmallow_dataclass import dataclass
from yarl import URL

from reidun.auth_method import BasicAuth
from reidun.client import ApiClient
from reidun.endpoint import ApiEndpoint, ParamsBuilder
from reidun.request import ApiRequestBuilder, ApiRequestVerbatim
from reidun.serialization import SerializableData

app: HttpServerMock = HttpServerMock(__name__)
auth: HTTPBasicAuth = HTTPBasicAuth()


# noinspection Mypy
@app.route("/gettable", methods=["GET"])
def empty_json_object_get() -> Response:
    return make_response({})


# noinspection Mypy
@app.route("/gettable-with-params", methods=["GET"])
def reflect_query_parameters_as_json_get() -> Response:
    return make_response(request.args.to_dict())


# noinspection Mypy
@app.route("/postable", methods=["POST"])
def reflect_body_data_post() -> Response:
    if len(request.data) > 0:
        return make_response(request.data)

    if len(request.form) > 0:
        return make_response(request.form)

    if request.is_json:
        return make_response(request.json)

    raise TypeError(
        "Unknown request data type (expected either binary data, form-encoded data or JSON)"
    )


# noinspection Mypy
@app.route("/tsge", methods=["GET"])
def simple_get_endpoint() -> Response:
    return make_response({})


# noinspection Mypy
@app.route("/tcge", methods=["GET"])
def complex_get_endpoint() -> Response:
    return make_response(
        {
            "float_variable": 1.0,
            "string_variable": "Hello, World!",
            "bool_variable": True,
        }
    )


# noinspection Mypy
@app.route("/tcgewp", methods=["GET"])
def complex_get_endpoint_with_params() -> Response:
    flt = request.args.get("flt")
    if flt is None:
        abort(400)

    if flt == "true":
        return make_response(
            {
                "float_variable": 1.0,
                "string_variable": "Hello, World!",
                "bool_variable": True,
            }
        )
    else:
        return make_response(
            {
                "float_variable": 150.1,
                "string_variable": "Ohai!",
                "bool_variable": False,
            }
        )


# noinspection Mypy
@app.route("/tcpe", methods=["POST"])
def complex_post_endpoint() -> Response:
    if not request.is_json:
        abort(400)

    request_data: str = cast(Dict[str, str], request.json)["string_variable"]
    return make_response(
        {"you_said": request_data, "i_said": "Gooooood morning, Night City!"}
    )


# noinspection Mypy
@auth.verify_password
def verify_password(username: str, password: str) -> Optional[str]:
    if username == "admin" and password == "411u2b453423b310ng70u5":
        return "admin"

    return None


# noinspection Mypy
@app.route("/auth", methods=["GET"])
@auth.login_required
def auth_endpoint() -> Response:
    return make_response({"status": "success"})


@pytest.fixture
def server_deets() -> Tuple[str, int]:
    return "127.0.0.1", 8080


@pytest.fixture
def client(server_deets: Tuple[str, int]) -> ApiClient:
    # noinspection HttpUrlsUsage
    return ApiClient(
        URL(f"http://{server_deets[0]}:{server_deets[1]}/"),
    )


def test_create_client() -> None:
    client: ApiClient = ApiClient(
        URL("https://there-is-no-need-to-have-a-valid-server.com/"),
        encoding="latin1",
        timeout=ClientTimeout(total=60),
        auth=BasicAuth("admin", "411u2b453423b310ng70u5"),
    )

    assert isinstance(client, ApiClient)
    assert client.encoding == "latin1"


def test_create_client_with_defaults() -> None:
    client: ApiClient = ApiClient(
        URL("https://there-is-no-need-to-have-a-valid-server.com/"),
    )

    assert client.encoding == "utf8"


@pytest.mark.asyncio
async def test_use_client_as_async_context_manager(client: ApiClient) -> None:
    async with client as cl:
        print(cl)


def test_client_provides_api_request_builder(client: ApiClient) -> None:
    _rb: ApiRequestBuilder = client.request_builder()
    assert _rb.host == client.host


@pytest.mark.asyncio
async def test_client_can_send_custom_verbatim_request(
    server_deets: Tuple[str, int], client: ApiClient
) -> None:
    with app.run(server_deets[0], server_deets[1]):
        async with client as client:
            _request: ApiRequestVerbatim = (
                client.request_builder()
                .with_params({"a": "alpha", "b": "false"})
                .build("/gettable-with-params")
            )

            response_data, response_status = await client.request_verbatim(_request)
            assert response_data == b'{"a":"alpha","b":"false"}'
            assert response_status == 200


@pytest.mark.asyncio
async def test_client_catches_unauthenticated_request_to_basic_auth_protected_server(
    server_deets: Tuple[str, int], client: ApiClient
) -> None:
    with app.run(server_deets[0], server_deets[1]):
        async with client as client:
            _request: ApiRequestVerbatim = client.request_builder().build("/auth")

            with pytest.raises(ValueError, match=r".*401.*"):
                await client.request_verbatim(_request)


@pytest.mark.asyncio
async def test_client_catches_bad_authentication_to_basic_auth_protected_server(
    server_deets: Tuple[str, int]
) -> None:
    with app.run(server_deets[0], server_deets[1]):
        # noinspection HttpUrlsUsage
        async with ApiClient(
            URL(f"http://{server_deets[0]}:{server_deets[1]}"),
            auth=BasicAuth("admin", "badpassword"),
        ) as client:
            _request: ApiRequestVerbatim = client.request_builder().build("/auth")

            with pytest.raises(ValueError, match=r".*401.*"):
                await client.request_verbatim(_request)


@pytest.mark.asyncio
async def test_client_can_send_basic_authenticated_custom_verbatim_request(
    server_deets: Tuple[str, int]
) -> None:
    with app.run(server_deets[0], server_deets[1]):
        # noinspection HttpUrlsUsage
        async with ApiClient(
            URL(f"http://{server_deets[0]}:{server_deets[1]}"),
            auth=BasicAuth("admin", "411u2b453423b310ng70u5"),
        ) as client:
            _request: ApiRequestVerbatim = client.request_builder().build("/auth")

            _response, _ = await client.request_verbatim(_request)
            assert _response == b'{"status":"success"}'


@pytest.mark.asyncio
async def test_client_refuses_to_send_uncontextual_verbatim_custom_request(
    server_deets: Tuple[str, int], client: ApiClient
) -> None:
    with app.run(server_deets[0], server_deets[1]):
        req = client.request_builder().build("/gettable")
        with pytest.raises(ValueError, match=r".*async context manager.*"):
            await client.request_verbatim(req)


@pytest.mark.asyncio
async def test_client_catches_http_status_errors_on_verbatim_custom_requests(
    server_deets: Tuple[str, int], client: ApiClient
) -> None:
    with app.run(server_deets[0], server_deets[1]):
        async with client as client:
            req = client.request_builder().build("/non-extand-endpoint")
            with pytest.raises(ValueError, match=r".*HTTP status code 404.*"):
                await client.request_verbatim(req)


@pytest.mark.asyncio
async def test_client_catches_connection_errors_on_verbatim_custom_requests(
    client: ApiClient,
) -> None:
    async with client as client:
        req = client.request_builder().build("/gettable")
        with pytest.raises(ClientConnectorError):
            await client.request_verbatim(req)


@pytest.mark.asyncio
async def test_client_catches_timeouts_on_verbatim_custom_requests(
    server_deets: Tuple[str, int], client: ApiClient
) -> None:
    with app.run(server_deets[0], server_deets[1]):
        async with client as client:
            req = (
                client.request_builder()
                .with_timeout(ClientTimeout(total=0.0000001))
                .build("/gettable")
            )
            with pytest.raises(asyncio.TimeoutError):
                await client.request_verbatim(req)


@pytest.mark.asyncio
async def test_client_can_send_typed_get_request(
    server_deets: Tuple[str, int], client: ApiClient
) -> None:
    @dataclass
    class TestResponseData(SerializableData):
        pass

    class TestSimpleGetEndpoint(ApiEndpoint):
        def params(self) -> ParamsBuilder:
            raise NotImplementedError()

        def request_data_type(self) -> Type[SerializableData]:
            raise NotImplementedError()

        def response_data_type(self) -> Type[TestResponseData]:
            return TestResponseData

        def path(self) -> str:
            return "/tsge"

    with app.run(server_deets[0], server_deets[1]):
        async with client as client:
            _response, _ = await client.get(TestSimpleGetEndpoint())
            assert _response == TestResponseData()


@pytest.mark.asyncio
async def test_client_can_send_typed_get_request_with_response_data(
    server_deets: Tuple[str, int], client: ApiClient
) -> None:
    @dataclass
    class TestResponseData(SerializableData):
        float_variable: float
        string_variable: str
        bool_variable: bool

    class TestComplexGetEndpoint(ApiEndpoint):
        def params(self) -> ParamsBuilder:
            raise NotImplementedError()

        def request_data_type(self) -> Type[SerializableData]:
            raise NotImplementedError()

        def response_data_type(self) -> Type[TestResponseData]:
            return TestResponseData

        def path(self) -> str:
            return "/tcge"

    with app.run(server_deets[0], server_deets[1]):
        async with client as client:
            _response, _ = await client.get(TestComplexGetEndpoint())
            assert isinstance(_response, TestResponseData)
            # noinspection Mypy
            assert _response == TestResponseData(1.0, "Hello, World!", True)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "flt,expected",
    [
        ("true", (1.0, "Hello, World!", True)),
        ("false", (150.1, "Ohai!", False)),
    ],
)
async def test_client_can_send_typed_get_request_with_parameters_and_response_data(
    server_deets: Tuple[str, int],
    client: ApiClient,
    flt: str,
    expected: Tuple[float, str, bool],
) -> None:
    @dataclass
    class TestResponseData(SerializableData):
        float_variable: float
        string_variable: str
        bool_variable: bool

    class TestComplexGetEndpoint(ApiEndpoint):
        def params(self) -> ParamsBuilder:
            raise NotImplementedError()

        def request_data_type(self) -> Type[SerializableData]:
            raise NotImplementedError()

        def response_data_type(self) -> Type[TestResponseData]:
            return TestResponseData

        def path(self) -> str:
            return "/tcgewp"

    with app.run(server_deets[0], server_deets[1]):
        async with client as client:
            _response, _ = await client.get(
                TestComplexGetEndpoint(), params={"flt": flt}
            )
            assert isinstance(_response, TestResponseData)
            # noinspection Mypy
            assert _response == TestResponseData(*expected)


@pytest.mark.asyncio
async def test_client_can_send_typed_post_request_with_data(
    server_deets: Tuple[str, int], client: ApiClient
) -> None:
    @dataclass
    class TestResponseData(SerializableData):
        you_said: str
        i_said: str

    @dataclass
    class TestRequestData(SerializableData):
        string_variable: str

    class TestComplexPostEndpoint(ApiEndpoint):
        def params(self) -> ParamsBuilder:
            raise NotImplementedError()

        def response_data_type(self) -> Type[TestResponseData]:
            return TestResponseData

        def request_data_type(self) -> Type[TestRequestData]:
            return TestRequestData

        def path(self) -> str:
            return "/tcpe"

    with app.run(server_deets[0], server_deets[1]):
        async with client as client:
            # noinspection Mypy
            _response, _ = await client.post(
                TestComplexPostEndpoint(), TestRequestData("Hello, World!")
            )
            # noinspection Mypy
            assert _response == TestResponseData(
                "Hello, World!", "Gooooood morning, Night City!"
            )
