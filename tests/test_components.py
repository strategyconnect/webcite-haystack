from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

import pytest
from haystack import Pipeline
from haystack.dataclasses import ByteStream
from haystack.utils import Secret
from webcite import Webcite

from haystack_integrations.components.converters.webcite import WebciteDocumentConverter
from haystack_integrations.components.verifiers.webcite import WebciteClaimVerifier
from haystack_integrations.components.websearch.webcite import WebciteWebSearch
from tests.conftest import RecordedApi

W9 = "https://www.irs.gov/pub/irs-pdf/fw9.pdf"
NASA = "https://www.nasa.gov/image-article/great-wall/"


def with_client(component: Any, client: Webcite) -> Any:
    component._client = client
    return component


def test_search_returns_passages_and_links(client: Webcite, api: RecordedApi) -> None:
    result = with_client(WebciteWebSearch(top_k=3), client).run(query="great wall moon")
    assert len(result["documents"]) == 3
    assert "isn't visible from the moon" in result["documents"][0].content
    assert result["documents"][0].meta["stance"] == "contradicts"
    assert result["links"][0] == NASA
    assert api.bodies == [{"query": "great wall moon", "limit": 3}]


def test_search_top_k_at_run_time(client: Webcite, api: RecordedApi) -> None:
    result = with_client(WebciteWebSearch(), client).run(query="q", top_k=1)
    assert len(result["documents"]) == 1
    assert api.bodies[0]["limit"] == 1


def test_verifier_returns_verdict_and_citations(client: Webcite, api: RecordedApi) -> None:
    claim = "The Great Wall of China is visible from the Moon with the naked eye."
    out = with_client(WebciteClaimVerifier(max_citations=2), client).run(
        claims=[claim], source_urls=[NASA]
    )
    verdict = out["verdicts"][0]
    assert (verdict["result"], verdict["credits"]) == ("contradicted", 4)
    assert verdict["response"]["claim_groups"][0]["claim"] == claim
    assert [d.meta["url"] for d in out["documents"]][0] == NASA
    assert all(d.meta["claim"] == claim for d in out["documents"])
    assert len(out["documents"]) == 2
    assert api.bodies[0]["source_urls"] == [NASA]


def test_converter_reads_url_to_markdown(client: Webcite, api: RecordedApi) -> None:
    out = with_client(WebciteDocumentConverter(mode="lite"), client).run(
        sources=[W9], meta={"team": "tax"}
    )
    doc = out["documents"][0]
    assert doc.content.startswith("Form **W-9**")
    assert doc.meta == {
        "team": "tax",
        "source": W9,
        "state": "complete",
        "pages": 1,
        "credits": 0.4966,
    }
    assert api.bodies == [{"asset_url": W9, "mode": "lite"}]


def test_converter_uploads_local_files_and_streams(
    client: Webcite, api: RecordedApi, tmp_path: Path
) -> None:
    pdf = tmp_path / "w9.pdf"
    pdf.write_bytes(b"%PDF-1.4 test")
    stream = ByteStream(data=b"%PDF-1.4 other", meta={"file_name": "other.pdf"})
    out = with_client(WebciteDocumentConverter(), client).run(sources=[pdf, stream])
    assert [d.meta["source"] for d in out["documents"]] == [str(pdf), "other.pdf"]
    assert api.paths == ["/api/v1/upload", "/api/v1/extract"] * 2
    assert b"%PDF-1.4 test" in api.bodies[0]
    assert api.bodies[1] == {"asset_id": "a1"}


@pytest.mark.parametrize("cls", [WebciteWebSearch, WebciteClaimVerifier, WebciteDocumentConverter])
def test_serialization_round_trip_keeps_env_secret(cls: Any) -> None:
    data = cls().to_dict()
    assert data["init_parameters"]["api_key"] == {
        "type": "env_var",
        "env_vars": ["WEBCITE_API_KEY"],
        "strict": True,
    }
    assert cls.from_dict(copy.deepcopy(data)).to_dict() == data


def test_pipeline_yaml_round_trip(monkeypatch: pytest.MonkeyPatch) -> None:
    pipe = Pipeline()
    pipe.add_component("search", WebciteWebSearch(top_k=2))
    pipe.add_component("convert", WebciteDocumentConverter(mode="lite"))
    loaded = Pipeline.loads(pipe.dumps())
    assert loaded.get_component("search").top_k == 2
    assert loaded.get_component("convert").mode == "lite"


def test_missing_key_names_the_variable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("WEBCITE_API_KEY", raising=False)
    with pytest.raises(ValueError, match="WEBCITE_API_KEY"):
        WebciteWebSearch().warm_up()


def test_token_secret_builds_a_client() -> None:
    search = WebciteWebSearch(api_key=Secret.from_token("webcite_test"))
    search.warm_up()
    assert search._client is not None
