from __future__ import annotations

from typing import Any

from haystack import Document, component, default_from_dict, default_to_dict
from haystack.utils import Secret, deserialize_secrets_inplace

from haystack_integrations.common.webcite import (
    DEFAULT_KEY,
    citation_document,
    citations,
    make_client,
)
from webcite import Webcite


@component
class WebciteWebSearch:
    """Find sources for a query with Webcite source search (2 credits per search).

    Returns one Document per source, with the matching source passage as content and the URL,
    title and stance in ``meta``, plus the list of URLs.

    ```python
    from haystack_integrations.components.websearch.webcite import WebciteWebSearch

    search = WebciteWebSearch(top_k=3)
    result = search.run(query="Apple total net sales fiscal 2024")
    ```
    """

    def __init__(
        self, api_key: Secret = DEFAULT_KEY, top_k: int | None = 5, timeout: float | None = None
    ) -> None:
        self.api_key = api_key
        self.top_k = top_k
        self.timeout = timeout
        self._client: Webcite | None = None

    def warm_up(self) -> None:
        if self._client is None:
            self._client = make_client(self.api_key, self.timeout)

    def to_dict(self) -> dict[str, Any]:
        return default_to_dict(
            self, api_key=self.api_key.to_dict(), top_k=self.top_k, timeout=self.timeout
        )

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> WebciteWebSearch:
        deserialize_secrets_inplace(data["init_parameters"], keys=["api_key"])
        return default_from_dict(cls, data)

    @component.output_types(documents=list[Document], links=list[str])
    def run(self, query: str, top_k: int | None = None) -> dict[str, Any]:
        self.warm_up()
        assert self._client is not None
        limit = top_k if top_k is not None else self.top_k
        found = citations(self._client.search(query, limit=limit))
        documents = [citation_document(c) for c in (found[:limit] if limit else found)]
        return {
            "documents": documents,
            "links": [d.meta["url"] for d in documents if "url" in d.meta],
        }
