# webcite-haystack

[Haystack](https://haystack.deepset.ai) components for [Webcite](https://webcite.co), one evidence
suite for AI apps and agents: document parsing and OCR to Markdown, claim verification with
verdicts, citations bound to source passages, and source search.

| Component | Import | What it does | Credits |
|---|---|---|---|
| `WebciteDocumentConverter` | `haystack_integrations.components.converters.webcite` | PDFs, scans, images, spreadsheets and office files (paths, `ByteStream`s or `https://` URLs) to Markdown `Document`s | Per page, at cost; upload is free |
| `WebciteWebSearch` | `haystack_integrations.components.websearch.webcite` | Sources for a query as `Document`s (passage as content; URL, title, stance in `meta`) and `links` | 2 per search |
| `WebciteClaimVerifier` | `haystack_integrations.components.verifiers.webcite` | A verdict per claim, with the citations it rests on as `Document`s | 4 per claim |

Prices are on [webcite.co/pricing](https://webcite.co/pricing). The Free plan includes 100
credits, renewing every 30 days while credits remain.

## Install

<!-- Switch back to "pip install webcite-haystack" once it is published on PyPI. -->
```bash
pip install "git+https://github.com/strategyconnect/webcite-python.git@v0.1.0" "git+https://github.com/strategyconnect/webcite-haystack.git@v0.1.0"
export WEBCITE_API_KEY=...   # create one at https://webcite.co/api-keys
```

Python 3.10 or newer, Haystack 2.x. The key is read through a Haystack `Secret`
(`Secret.from_env_var("WEBCITE_API_KEY")` by default), so pipelines serialize without it.

## Convert documents to Markdown

```python
from haystack_integrations.components.converters.webcite import WebciteDocumentConverter

converter = WebciteDocumentConverter()            # mode="lite" for the faster, cheaper read
docs = converter.run(sources=["https://www.irs.gov/pub/irs-pdf/fw9.pdf"])["documents"]
print(docs[0].meta)
print(docs[0].content.splitlines()[0])
```

Output for page 1 of the form, from the response recorded from the API
([webcite.co/samples/doc-irs-w9.json](https://webcite.co/samples/doc-irs-w9.json)):

```text
{'source': 'https://www.irs.gov/pub/irs-pdf/fw9.pdf', 'state': 'complete', 'pages': 1, 'credits': 0.4966}
Form **W-9**
```

Check `meta["state"]`: anything other than `complete` comes with `meta["reason"]` naming what was
not read. The request stays open until every page is read; there is no job to poll.

## Verify claims

```python
from haystack_integrations.components.verifiers.webcite import WebciteClaimVerifier

verifier = WebciteClaimVerifier(max_citations=2)
out = verifier.run(claims=["The Great Wall of China is visible from the Moon with the naked eye."])
print(out["verdicts"][0]["result"], out["verdicts"][0]["credits"])
for doc in out["documents"]:
    print(doc.meta["stance"], doc.meta["url"])
```

Output, from the response recorded from the API on 24 November 2026
([webcite.co/samples/claim-great-wall.json](https://webcite.co/samples/claim-great-wall.json)):

```text
contradicted 4
contradicts https://www.nasa.gov/image-article/great-wall/
inconclusive https://www.britannica.com/question/Can-you-see-the-Great-Wall-of-China-from-space
```

Each document's content is the source passage the citation is bound to. Pass `source_urls` to
check claims against given pages instead of a web search. `verdicts[i]["response"]` keeps the full
API response.

## Search sources

```python
from haystack_integrations.components.websearch.webcite import WebciteWebSearch

search = WebciteWebSearch(top_k=3)
result = search.run(query="Apple total net sales fiscal 2024")
print(result["links"])
```

## In a pipeline

See [`examples/pipeline.py`](examples/pipeline.py). All three components support `to_dict` and
`from_dict`, so pipelines round-trip through YAML.

The same capabilities are also available to any MCP client from the hosted server at
`https://api.webcite.co/mcp` (OAuth or API key).

## Development

```bash
make install   # uv sync --all-groups
make check     # ruff, mypy, pytest
make build     # wheel and sdist in dist/
```

Tests run against recorded API responses in `tests/fixtures` with sockets disabled, so no test
reaches the network or spends credits.

## Links

- [Webcite API reference](https://webcite.co/api-docs)
- [Webcite Python SDK](https://github.com/strategyconnect/webcite-python)
- Issues: https://github.com/strategyconnect/webcite-haystack/issues
- Support: support@webcite.co

MIT licensed.
