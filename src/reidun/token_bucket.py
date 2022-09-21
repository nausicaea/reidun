"""
Provide a token bucket algorithm that limits the caller to a certain call rate
"""

import asyncio
import logging
from dataclasses import dataclass, field
from math import floor
from time import monotonic
from typing import Optional

_LOG: logging.Logger = logging.getLogger(__name__)


@dataclass
class TokenBucket:
    """
    The token bucket algorithm is used to limit the number of requests sent to an API, keeping a constant number
    of tokens (ex. requests) available per second. The same token bucket can be used for multiple different endpoints.
    """

    tokens: int = field(default=1)
    tokens_updated_at: float = field(default_factory=monotonic)
    max_tokens: int = field(default=10)

    async def take(self, rate_limit: Optional[float]) -> None:
        """
        Take a token or wait if there are no tokens left

        :param rate_limit: An optional rate limit in tokens (ex. requests) per second
        """

        # Allow rate limits to be disabled
        if rate_limit is None:
            return

        # Build tokens if there are none left
        while self.tokens < 1:
            now = monotonic()
            new_tokens = floor((now - self.tokens_updated_at) * rate_limit)
            if self.tokens + new_tokens >= 1:
                self.tokens = min(self.tokens + new_tokens, self.max_tokens)
                self.tokens_updated_at = now

            _LOG.debug("Waiting for a rate limiting token")
            await asyncio.sleep(1.0 / rate_limit)

        # Take a token
        self.tokens -= 1
