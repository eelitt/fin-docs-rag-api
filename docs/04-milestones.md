# Milestones

Status: **decided**
Updated: 2026-11-25

Build in order. A milestone is done only when its check passes. Do not open a later milestone to make the repo look fuller.

## M1 — Corpus and parse

Offline. No Azure.

- Sources manifest and download script. A `.gitignore` covers `.env`, downloaded PDFs, and MLflow runs before the first code commit.
- Parser that yields pages. A test loads one real KID and asserts that a known cost figure and a known risk indicator each appear intact inside a single chunk. If that test fails, change the parser before M2. No OCR and no Document Intelligence.
- Chunk ids are `{doc_id}:{section}:{page}:{window}`. `window` is `0` when the section is one chunk.
- Chunker. After measuring two real files, record the final heading list, chunk sizes, and the printed cost-row label in `STATUS.md` only.
- Tests on at least two real downloaded documents: a KID and the longer document.

Check: `pytest` green with no cloud credentials, including the intact-figure test.

## M2 — Index

- Bicep for resource group, storage, search, OpenAI, Key Vault.
- Ingest command: upload blobs, embed, push to the index.
- Hybrid query function returning chunk ids and snippets.
- Integration test skipped unless Azure credentials are present.

Check: one manual query returns the chunk that contains a known charge or risk figure.

## M3 — Sheet, answer, cite, refuse

- Workflow in `03-architecture.md`.
- Ingest writes `sheet.json`: one extract call per KID, then the quote check. Cells are `stated`, `not_stated`, or `not_extracted`.
- `GET /sheet` and `GET /compare` read that file and do not call the model. `GET /compare` takes `isin_a` and `isin_b` and compares the ongoing-cost column with the English template in `06-ai-architecture.md`. The model does not write the difference. `GET /compare` is the demo route. A KID with no parseable ISIN fails ingest and does not become a row.
- `POST /ask` uses the request envelope, the response object, and the error checks in `02-product.md`. A sheet column is served from `sheet.json`. Any other question uses retrieve, grade, and a cited answer. A body with a field outside the envelope is HTTP 400 and does not call the model. A failed check does not count toward the rate limit.
- Tests with a fake retriever and a fake model for the five question types, plus one sheet row of each cell state.

Check: the five question types in `02-product.md` pass on fakes, and a sheet request does not call the fake model.

## M4 — Evaluation

- Golden file: the five types, expanded to a small set (target 25–40 items). Include near-misses: two funds with similar names, a fact the corpus does not state, and a comparison whose holding periods differ. Each item has a path label from `06-ai-architecture.md` (`sheet`, `retrieve`, or `refuse`) and an outcome: must cite a source id, must abstain, or must match a number.
- Retrieval metrics on the golden set: hit rate at k for items that name a source.
- A faithfulness check: a generated answer cites only ids retrieved this turn, a sheet answer cites only the stored cell, and a refused item has no answer body.
- GitHub Actions runs the fake-model tests on pull requests.
- MLflow logs a live run when the manual workflow is used.

Check: the golden file is in git. The PR workflow fails if a refusal item returns an answer body, or if a run takes a path other than its label.

## M5 — Traces

- One root span per `/ask`, with a child span for each model call, as in `06-ai-architecture.md`. The root carries `request_id`, `caller`, latency, total tokens, cost estimate, chunk ids, and reason code. It carries `instrument_ids` only for `caller: demo`. Each child carries its own latency, tokens, prompt id, and model version. The raw question, the prompt, the completion, and the caller secret are not fields. A rejected envelope is not traced. Application Insights is created with content capture off and a 0.1 GB daily cap.
- Export to Application Insights when deployed. Local runs write the same object to the log.

Check: one real call's trace is pasted into the README later, at M8. Until then, a test asserts the fields exist.

## M6 — Deploy

- Dockerfile.
- Container Apps in the same Bicep file. Liveness probe `GET /health`. Readiness probe `GET /ready`.
- The Container App identity can read the blob, query the index, and call the model deployments. It cannot write the blob or the index. Ingest uses a separate principal that can write. Neither principal is a subscription owner. The container has no API keys in its environment.
- GitHub Actions deploy on main, using GitHub secrets.
- Teardown documented as a single Azure CLI command.

Check: the deployed URL returns `GET /health` and `GET /ready`, and `POST /ask` answers one scripted question. The page can still be a placeholder at this milestone. Record the URL in `STATUS.md`.

## M7 — MCP

- MCP server exposing the same search function and `domain/calculate.py`. The model does not receive a general calculator.
- The server is not mounted on the public ingress. README shows one local client call.

Check: the tool names and schemas match the functions the API uses. No second implementation of search. The public URL does not serve MCP.

## M8 — Demo and README

- `frontend/` is the Vite React app from `02-product.md`: the fact sheet, a two-fund comparison, the follow-up box, citations, refusal, trace, and the disclaimer.
- The production image builds those static files, and the same Container App serves them at `GET /`. No second host.
- README: what it is, how to run locally, how to deploy, eval numbers from the latest live run, cost note, and a short map onto `01-gap-map.md`.
- Disclaimer: research aid over public documents, not investment advice, and not a product of any bank or fund company.

Check: a new reader can run the demo from the README without this `docs/` folder.

## M9 — Later, only after M8

Databricks is optional and only if the human asks. The smallest honest version is: parsed document metadata and eval metrics land in a Delta table, and the same MLflow experiment is viewed there. Do not start M9 to decorate the README.

## Suggested session size

One milestone per session. End by updating `STATUS.md`.
