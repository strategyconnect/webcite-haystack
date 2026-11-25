from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import httpx
import pytest
from webcite import Webcite

FIXTURES = Path(__file__).parent / "fixtures"
ROUTES = {
    "/api/v1/verify": "claim-great-wall.json",
    "/api/v1/sources/search": "search-great-wall.json",
    "/api/v1/extract": "doc-irs-w9.json",
}


class RecordedApi:
    """Answers Webcite API calls from the saved responses and records each request."""

    def __init__(self) -> None:
        self.paths: list[str] = []
        self.bodies: list[Any] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.paths.append(request.url.path)
        if request.url.path == "/api/v1/upload":
            self.bodies.append(request.content)
            return httpx.Response(200, json={"successCode": 200, "data": {"asset_id": "a1"}})
        self.bodies.append(json.loads(request.content or b"{}"))
        return httpx.Response(
            200, json=json.loads((FIXTURES / ROUTES[request.url.path]).read_text())
        )


@pytest.fixture
def api() -> RecordedApi:
    return RecordedApi()


@pytest.fixture
def client(api: RecordedApi) -> Webcite:
    return Webcite("test-key", http_client=httpx.Client(transport=httpx.MockTransport(api)))
