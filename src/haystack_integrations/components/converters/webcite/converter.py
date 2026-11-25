from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

from haystack import Document, component, default_from_dict, default_to_dict
from haystack.dataclasses import ByteStream
from haystack.utils import Secret, deserialize_secrets_inplace

from haystack_integrations.common.webcite import DEFAULT_KEY, make_client
from webcite import Webcite

Source = str | Path | ByteStream


@component
class WebciteDocumentConverter:
    """Read PDFs, scans, images, spreadsheets and office files into Markdown Documents.

    Sources may be local paths, ``ByteStream`` objects (with ``meta["file_name"]``) or
    ``https://`` URLs. Local files and byte streams are uploaded first (free); extraction is
    metered per page at cost. Each Document's ``meta`` has ``state``, ``pages`` and ``credits``;
    when ``state`` is not ``complete``, ``reason`` names what was not read.

    ```python
    from haystack_integrations.components.converters.webcite import WebciteDocumentConverter

    converter = WebciteDocumentConverter(mode="lite")
    docs = converter.run(sources=["https://www.irs.gov/pub/irs-pdf/fw9.pdf"])["documents"]
    ```
    """

    def __init__(
        self,
        api_key: Secret = DEFAULT_KEY,
        mode: Literal["standard", "lite"] | None = None,
        timeout: float | None = None,
    ) -> None:
        self.api_key = api_key
        self.mode = mode
        self.timeout = timeout
        self._client: Webcite | None = None

    def warm_up(self) -> None:
        if self._client is None:
            self._client = make_client(self.api_key, self.timeout)

    def to_dict(self) -> dict[str, Any]:
        return default_to_dict(
            self, api_key=self.api_key.to_dict(), mode=self.mode, timeout=self.timeout
        )

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> WebciteDocumentConverter:
        deserialize_secrets_inplace(data["init_parameters"], keys=["api_key"])
        return default_from_dict(cls, data)

    def _extract(self, client: Webcite, source: Source) -> tuple[dict[str, Any], str]:
        if isinstance(source, str) and source.startswith("https://"):
            return dict(client.extract(asset_url=source, mode=self.mode)), source
        if isinstance(source, ByteStream):
            name = str(source.meta.get("file_name") or "")
            asset = client.upload(source.data, filename=name)["data"]
        else:
            name = str(source)
            asset = client.upload(Path(source))["data"]
        return dict(client.extract(asset["asset_id"], mode=self.mode)), name

    @component.output_types(documents=list[Document])
    def run(self, sources: list[Source], meta: dict[str, Any] | None = None) -> dict[str, Any]:
        self.warm_up()
        assert self._client is not None
        documents = []
        for source in sources:
            response, name = self._extract(self._client, source)
            usage = response.get("usage") or {}
            info = {
                "source": name,
                "state": response.get("state"),
                "reason": response.get("reason"),
                "pages": usage.get("pages"),
                "credits": usage.get("credits"),
            }
            documents.append(
                Document(
                    content=response.get("markdown"),
                    meta={**(meta or {}), **{k: v for k, v in info.items() if v is not None}},
                )
            )
        return {"documents": documents}
