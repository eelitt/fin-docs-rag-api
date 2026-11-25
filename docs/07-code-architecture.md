# Code architecture

Status: **decided**
Updated: 2026-11-25

How the Python code is split. Product behavior is in `02-product.md`. The model path is in `06-ai-architecture.md`. This file is the module map. Each module has one reason to change.

Through M4 the repo has the M3 modules plus `eval/score.py`, `eval/run.py`, `adapters/mlflow_log.py`, `eval/golden.json`, and the GitHub workflows. Telemetry and `frontend/` are later milestones.

## Rule

A module owns one job. A change to that job should land in that module and leave the others alone.

- The HTTP layer does not contain prompt text and does not import a vendor SDK. `GET /ready` calls the blob and search ports. Adapters make the Azure calls.
- A model step does not check its own quotes and does not call the next step.
- Domain functions do not read the network, the disk, or the environment.
- Vendor SDKs appear only in adapters.
- `composition.py` is the only place that builds real adapters. Tests pass fakes in.

Dependency direction, and nothing back:

```
http, ingest CLI, eval runner
        → pipeline
        → steps
        → domain, ports
adapters → ports, vendor SDKs
```

`domain` imports no other project package. `steps` do not import `adapters` or `http`. `adapters` do not import `steps`, `pipeline`, or `http`.

## Tree

```
src/fin_docs_rag/
  domain/
    models.py
    isin.py
    chunking.py
    verify.py
    calculate.py
  ports.py
  steps/
    route.py
    retrieve.py
    grade.py
    answer.py
    extract.py
  pipeline.py
  adapters/
    openai_chat.py
    openai_embed.py
    search.py
    blob_store.py
    prompts.py
    telemetry.py
    mlflow_log.py
  ingest/
    parse_pdf.py
    run.py
  http/
    app.py
  eval/
    score.py
    run.py
  trace.py
  config.py
  composition.py
prompts/
  router_v1.md
  grade_v1.md
  answer_v1.md
  extract_v1.md
frontend/
infra/
tests/
  domain/
  steps/
  pipeline/
  http/
  eval/
  integration/
```

`prompts/`, `frontend/`, and `infra/` stay outside the import package. Bicep is not imported by Python. Prompt text is not stored in Python source. The React app is not imported by Python. The image build copies its static files, and FastAPI serves them.

## Domain

Pure data and pure rules. No Azure, no FastAPI, no prompt wording.

| Module | Owns | Does not |
| --- | --- | --- |
| `domain/models.py` | `Chunk`, `Route`, `Citation`, `Answer`, `SheetCell`, `RequestEnvelope`, reason codes, the sheet columns | Decide a path, call a model, format HTTP |
| `domain/isin.py` | The ISIN regex and the scan of a question or a page | Search, or guess a fund name |
| `domain/chunking.py` | Heading split, the token windows from `06-ai-architecture.md`, and chunk ids `{doc_id}:{section}:{page}:{window}` | Open a PDF or embed a chunk |
| `domain/verify.py` | Chunk-id membership, quote substring, the 400-character cap, Finnish comma decimal against the model's number | Call the model again, or rewrite the answer |
| `domain/calculate.py` | The difference of two `stated` cells, both holding periods, and the comparison template. An empty cell produces no difference. The template does not rank the funds | Extract numbers from prose, or read the blob |

## Ports

`ports.py` holds the protocols the steps call. One protocol, one capability.

| Protocol | Method |
| --- | --- |
| `Chat` | `complete(prompt_id, payload) -> dict` |
| `Embedder` | `embed(text) -> list[float]` |
| `Searcher` | `hybrid(query, vector, isin_filter) -> list[Chunk]` |
| `PromptSource` | `load(prompt_id) -> str` |
| `BlobStore` | `put(name, bytes) -> None`, `get(name) -> bytes` |
| `Tracer` | `write(trace) -> None` |

A fake in tests is a small class in the test file that implements one protocol. Fakes are not a package of their own.

## Steps

One step, one model or search action. A step returns a domain object. It does not catch a failure and turn it into an answer. The pipeline sets `ungrounded` or `not_in_corpus`. `http/app.py` maps a dependency failure to HTTP 503.

| Module | Owns | Does not |
| --- | --- | --- |
| `steps/route.py` | The router call. Returns a `Route`. | Search, refuse by itself, or read the PDF |
| `steps/retrieve.py` | Embed `search_query`, call hybrid search, return chunks | Grade, filter on a fund name, or embed the raw question |
| `steps/grade.py` | The grade call. Returns the kept chunks, at most four | Answer, drop chunks for a fund-name preference, or drop chunks for any reason other than the model's `relevant` flag |
| `steps/answer.py` | The lookup call. Returns the draft answer and its citations | Run `verify`, or discard the draft |
| `steps/extract.py` | The ingest extract call for one KID. Returns raw column items | Compute a difference, assign `stated`, or fill the template |

The step names the prompt id (`router_v1`, and the others). Wording changes happen in `prompts/`. Call-shape changes happen in the step.

