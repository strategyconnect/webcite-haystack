# Test fixtures

- `claim-great-wall.json`: a verification response recorded from the Webcite API on
  24 November 2026 (also published at https://webcite.co/samples/claim-great-wall.json).
- `doc-irs-w9.json`: an extraction response recorded from the Webcite API (also published at
  https://webcite.co/samples/doc-irs-w9.json).
- `search-great-wall.json`: built from the citations of `claim-great-wall.json` in the shape a
  source search returns (`claim_groups[0].citations`, 2 credits). It is not a recorded search
  response; it exists to test how results are formatted.

Tests serve these through `httpx.MockTransport`; no test reaches the network.
