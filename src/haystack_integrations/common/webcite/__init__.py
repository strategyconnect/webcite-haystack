"""Shared helpers for the Webcite Haystack components."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from haystack import Document
from haystack.utils import Secret

from webcite import Webcite

DEFAULT_KEY = Secret.from_env_var("WEBCITE_API_KEY")


def make_client(api_key: Secret, timeout: float | None) -> Webcite:
    return Webcite(api_key.resolve_value(), timeout=timeout)


def citations(response: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    groups = response.get("claim_groups") or []
    if groups and groups[0].get("citations") is not None:
        return list(groups[0]["citations"])
    return list(response.get("citations") or [])


def citation_document(citation: Mapping[str, Any]) -> Document:
    """One citation as a Document: the bound source passage as content."""
    bound = citation.get("passage") or {}
    passage = bound.get("text") or citation.get("snippet")
    meta = {
        "url": citation.get("url"),
        "title": citation.get("title"),
        "stance": citation.get("stance"),
        "citation_id": citation.get("id"),
        "passage_sha256": bound.get("sha256"),
    }
    return Document(
        content=str(passage or citation.get("title") or citation.get("url")),
        meta={k: v for k, v in meta.items() if v is not None},
    )
