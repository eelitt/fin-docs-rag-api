# Status

Updated: 2026-11-26

## Phase

`deployed`

M1 passed. M2 passed: ingest uploaded the corpus, embedded it, and pushed index `chunks`. A hybrid query for the known charge returns `FI0008804729:costs:3:0`, and that chunk contains `0,30 %`. M3 passed on fakes. M4 passed on fakes: `eval/golden.json` has 29 items, and `uv run pytest` scores that file on fakes. The live hybrid query is skipped when Azure credentials are not in the environment. With those credentials it runs too. The manual live eval was not run. M5 passed on fakes: an accepted `/ask` writes the trace object to the log, a rejected envelope does not, and the same fields export to Application Insights only when `APPLICATIONINSIGHTS_CONNECTION_STRING` is set. M6 is deployed. The public URL is `https://ca-fin-docs-rag.thankfulflower-24c321f8.swedencentral.azurecontainerapps.io`. `GET /health` and `GET /ready` returned status ok. `POST /ask` for the ongoing cost of `FI0008804729` returned HTTP 200 and the sentence that the cost was not extracted. Every `ongoing_charge` cell in the live sheet is `not_extracted`. The setup notes are in gitignored `docs/m6-setup.md`. M7 passed on fakes. A local stdio server exposes `retrieve` and `compare_sentence`. The public app does not serve MCP. M8 is in the working tree and is not deployed: `frontend/` is the Vite page, the image build copies it, and FastAPI serves `frontend/dist` at `GET /`. The public URL still serves the previous image.

## Decision

Build a Python RAG service on Azure over a small corpus of public fund documents. The product is a cited fact sheet for that shelf, built when the documents are indexed, plus a follow-up question that cites or refuses. `POST /ask` takes an envelope: `request_id`, `caller`, `instrument_ids`, and `question`. v1 accepts only `caller: demo` and rejects any personal field before a model call. The response bodies and the `/ask` error checks are in `02-product.md`. The trace stores `instrument_ids` for the demo only. A later caller's ISIN list stays in that app's log. The trace does not store the question. The demo is a Vite React app served as static files by the same Container App. Evaluation and a trace of cost and retrieval stay in scope. It is a research aid, not a consumer robo-advisor.

`idea_one.md` is accepted on the domain and the lifecycle (retrieve, judge, answer, evaluate, observe). It is not accepted on Azure: the system runs on Azure. Writing "how this would move to Azure" does not close the gap.

## Last session

2026-11-26. M8 adds the Vite page, serves the built files at `GET /`, and extends the root README. `uv run pytest` was 65 passed and 1 skipped. `uv run eval-run` against Azure was not ok: 9 of 29 items passed, and the retrieval hit rate at 8 was 0.6 (3 of 5). One accepted `POST /ask` on the deployed app returned a trace, and that trace is in the README. The new page is not deployed.

## Corpus measurements

| Item | Value |
| --- | --- |
| Heading list | KID section keys, in order: `purpose`, `product`, `what`, `risks`, `inability`, `costs`, `holding`, `complaints`, `other`. Printed lines: Tarkoitus (one file prints Tämän asiakirjan tarkoitus), Tuote, Mikä tämä tuote on?, Mitkä ovat riskit ja mitä tuottoa sijoittaja voi saada?, Mitä tapahtuu, jos …, Mitä kuluja sijoittajalle aiheutuu?, Miten pitkäksi aikaa sijoitus olisi tehtävä…, Kuinka sijoittaja voi valittaa?, Muut olennaiset tiedot. English lines of the same sections are recognized. The longer report splits on its own uppercase headings, then on 800-token windows with 120 tokens of overlap. |
| Chunk sizes | Intact-test KID `FI0008804729`: 13 chunks, 8–1174 tokens. Limit 1200, overlap 100. Longer report `report-2026-q3`: 253 chunks, 2–800 tokens. Limit 800, overlap 120. Rechecked when M2 indexed the file. The earlier count of 244 is superseded. |
| Printed cost-row label | Two wordings. `FI0008804729`: Hallinnolliset maksut ja muut hallinto- tai toimintakulut. `FI0008804687`: Hallinnointipalkkio ja muut hallinto- tai toimintakulut. |
| Known cost figure used in the parser test | 0,30 % on `FI0008804729`. The second KID keeps 0,9 prosenttia in one chunk. |
| Known risk indicator used in the parser test | 2 on `FI0008804729` (the sentence contains määritetty 2). The second KID keeps määritetty 4 in one chunk. |

## Next action

Do not start M9. Deploy the M8 image only when the human asks. The live sheet still has 22 rows and every `ongoing_charge` cell is `not_extracted`. The manual workflow still needs the model endpoints as GitHub secrets. The live numbers in the README are from a local `uv run eval-run`.

## Blockers

Do not create Azure AI Search Basic or Azure Container Registry. `sheet.json` is in the blob and its cost cells are `not_extracted`. Pull-request pytest still fails on GitHub because `data/pdfs/` is gitignored and the workflow does not download the PDFs.

## Done when this project is interview-ready

All of these are visible in the public repo:

- The fact sheet shows a cited value, or an explicit empty cell, for a real public fund KID.
- A follow-up question over a real public fund document returns an answer with a citation, or an abstention.
- A checked-in eval set reports retrieval and faithfulness numbers, including questions the system must refuse.
- A trace shows retrieved passages, model, tokens, and cost for one real call.
- Azure resources are declared as infrastructure as code and the API is deployable as a container.
- The README maps each of those to a requirement in `01-gap-map.md`.

## Session handoff template

Copy this shape when updating this file:

```
Updated: YYYY-MM-DD
Phase: planning | building | evaluating | deployed
Last session: one or two sentences of what changed.
Next action: the single next step.
Blockers: none, or a list.
```
