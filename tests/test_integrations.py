import asyncio
import json
import random

import pytest
from flask import Response, abort, make_response, request
from http_server_mock import HttpServerMock  # type: ignore
from yarl import URL

from reidun.client import ApiClient
from reidun.request import ApiRequestVerbatim
from reidun.request_method import RequestMethod

bob: HttpServerMock = HttpServerMock(__name__)
cathrine: HttpServerMock = HttpServerMock(__name__)


# noinspection Mypy
@bob.route("/tax-returns", methods=["GET"])
async def tax_returns() -> Response:
    async with ApiClient(URL("http://127.0.0.1:9092")) as client:
        q = request.args.get("q")
        _req: ApiRequestVerbatim = (
            client.request_builder()
            .with_method(RequestMethod.GET)
            .with_params({"query": q} if q is not None else None)
            .build("/panopticon")
        )

        response, _ = await client.request_verbatim(_req)
        response_data = json.loads(response.decode("utf-8"))
        return make_response(response_data["tax_filings"][0])


# noinspection Mypy
@cathrine.route("/panopticon", methods=["GET"])
async def panopticon() -> Response:
    query = request.args.get("query")
    await asyncio.sleep(1)

    if query is not None and "Trump" in query:
        return make_response(
            {
                "first_names": ["Donnald", "John"],
                "last_names": ["Trump"],
                "tax_filings": [
                    {
                        "equity": 1000000000,
                        "debt": 2000000000000,
                    }
                ],
                "criminal_case_ids": [random.randint(0, 1000000) for _ in range(1000)],
                "lawsuits": None,
            }
        )
    else:
        abort(404)


@pytest.mark.asyncio
async def test_server_side_request_after_client_request_wrt_timeouts() -> None:
    with cathrine.run("127.0.0.1", 9092):
        with bob.run("127.0.0.1", 9091):
            async with ApiClient(URL("http://127.0.0.1:9091")) as alice:
                _req: ApiRequestVerbatim = (
                    alice.request_builder()
                    .with_method(RequestMethod.GET)
                    .with_params({"q": "*Trump*"})
                    .build("/tax-returns")
                )

                response, _ = await alice.request_verbatim(_req)
                response_data = json.loads(response.decode("utf-8"))
                assert response_data == {"equity": 1000000000, "debt": 2000000000000}
