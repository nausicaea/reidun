from abc import ABC, abstractmethod
from typing import Dict, Optional, Type

from ..serialization import OutputFormat, SerializableData


class ParamsBuilder(ABC):
    @abstractmethod
    def build(self) -> Optional[Dict[str, str]]:
        ...


class ApiEndpoint(ABC):
    @abstractmethod
    def params(self) -> ParamsBuilder:
        ...

    @abstractmethod
    def path(self) -> str:
        ...

    @abstractmethod
    def response_data_type(self) -> Type[SerializableData]:
        ...

    @abstractmethod
    def request_data_type(self) -> Type[SerializableData]:
        ...

    @staticmethod
    def request_format() -> OutputFormat:
        return OutputFormat.JSON

    @staticmethod
    def rate_limit() -> Optional[float]:
        return None
