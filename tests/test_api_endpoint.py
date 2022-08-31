from typing import Type
from mashumaro.mixins.json import DataClassJSONMixin

import pytest

from reidun.endpoint import ApiEndpoint, ParamsBuilder


def test_endpoint_is_abstract_class() -> None:
    with pytest.raises(TypeError, match=".*Can't instantiate abstract class.*"):
        ApiEndpoint()  # type: ignore


def test_endpoint_has_path_function() -> None:
    assert callable(ApiEndpoint.path)


def test_endpoint_has_params_function() -> None:
    assert callable(ApiEndpoint.params)


def test_endpoint_has_response_data_type_function() -> None:
    assert callable(ApiEndpoint.response_data_type)


def test_endpoint_has_request_data_type_function() -> None:
    assert callable(ApiEndpoint.request_data_type)


def test_endpoint_implementation() -> None:
    class TestEndpoint(ApiEndpoint):
        def params(self) -> ParamsBuilder:
            raise NotImplementedError()

        def request_data_type(self) -> Type[DataClassJSONMixin]:
            raise NotImplementedError()

        def response_data_type(self) -> Type[DataClassJSONMixin]:
            raise NotImplementedError()

        def path(self) -> str:
            raise NotImplementedError()

    with pytest.raises(NotImplementedError):
        TestEndpoint().params()

    with pytest.raises(NotImplementedError):
        TestEndpoint().request_data_type()

    with pytest.raises(NotImplementedError):
        TestEndpoint().response_data_type()

    with pytest.raises(NotImplementedError):
        TestEndpoint().path()

    assert TestEndpoint.rate_limit() is None
