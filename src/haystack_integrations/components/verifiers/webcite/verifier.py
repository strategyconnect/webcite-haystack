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
class WebciteClaimVerifier:
    """Check claims against sources with Webcite (4 credits per claim with stance and verdict).

    For each claim, returns a verdict (``result`` and ``summary``) and the citations it rests on
    as Documents whose content is the bound source passage. ``source_urls`` restricts the check
    to given pages instead of a web search.

    ```python
    from haystack_integrations.components.verifiers.webcite import WebciteClaimVerifier

    verifier = WebciteClaimVerifier()
    result = verifier.run(claims=["The Great Wall of China is visible from the Moon."])
    print(result["verdicts"][0]["result"])
    ```
    """

    def __init__(
        self,
        api_key: Secret = DEFAULT_KEY,
        max_citations: int = 5,
        timeout: float | None = None,
    ) -> None:
        self.api_key = api_key
        self.max_citations = max_citations
        self.timeout = timeout
        self._client: Webcite | None = None

    def warm_up(self) -> None:
        if self._client is None:
            self._client = make_client(self.api_key, self.timeout)

    def to_dict(self) -> dict[str, Any]:
        return default_to_dict(
            self,
            api_key=self.api_key.to_dict(),
            max_citations=self.max_citations,
            timeout=self.timeout,
        )

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> WebciteClaimVerifier:
        deserialize_secrets_inplace(data["init_parameters"], keys=["api_key"])
        return default_from_dict(cls, data)

    @component.output_types(verdicts=list[dict[str, Any]], documents=list[Document])
    def run(self, claims: list[str], source_urls: list[str] | None = None) -> dict[str, Any]:
        """``documents`` holds every claim's citations; each has ``meta["claim"]``."""
        self.warm_up()
        assert self._client is not None
        verdicts: list[dict[str, Any]] = []
        documents: list[Document] = []
        for claim in claims:
            response = self._client.verify(claim, source_urls=source_urls or None)
            groups = response.get("claim_groups") or []
            verdict = (groups[0].get("verdict") if groups else None) or {}
            verdicts.append(
                {
                    "claim": claim,
                    "result": verdict.get("result"),
                    "summary": verdict.get("summary"),
                    "credits": (response.get("usage") or {}).get("credits"),
                    "response": dict(response),
                }
            )
            for cited in citations(response)[: self.max_citations]:
                doc = citation_document(cited)
                documents.append(Document(content=doc.content, meta={**doc.meta, "claim": claim}))
        return {"verdicts": verdicts, "documents": documents}
