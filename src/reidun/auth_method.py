"""
Provides various authentication method commonly used with REST APIs
"""
from abc import ABC
from base64 import b64encode
from dataclasses import dataclass, field
from typing import Dict, Optional, Union

from aiohttp.hdrs import AUTHORIZATION
from multidict import istr


class AuthMethod(ABC):
    """
    Abstract base class of an authentication method
    """

    # noinspection PyMethodMayBeStatic
    def headers(self) -> Optional[Dict[Union[str, istr], str]]:
        """
        Return the headers used for authentication
        """
        return None


@dataclass
class BasicAuth(AuthMethod):
    username: str
    password: str
    encoding: str = field(default="latin1")

    def headers(self) -> Optional[Dict[Union[str, istr], str]]:
        concatenated_creds: str = f"{self.username}:{self.password}"
        encoded_creds: str = b64encode(concatenated_creds.encode(self.encoding)).decode(
            self.encoding
        )
        return {AUTHORIZATION: f"Basic {encoded_creds}"}


@dataclass
class BearerAuth(AuthMethod):
    token: str

    def headers(self) -> Optional[Dict[Union[str, istr], str]]:
        return {AUTHORIZATION: f"Bearer {self.token}"}


@dataclass
class RawAuth(AuthMethod):
    raw_authorization_header: str

    def headers(self) -> Optional[Dict[Union[str, istr], str]]:
        return {AUTHORIZATION: self.raw_authorization_header}
