# Architecture

Status: **decided** for v1. Databricks remains deferred.
Updated: 2026-11-25

## Stack

| Piece | Choice | Why this one |
| --- | --- | --- |
| Language | Python 3.12 | The posting asks for strong Python. The other repo is TypeScript. |
| API | FastAPI | Small, typed, easy to containerize. |
| Documents | Blob Storage | Original files stay out of git. The manifest stays in git. |
| Retrieval | Azure AI Search dedicated Free tier, hybrid keyword + vector | 15 KIDs fit in the 50 MB free quota. Semantic ranker is off because it is not available on this tier. |
| Models | Azure OpenAI, standard pay-as-you-go. Chat: GPT-4.1-mini global. Embeddings: text-embedding-3-small global. | These two models embed chunks and write or refuse answers. PDF parsing stays in Python. No provisioned throughput. |
| Secrets | Key Vault, local `.env` for dev | No keys in the repo. |
| Host | One Container App, Consumption, min replicas 0 | The public demo URL. Serves the API and the page. |
| IaC | Bicep | One language for the resource group. |
| CI | GitHub Actions | Tests on every push. Live eval is a separate workflow so a pull request does not spend tokens. |
| Traces | OpenTelemetry to Application Insights | One root span per `/ask`, one child span per model call. Latency, tokens, result type, retrieved ids. |
| Eval log | MLflow, file store locally | Prompt and eval-set versions get a run. The tracking URI can move later. A Databricks workspace is not required for this. |
| Tools | MCP server exposing search and `domain/calculate.py` | Same functions the API uses. The compare path fills a template. There is no general calculator. |
| UI | Vite and React, built to static files and served by FastAPI at `/` | The fact sheet is a table, a two-fund comparison, and a follow-up. One Container App. No Node process in production, and no second host. |

## Workflow

Two paths. The fact sheet is built once, at ingest. A question is one Python function. Neither path is a swarm of agents. Calls, schemas, the quote check, and rejected libraries are in `06-ai-architecture.md`. The columns and cell states are in `02-product.md`.

### Sheet, at ingest

1. Parse, chunk, embed, and index the documents.
2. For each KID, one extract call reads that fund's chunks and returns the sheet columns.
3. Verify each claimed value. A passing quote becomes `stated`. An absent field becomes `not_stated`. A failed quote or figure check becomes `not_extracted`, and the claimed value is dropped.
4. Write `sheet.json` to the private blob container.

`GET /sheet` reads that file. `GET /compare` fills the comparison template from two stored cells. Neither request calls a model.

### Question, `POST /ask`

1. Route the question. Advice with high confidence returns `advice_refused` and does not search. Uncertain advice still continues, and a later step may still refuse.
2. If the question is a sheet column for a fund on the sheet, or a comparison of two sheet rows, return the stored cells. Resolve the fund from `instrument_ids` when that list is present, and from the question only when the list is empty. Do not search and do not call the model again. An empty cell stays empty. The comparison template states both figures, both holding periods, and the difference, and it does not rank the funds.
3. Otherwise retrieve the top chunks with hybrid search. This is the longer report, a fact the columns do not cover, a fund the sheet does not resolve, and uncertain advice. A non-empty `instrument_ids` list is the only hard filter. When the list is empty, an ISIN in the question is the hard filter.
4. Grade chunks. Drop ones that do not bear on the question. If the router named a fund and the call had no ISIN, prefer kept chunks that contain that name. Use the unfiltered kept set only when the preference keeps nothing.
5. If nothing remains, return `not_in_corpus`.
6. Generate an answer from the kept chunks.
7. Verify every citation. The chunk id must be one of the kept chunks, and the quote must be a substring of that chunk. A figure must match the number printed in the quote. If a claimed answer fails the check, return `ungrounded` and discard the draft.
8. Log the trace: one root span and one child span per model call, as in `06-ai-architecture.md`. Do not write the raw question into the trace. `GET /sheet` and `GET /compare` do not write that trace. Failure results are the table in that same file.

`ungrounded` is only the failed check in step 7. An empty grade result is `not_in_corpus`.

The question path is one Python function. It is not several chat models choosing tools. MCP, later, exposes the same search function and `domain/calculate.py`.

## Deploy and demo

One Container App in `rg-fin-docs-rag`, Sweden Central, name `ca-fin-docs-rag`. The environment is Consumption. Minimum replicas stay 0. The first request after idle can take several seconds.

The same process serves:

- `GET /` — the React app.
- `GET /sheet` — the fact sheet from `sheet.json`, in the shape in `02-product.md`. No model call.
- `GET /compare` — `isin_a` and `isin_b`, and the ongoing-cost sentence. The body is in `02-product.md`. No model call.
- `POST /ask` — the follow-up. Body is the request envelope in `02-product.md`. HTTP 200 is the answer object there, including `request_id` and the trace. A failed check is the error object there. A field other than the four envelope fields is HTTP 400 and does not call the model.
- `GET /health` — liveness. The process is up. It does not touch Azure.
- `GET /ready` — readiness. It reads `sheet.json` and pings search. It does not call a model. A missing sheet or a missing index is HTTP 503.

The Container App liveness probe is `/health`. The readiness probe is `/ready`. A deleted Free search service then stops traffic without a restart loop.

The UI is a Vite React app in `frontend/`. The image build produces static files, and FastAPI serves them at `/` on the same origin. There is no Node process in production, no Static Web Apps site, and no second host. The page is a demo client. Portfolio-tracker does not call this API in v1.

