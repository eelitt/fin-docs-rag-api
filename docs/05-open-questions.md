# Open questions

Updated: 2026-11-27

No open product questions. M1, M2, and M3 are done, and the Azure setup is done. The ongoing-cost column key is `ongoing_charge`, chosen 2026-11-25. Known limits that this repo does not fix unless asked are under Parked.

## Closed

### Azure spend

Closed 2026-11-24. The project has to prove it runs, at a small bill. The cap is an Azure budget alert at $20. The design that stays inside that cap is in `03-architecture.md`: Search Free, GPT-4.1-mini and text-embedding-3-small on standard pay-as-you-go, Container Apps with `minReplicas` 0, no semantic ranker, no provisioned throughput. Region: Sweden Central when the two model deployments exist there.

Expected careful-month spend is a few dollars of tokens. Search Basic is forbidden because it is about $74 per month in Sweden Central for as long as the service exists.

### Corpus

Closed 2026-11-24. Use the corpus in `02-product.md`: 8–15 public Finnish fund KIDs, plus one longer public report section.

### AI path

Closed 2026-11-24. Updated 2026-11-25 for the fact sheet. The question path is one Python function. Sheet columns are extracted once per KID at ingest, checked, and stored. A follow-up the sheet cannot answer still routes, searches, grades, and cites. Quotes must be substrings of the source chunk. Comparison math is a template over stored cells. Detail is in `06-ai-architecture.md`.

Rejected, and not open:

- An agent framework (LangChain, LangGraph, LlamaIndex, Semantic Kernel) as the orchestrator.
- Foundry Agent Service or Foundry IQ agentic retrieval as the orchestrator.
- RAGAS or another judge model as the CI gate.
- Multi-turn chat in v1.
- A second chat model, OCR, or a model that reads the PDF.

### HTTP response shapes

Closed 2026-11-25. `GET /sheet`, `GET /compare`, and `POST /ask` bodies, the error object, and the `/ask` check order are in `02-product.md`. `GET /compare` takes `isin_a` and `isin_b` and compares the ongoing-cost column. A question longer than 1,000 characters is HTTP 400. The rate limit counts only envelopes that pass those checks. The two printed cost-row labels are in `STATUS.md`. The ongoing-cost column key is `ongoing_charge`, chosen 2026-11-25, with no alias.

## Parked

These are not blockers. The plan already chooses an answer. Reopen only by editing the decision docs.

- Databricks in v1: no. See M9.
- Classical ML model: no.
- Linking this repo to portfolio-tracker user data: no. A later app may send its name and public ISINs from its server, with a caller secret. The browser does not make that call. The trace for that caller omits the ISIN list. The envelope does not carry holdings or amounts. See `02-product.md` and `03-architecture.md`.
- The example role's close date driving this repo: no. Apply to that role with portfolio-tracker. This repo follows `04-milestones.md`.

### Known limits

Recorded 2026-11-27. These are not open questions. Do not start them unless the human asks.

- `ingest index` overlays a grammar cell only when it is `stated`. A miss leaves the model cell. `ingest sheet` refuses the upload. Do not change that split.
- `3 kuukautta` is stored as `3`. The compare template labels a holding-period difference as years. Do not convert `3` into `0.25`.
- The marked passage, and a holding quote that already ends with `.`, are correct on the local page. The public image still lacks the mark and still adds a second period. Do not deploy unless asked.
- Router misses `fact-sri-4729`, `fact-sri-1733`, and `compare-sri-different-holding`, and retrieval misses `near-pharos-phoebus` and `near-eurooppa`, stay as recorded in `STATUS.md`. No query, filter, golden-id, chunk-size, or ranker change.
- The grammar covers the three Finnish layouts in the current 12 KIDs. A new wording fails `ingest sheet`. There is no grammar id on the cell. Do not add one.
- `passage` is the collapsed chunk, copied onto every share-class row, and public `GET /sheet` already returns it. Do not trim it.
- When several chunks share the same number, the first chunk wins. If that quote fails the gate, the cell is `not_extracted`. The current 12 files do not hit this. Do not change the gate.
- Image tags `7f341cfd66171397422f027a372c231563989246` and `4c0358ab339a74809b612e4eb66f90f6c6e389ba` are GHCR tags, not commits on current `main`. Do not check them out.
- Reopening the AI-path rejections above: only by editing `06-ai-architecture.md` and recording the reversal in `STATUS.md`.
- Treating "which is cheaper?" as advice: no. It is a comparison of two stored cells. The template states the difference and does not rank the funds. See `02-product.md`.
- A separate frontend host: no. The UI is a Vite React app built to static files and served by the same Container App. See `03-architecture.md`.
- The printed cost-row label: not open as a product choice. Both wordings are in `STATUS.md`. The column key is `ongoing_charge`, chosen 2026-11-25. There is no alias.
