# Status

Updated: 2026-11-27

## Phase

`deployed`

M1 through M8 are done. M3, M4, M5, and M7 passed on fakes. M6 and M8 are deployed. The public URL is `https://ca-fin-docs-rag.thankfulflower-24c321f8.swedencentral.azurecontainerapps.io`. `GET /health` and `GET /ready` returned status ok. `GET /` returns the Vite page from image `ghcr.io/eelitt/fin-docs-rag-api:7f341cfd66171397422f027a372c231563989246`. That tag is a container image, not a commit on current `main`. The live sheet has 22 rows. `ongoing_charge`, `sri`, and `holding_period` are `stated` on every row. Entry cost and exit cost are unchanged. `uv run ingest sheet` wrote those three columns and did not call a model. The public page does not mark the passage. Known limits are parked in `05-open-questions.md`. M7 is a local stdio server with `retrieve` and `compare_sentence`. The public app does not serve MCP. Do not start M9.

## Decision

Build a Python RAG service on Azure over a small corpus of public fund documents. The product is a cited fact sheet for that shelf, built when the documents are indexed, plus a follow-up question that cites or refuses. `POST /ask` takes an envelope: `request_id`, `caller`, `instrument_ids`, and `question`. v1 accepts only `caller: demo` and rejects any personal field before a model call. The response bodies and the `/ask` error checks are in `02-product.md`. The trace stores `instrument_ids` for the demo only. A later caller's ISIN list stays in that app's log. The trace does not store the question. The demo is a Vite React app served as static files by the same Container App. Evaluation and a trace of cost and retrieval stay in scope. It is a research aid, not a consumer robo-advisor.

The gitignored note `idea_one.md` is accepted on the domain and the lifecycle (retrieve, judge, answer, evaluate, observe). It is not accepted on Azure: the system runs on Azure. Writing "how this would move to Azure" does not close the gap. Do not implement that note.

## Last session

2026-11-27. Doc cleanup. The cited-sheet limits that this run does not fix are parked in `05-open-questions.md`. `docs/m6-setup.md` is deleted. `docs/azure_setup.md`, `idea_one.md`, and `docs/01-gap-map.md` stay on disk and are gitignored. `docs/01-gap-map.md` was removed from main history.

2026-11-26. Cited sheet columns. `domain/kid_cost.py` fills the ongoing cost, the risk indicator (`määritetty N`), and the recommended holding sentence, including `3 kuukautta` as printed. `uv run ingest sheet` replaced those three columns on the blob sheet and did not call a model. Public `GET /sheet` shows 22 rows, and all three columns are `stated` on every row. A compare of `FI0008804729` and `FI0008804687` states 0.3 and 0.9. `uv run pytest` was 80 passed and 1 skipped. The empty-cell `uv run eval-run` stays 9 of 29. The later run was 21 of 29: sheet 12 of 15, retrieve 6 of 10, refuse 3 of 4. Retrieval hit rate at 8 was 0.6. The misses are `near-pharos-phoebus` (`FI0008801907:costs:3:0` not in the first 8) and `near-eurooppa` (`FI0008801774:costs:3:0` not in the first 8). The three sheet misses are `fact-sri-4729`, `fact-sri-1733`, and `compare-sri-different-holding`: the router sent those risk-indicator questions to search. No query, filter, or golden-id change. The local page marks the quote in the passage. The public page does not, because it was not deployed.

## Corpus measurements

| Item | Value |
| --- | --- |
| Heading list | KID section keys, in order: `purpose`, `product`, `what`, `risks`, `inability`, `costs`, `holding`, `complaints`, `other`. Printed lines: Tarkoitus (one file prints Tämän asiakirjan tarkoitus), Tuote, Mikä tämä tuote on?, Mitkä ovat riskit ja mitä tuottoa sijoittaja voi saada?, Mitä tapahtuu, jos …, Mitä kuluja sijoittajalle aiheutuu?, Miten pitkäksi aikaa sijoitus olisi tehtävä…, Kuinka sijoittaja voi valittaa?, Muut olennaiset tiedot. English lines of the same sections are recognized. The longer report splits on its own uppercase headings, then on 800-token windows with 120 tokens of overlap. |
| Chunk sizes | Intact-test KID `FI0008804729`: 13 chunks, 8–1174 tokens. Limit 1200, overlap 100. Longer report `report-2026-q3`: 253 chunks, 2–800 tokens. Limit 800, overlap 120. Rechecked when M2 indexed the file. The earlier count of 244 is superseded. |
| Printed cost-row label | Two wordings. `FI0008804729`: Hallinnolliset maksut ja muut hallinto- tai toimintakulut. `FI0008804687`: Hallinnointipalkkio ja muut hallinto- tai toimintakulut. |
| Known cost figure used in the parser test | 0,30 % on `FI0008804729`. The second KID keeps 0,9 prosenttia in one chunk. |
| Known risk indicator used in the parser test | 2 on `FI0008804729` (the sentence contains määritetty 2). The second KID keeps määritetty 4 in one chunk. |

## Next action

Do not start M9. Do not deploy again unless the human asks. The marked passage is on the local page only. The manual workflow still needs the model endpoints as GitHub secrets.

## Blockers

Do not create Azure AI Search Basic or Azure Container Registry. `.github/workflows/tests.yml` downloads the PDFs before pytest. A push to `main` deploys the container app unless the commit message contains `[skip ci]`.

## Done when this project is interview-ready

All of these are visible in the public repo:

- The fact sheet shows a cited value, or an explicit empty cell, for a real public fund KID.
- A follow-up question over a real public fund document returns an answer with a citation, or an abstention.
- A checked-in eval set reports retrieval and faithfulness numbers, including questions the system must refuse.
- A trace shows retrieved passages, model, tokens, and cost for one real call.
- Azure resources are declared as infrastructure as code and the API is deployable as a container.
- The README has a short map of those signals.

## Session handoff template

Copy this shape when updating this file:

```
Updated: YYYY-MM-DD
Phase: planning | building | evaluating | deployed
Last session: one or two sentences of what changed.
Next action: the single next step.
Blockers: none, or a list.
```