The sheet and compare reads are public because the documents are public. There is no end-user sign-in. `POST /ask` allows 20 accepted requests per 10 minutes in this process. A request that fails the error checks in `02-product.md` does not count. Past the limit the response is HTTP 429 with no model call and no trace. The counter resets when the app scales to zero and is not shared across replicas. The spend caps remain the tokens-per-minute quota, the budget alert, and deleting the app when it is not being demoed.

`caller: demo` is the same-origin page. That page calls `/ask` from the browser and has no secret in the static files. Until a second caller is registered, any other `caller` is HTTP 401, the model is not called, and nothing is traced. There is no secret header in v1. After that registration, the other caller is a server of an app the human owns. That server sends a Key Vault secret in a header. The browser of that app never sees the secret and never calls `/ask`. A missing or wrong secret is the same HTTP 401. The header is not an envelope field and is not logged. `GET /sheet` stays public. `GET /compare` is public too, and only the demo calls it, with `isin_a` and `isin_b` from the shelf. Another app compares from `GET /sheet` on its own server.

MCP is not on the public ingress. It exposes the same search function and `domain/calculate.py` to a local client. It does not become an anonymous second door.

Two principals, and neither is a subscription owner:

| Principal | Can | Cannot |
| --- | --- | --- |
| Container App identity | Read the blob, query the index, call the chat and embedding deployments | Write the blob or the index, administer the subscription |
| Ingest principal | Those reads, plus write `sheet.json`, the PDFs, and the index | Run as the web process, administer the subscription |

The laptop uses `.env` keys. The running container does not receive those keys.

Logs record only the span fields in `06-ai-architecture.md`. The access log, the exception log, and OpenTelemetry do not record prompt text, completion text, or the raw envelope. GenAI content capture stays off.

Global Standard can process a prompt outside the EU. The page tells visitors not to enter personal data. The envelope rejects any personal field before a model call.

Locally, `uvicorn` serves the same page and API against the cloud index, or against fakes in tests.

## Local and cloud

- Pure functions (parse, chunk, quote and decimal checks, comparison template, refusal reason codes) run in pytest with no cloud.
- Index and model calls sit behind interfaces. Unit tests use fakes. A marked integration test talks to Azure when credentials exist.
- CI on pull requests runs the fake path only.
- A manual workflow runs the live golden set against Azure and writes an MLflow run.

## What the models do

Azure OpenAI does two jobs:

- `text-embedding-3-small` turns each chunk into a vector. Azure AI Search stores the vector and runs hybrid search.
- `gpt-4.1-mini` extracts the sheet columns once per KID at ingest. On a follow-up it routes the question, grades chunks, and writes a lookup answer when the sheet does not already hold the fact. Comparison sentences and arithmetic stay in Python. See `06-ai-architecture.md`.

Python parses the PDFs, chunks them, checks citation ids and quote substrings, and does the arithmetic. Azure Document Intelligence is not in this project. The KID text has to stay exact, and the parser has to run in tests with no cloud account.

## Cost controls

Retail prices below are USD, Sweden Central, from the Azure Retail Prices API on 2026-11-24. A bill in Finland is in euros at Microsoft's rate. Order of magnitude is what matters.

| Piece | Price used for this estimate | Proof-month expectation |
| --- | --- | --- |
| Chat, GPT-4.1-mini global | $0.40 / 1M input tokens, $1.60 / 1M output tokens | About $0.004 per follow-up question, and one extract call per KID when the sheet is built. A 40-question live eval is about $0.20. Loading the sheet is not a model call. A month of demos and reruns stays around $1–5. |
| Embeddings, text-embedding-3-small global | $0.02 / 1M tokens | Indexing this corpus once is under $0.01. Re-indexing during development stays under $0.10. |
| Azure AI Search Free | $0 / hour, 50 MB, one service per subscription | $0. The service can be removed after long inactivity, so the ingest command must be repeatable. |
| Azure AI Search Basic | $0.101 / hour, about $74 / month while the service exists | Do not create this. It is the cost that would dominate. |
| Container Apps consumption | Per-second vCPU and memory. Monthly grant: 180,000 vCPU-seconds, 360,000 GiB-seconds, 2M requests. Scale to zero has no compute charge. | $0 if `minReplicas` is 0 and traffic stays in the grant. |
| Blob, Hot LRS | $0.0184 / GB-month | Cents. The PDFs are megabytes. |
| Key Vault operations | $0.03 / 10,000 operations | Cents. |
| Log Analytics ingestion | $0 for the first 5 GB / month, then $2.99 / GB | $0 if traces stay small. Set a daily cap. |

Proof budget: set an Azure budget alert at $20. Expected spend for a careful month is a few dollars, almost all of it tokens. Delete the resource group when the demo is idle for a long stretch.

Do not create: Search Basic or higher, semantic ranker on a paid plan, provisioned throughput, Azure Container Registry Basic, Document Intelligence, or a live eval inside pull-request CI. A forgotten Search Basic service costs about $74 for every month it exists, whether or not anyone asks a question.

## Out of v1

- Databricks, Spark, Delta Lake.
- Azure API Management.
- Entra ID login for end users.
- Multi-index tenancy.
- Automatic reranking beyond what Azure AI Search hybrid provides in the basic setup.
- A second host for the frontend, including Static Web Apps or a Node server in production.
