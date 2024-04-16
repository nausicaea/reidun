from abc import ABC, abstractmethod
from typing import Dict, Optional, Type

from mashumaro.mixins.json import DataClassJSONMixin


class ParamsBuilder(ABC):
    @abstractmethod
    def build(self) -> Optional[Dict[str, str]]: ...


class ApiEndpoint(ABC):
    @abstractmethod
    def params(self) -> ParamsBuilder: ...

    @abstractmethod
    def path(self) -> str: ...

    @abstractmethod
    def response_data_type(self) -> Type[DataClassJSONMixin]: ...

    @abstractmethod
    def request_data_type(self) -> Type[DataClassJSONMixin]: ...

    @staticmethod
    def rate_limit() -> Optional[float]:
        return None
