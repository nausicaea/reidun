import aiohttp.hdrs

from reidun.auth_method import AuthMethod, BasicAuth, BearerAuth, RawAuth


def test_auth_method_has_headers_function() -> None:
    assert callable(AuthMethod.headers)


def test_headers_function_has_default_impl() -> None:
    class TestAuthMethod(AuthMethod):
        pass

    _tam = TestAuthMethod()
    assert _tam.headers() is None


def testbasic_auth_is_an_auth_method() -> None:
    assert issubclass(BasicAuth, AuthMethod)


def testbasic_auth_requires_username_and_password_with_default_encoding() -> None:
    ba: BasicAuth = BasicAuth("username", "password")
    assert ba.encoding == "latin1"


def testbasic_auth_accepts_encoding_parameter() -> None:
    BasicAuth("username", "password", encoding="utf8")


def testbasic_auth_correctly_sets_authorization_header() -> None:
    ba: BasicAuth = BasicAuth("username", "password")
    assert ba.headers() == {
        aiohttp.hdrs.AUTHORIZATION: "Basic dXNlcm5hbWU6cGFzc3dvcmQ="
    }


def test_bearer_auth_is_an_auth_method() -> None:
    assert issubclass(BearerAuth, AuthMethod)


def test_bearer_auth_requires_token() -> None:
    BearerAuth("authentication-token")


def test_bearer_auth_correctly_sets_authorization_header() -> None:
    ba: BearerAuth = BearerAuth("authentication-token")
    assert ba.headers() == {
        aiohttp.hdrs.AUTHORIZATION: "Bearer authentication-token"
    }


def test_raw_auth_is_an_auth_method() -> None:
    assert issubclass(RawAuth, AuthMethod)


def test_raw_auth_requires_raw_authorization_header() -> None:
    RawAuth("raw-header-value")


def test_raw_auth_correctly_sets_authorization_header() -> None:
    ra: RawAuth = RawAuth("raw-header-value")

    assert ra.headers() == {aiohttp.hdrs.AUTHORIZATION: "raw-header-value"}
