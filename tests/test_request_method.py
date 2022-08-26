from enum import Enum

import pytest

from reidun.request_method import RequestMethod


def test_request_method_is_enum() -> None:
    assert issubclass(RequestMethod, Enum)


@pytest.mark.parametrize(
    "method",
    [
        RequestMethod.GET,
        RequestMethod.POST,
        RequestMethod.HEAD,
        RequestMethod.OPTIONS,
        RequestMethod.PUT,
        RequestMethod.DELETE,
        RequestMethod.CONNECT,
        RequestMethod.TRACE,
        RequestMethod.PATCH,
    ],
)
def test_request_method_contains_most_common_methods(method: RequestMethod) -> None:
    assert method in RequestMethod