## Pipeline

`pipeline.py` is the only orchestrator. `answer_question(envelope, deps) -> Answer`. The envelope is the one in `02-product.md`. `caller` is copied onto the trace and is not sent to a step.

It sequences the steps from `06-ai-architecture.md`. A sheet-column question reads the stored sheet and calls `calculate`. Any other question applies the fund-name preference after grading, then calls `verify`. It builds the trace via `trace.py`. It does not talk to a vendor SDK, read prompt files, or know HTTP status codes. Ingest, not the question pipeline, calls `extract`.

`trace.py` builds one root span and one child span per model call, with the fields in `06-ai-architecture.md`. It does not store the raw question, the prompt, the completion, the caller secret, or a rejected field, and it does not export anywhere. Export is `adapters/telemetry.py`.

## Adapters

One adapter, one external system.

| Module | Owns | Does not |
| --- | --- | --- |
| `adapters/openai_chat.py` | Azure OpenAI chat, JSON schema, one retry on a broken schema | Choose a prompt, or interpret an answer |
| `adapters/openai_embed.py` | `text-embedding-3-small` | Index vectors |
| `adapters/search.py` | Index create and hybrid query. `content` uses the `fi.microsoft` analyzer | Embed, or grade |
| `adapters/blob_store.py` | Upload original PDFs and `sheet.json` to the private `documents` container, and read `sheet.json` back | Parse a PDF, or verify a cell |
| `adapters/prompts.py` | Read `prompts/` by id | Edit wording in code |
| `adapters/telemetry.py` | Send the spans from `trace.py` to Application Insights, with GenAI content capture off | Add prompt text, completion text, or the raw envelope |
| `adapters/mlflow_log.py` | Write one eval run | Run during a user request |

## Edges

| Module | Owns | Does not |
| --- | --- | --- |
| `http/app.py` | Serve the built React files at `GET /`. `GET /sheet`, `GET /compare`, `POST /ask`, `GET /health`, `GET /ready`. The bodies and the `/ask` check order are in `02-product.md`. Assign `request_id` only after those checks pass. A caller other than `demo` is HTTP 401 in v1, with no secret header. Count only accepted `/ask` calls toward the process limit of 20 per 10 minutes. The next one is HTTP 429 and is not traced. Map an `Answer` to status 200 and a dependency failure to 503 `{ "error": "unavailable", "request_id": "…" }`, with the trace in the log only. Access logs omit the body | Call Azure from a route handler, branch on intent, build the sheet, log a body or a secret, or treat the request limit as a spend cap |
| `frontend/` | The Vite React page: sheet, comparison, follow-up, disclaimer. Calls same-origin `/sheet`, `/compare`, and `/ask` | Contain a second copy of the refusal rules, call a model, or offer the original PDF |
| `ingest/parse_pdf.py` | PDF bytes to pages of text, including table text in reading order | Chunk, embed, upload, or call Document Intelligence |
| `ingest/run.py` | The ingest command: parse, chunk, upload, embed, push, extract one row per KID, verify, write `sheet.json` | Answer a question |
| `eval/score.py` | Compare an `Answer` to one golden item: path label (`sheet`, `retrieve`, or `refuse`), cited id, number, or reason code | Call a model |
| `eval/run.py` | Load the golden file, call the pipeline, score, hand the summary to MLflow | Live inside the web process |
| `config.py` | Read the environment once into a settings object | Open an Azure client |
| `composition.py` | Build settings, adapters, and the pipeline | Contain business rules |

`GET /health` does not construct the chat client and does not call a port. `GET /ready` calls the blob and search ports. It does not call the model, and it does not import a vendor SDK.

## Tests

| Folder | Exercises | Uses |
| --- | --- | --- |
| `tests/domain/` | Chunking, stable chunk ids, ISIN, verify, calculate, and the intact cost and risk-indicator strings from one real KID | No fakes and no network |
| `tests/steps/` | One step | A fake of the one port that step calls |
| `tests/pipeline/` | The five question types in `02-product.md`, and a sheet-column question that does not call extract | Fake steps or fake ports, never Azure |
| `tests/eval/` | The golden file on fakes, the path and refusal gate, and one MLflow log | Fake ports, never Azure |
| `tests/http/` | Status codes, the error object in `02-product.md`, a 400 that does not advance the rate limit, `question_too_long`, `GET /compare` for an ISIN that is not a row, `GET /sheet` making no model call, and an envelope with a forbidden field returning 400 without a model call | The pipeline and the sheet replaced with fakes |
| `tests/integration/` | Ingest and one live question | Azure credentials. Skipped when the credentials are absent |

A test that needs two vendor services is an integration test. A unit test that imports `openai` or `azure` is in the wrong folder.

## When a module is too big

Split it when it has a second reason to change. Typical cases:

- A file imports two vendor SDKs.
- A function both calls the model and checks a quote.
- A function both parses a PDF and decides chunk boundaries.
- HTTP code builds a prompt or a search filter.

Do not split a module that still has one reason to change just to add a layer.
