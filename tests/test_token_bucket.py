from collections import deque
from time import monotonic
from typing import Deque

import pytest

from reidun.token_bucket import TokenBucket


@pytest.mark.asyncio
async def test_take() -> None:
    tb = TokenBucket()
    rate_limit = 5.0

    niter: int = 100
    rates: Deque[float] = deque(maxlen=10)
    timestamp: float = monotonic()

    for _ in range(niter):
        await tb.take(rate_limit)

        # Measure the time between calls to _take_token
        current = monotonic()
        rates.append(1.0 / (current - timestamp))
        timestamp = current

    assert sum(rates) / len(rates) <= rate_limit
