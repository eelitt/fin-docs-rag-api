# AI architecture

Status: **decided**
Updated: 2026-11-25

Detail behind the workflow in `03-architecture.md`. The system map stays there. This file is the model path: which call runs, what Python decides, and which libraries stay out.

## Shape

The sheet is built at ingest. A question is one Python function, `answer_question(envelope) -> Answer`. The envelope is defined in `02-product.md`. No chat history. No agent loop that picks its own next step. `caller` is for the trace. The model does not see it.

```
ingest, per KID
  → one extract call over that fund's chunks
  → verify each column
  → stated | not_stated | not_extracted
  → sheet.json in blob

question
  → router (one model call, JSON)
      advice, high confidence → advice_refused
      sheet column, or compare of two sheet rows → read sheet.json, Python writes the sentence
      anything else → retrieve → grade → answer or abstain
  → verify quotes and citation ids on a generated answer
  → trace
```

Building one KID's row costs one chat call. Loading the sheet or comparing two stored rows costs no model call. A follow-up that the sheet cannot answer costs one embedding plus three chat calls (router, grade, answer). A sheet-column question costs the router call only. A high-confidence advice question costs one chat call and does not touch search.

## What each part uses

| Step | Who does it | Why |
| --- | --- | --- |
| Read the PDF, pages, ISIN | Python (`pypdf` or `pymupdf`) | The figure on the page has to match the figure in the index. A model parser can silently change `1,20` to `1.25`. |
| Headings and chunks | Python | PRIIPs KIDs share a fixed outline. A section chunk is the unit a citation can point at. |
| Vectors | `text-embedding-3-small`, 1536 dimensions | One Azure embedding deployment. The model handles Finnish and English. This corpus does not justify a second embedding model. |
| Keyword + vector search | Azure AI Search hybrid query, our index | Charges, ISINs, and fund names need keyword match. Paraphrases need vectors. The free tier has no semantic ranker, so both signals stay on. |
| Route, grade, answer, sheet extract | `gpt-4.1-mini`, JSON schema | Same chat deployment for every call. The extract runs at ingest, once per KID. Structured output is the contract the tests assert. |
| Quote check, arithmetic, comparison sentence | Python | A citation counts only when the quote is a substring of the kept chunk. A difference is computed, then placed in a template. |
| Eval on pull requests | Deterministic checks on fakes | A judge model can score a fluent wrong answer as faithful. CI must be free of token spend. |

Client library: the official OpenAI Python SDK pointed at the Azure OpenAI endpoint, plus `azure-search-documents` for the index. Schemas are Pydantic models. Prompts are files under `prompts/`, each with a version id stored on the trace (`router_v1`, `grade_v1`, `answer_v1`, `extract_v1`).

## Index

One index, named `chunks`, created by the ingest command. Fields:

| Field | Role |
| --- | --- |
| `chunk_key` | Search document key. The chunk id with `:` replaced by `_`. A search key cannot contain `:`. |
| `id` | `{doc_id}:{section}:{page}:{window}`. `window` is `0` when the section is one chunk. This field is stored and returned. It is not the search key. Re-index must reproduce the same ids. |
| `content` | Searchable text. Analyzer `fi.microsoft`, so Finnish inflection still matches on the keyword side. English text in the corpus relies on the vector. |
| `content_vector` | 1536-d vector, cosine, HNSW. Not returned with the hit. |
| `doc_id`, `source_title`, `page`, `section` | Returned with the hit and shown in the citation. |
| `isin` | Filterable collection. A KID chunk stores every checksum-valid ISIN in that file. A report chunk stores only the ISINs in that chunk. Extracted with the ISIN regex, not by the model. |
| `language` | `fi` or `en`, from the manifest. Filterable. |

Do not create the index by hand in the portal.

## Chunking

KIDs follow the PRIIPs outline (purpose, product, risks and performance, inability to pay, costs, holding period, complaints, other information). Split on those headings in Finnish and in English. A section under about 1200 tokens is one chunk. A longer section splits on blank lines with about 100 tokens of overlap.

The longer report splits on its own headings, then on about 800-token windows with about 120 tokens of overlap. Every chunk keeps its page number.

M1 confirmed the heading list against two real files. `STATUS.md` holds the sizes and the two printed cost-row labels. The ongoing-cost column key is `ongoing_charge`, chosen 2026-11-25, with no alias. Until a live eval shows a miss, do not retune the sizes.

A PDF with no text layer fails ingest for that file. There is no OCR in v1. A text layer is not enough when the costs sit in a table. M1 keeps a known cost figure and a known risk indicator each inside one chunk. Do not add Document Intelligence to get past that test.

The quote shown in the product is a short snippet. Ingest does not publish the original PDF.

The chunk text contains whatever the KID itself prints, including the fund and the manufacturer. That is source text. The app chrome, the README, and these docs still name no bank and no fund company.

## Router

One chat call. Input is the raw question. Output:

- `intent`: `lookup`, `compare`, or `advice`
- `advice_confidence`: `high` or `low`
- `funds`: names or ISINs mentioned
- `comparison_field`: `ongoing_charge`, `sri`, `holding_period`, `entry_cost`, or `exit_cost`, or empty
- `search_query`: a short query for hybrid search

`advice` plus `high` returns `advice_refused` and stops. `advice` plus `low` still retrieves, and the answer step may still refuse. A question about a sheet column is served from `sheet.json` when the named fund resolves to a row. The prompt examples must say that a holding period or a risk indicator is that kind of lookup, not advice. A column question whose fund does not resolve falls through to search.

When `instrument_ids` is non-empty, those ISINs are the only hard search filter. Python does not also scan the question. When the list is empty, Python scans the question for an ISIN, and that regex is the hard filter. A fund name from the model is added to `search_query` and is not a search filter, because a wrong name would zero the hits. After grading, Python prefers kept chunks that contain that name, and keeps the unfiltered set only when the preference is empty. "Which is cheaper?" is `compare`, not `advice`.

## Retrieve and grade

Hybrid search, top 8, no semantic ranker. The vector is the embedding of `search_query`, not of the raw question, so the router can drop advice wording before search.

One grade call sees all 8 chunks and returns `relevant: true | false` per chunk id. Python drops the rest and keeps at most 4. Zero kept returns `not_in_corpus` and lists the document titles that were searched.

Grading exists because the free tier will not rerank. The usual miss is the right section from the wrong fund.

## Answer path

One chat call. The model sees only the kept chunks. Output:

- `can_answer`
- `answer`
- `citations`: chunk id plus a quote
- `reason`: empty, `not_in_corpus`, or `ungrounded`

Python then does all of the following before anything is returned:

- Every cited id is in the kept set.
- Every quote is a substring of that chunk after whitespace is collapsed and case is folded.
- `can_answer: true` with a failed quote becomes `ungrounded`, and the draft text is discarded.
- `can_answer: false` becomes `not_in_corpus`.

The HTTP body is the `POST /ask` object in `02-product.md`. Its `chunk_ids` are the kept set offered to the answer model, and its `request_id` is the one assigned after the error checks. The trace has one root span for the request and one child span for each model call. The root stores `caller`, the pre-grade ids under `chunk_ids`, total tokens, total cost, and the reason code. It stores `instrument_ids` only when `caller` is `demo`. Any other caller's instrument ids stay out of the trace. Each child stores its name (`embed`, `router`, `grade`, `answer`, or `extract`), prompt id, deployment name, model version, latency, and token counts. A schema retry stores both attempts on that child. The trace does not store the raw question, the prompt, the completion, the caller secret, or any field the envelope rejected. The access log and the exporter are held to the same fields. A reviewer can see what grading dropped without keeping what the visitor typed. On HTTP 503 the same trace is written to the log and is not put on the response.

## Sheet extract

The model does not subtract, and it does not write the result sentence. Extraction runs at ingest, not on `GET /sheet`.

One extract call per KID returns one item per column: field, `present` or `absent`, chunk id, quote, and a numeric value when the column is a number. The product sentence has a quote and no number. Python checks a present quote the same way as an answer citation, including the 400-character cap. For a number, it parses the figure printed in the quote, including a Finnish comma decimal (`1,20`), and rejects the item when that number disagrees with the model's value.

A checked present value is stored as `stated`. `absent` is stored as `not_stated`. A rejected value is stored as `not_extracted` with no number and no quote. A numeric column is `stated` only when one printed figure matches the stored number. The stored file is the `GET /sheet` document in `02-product.md`, written to `sheet.json` in the private blob container. The new `sheet.json` is written only when that ingest run finishes its checks. A failed run leaves the previous file in place.

`GET /compare` reads the two ongoing-cost cells for `isin_a` and `isin_b`. When both are `stated` numbers, Python computes the difference and fills an English template: the two figures, the holding period each figure assumes, their citations, and the difference in percentage points. If the holding periods differ, both periods appear and the sentence does not rank the funds. The template does not say which fund to choose. If either cell is `not_stated` or `not_extracted`, or either ISIN is not a row, the sentence says so and does not invent a difference. The response body is in `02-product.md`. A follow-up comparison uses the same template on the router's `comparison_field`, in percentage points, years, or risk-indicator steps. The page shows the two product sentences from `GET /sheet`.

The same pure function is what the later MCP server exposes. There is no general calculator the model can call with its own expression. A follow-up comparison of two sheet rows uses this function and does not call extract again.

## Abstain and refuse

| Code | When |
| --- | --- |
| `advice_refused` | Router is sure the user wants a recommendation, or a later step still sees a recommendation request. |
| `not_in_corpus` | Search or grading found nothing usable, or the kept chunks do not contain the fact. |
| `ungrounded` | The model claimed an answer whose quote or chunk id failed the Python check. |

Document text is data. The system prompt says so, so a line inside a PDF cannot change the refusal rules.

## Failure modes

One list. Other docs point here instead of restating it.

| What happened | Result |
| --- | --- |
| High-confidence advice | `advice_refused`. No search. |
| Grading keeps nothing, or the kept chunks lack the fact | `not_in_corpus`. |
| Quote or figure check fails | `ungrounded`. The draft is dropped. |
| A `GET /compare` query is missing a parameter, has a non-ISIN, or repeats one ISIN | HTTP 400 `{ "error": "invalid_instrument_id" }`. No model call and no trace. |
| An `/ask` body fails a check in the error table in `02-product.md` | That row's status and `error` code. `{ "error": "<code>" }` only. The model is not called. The body is not stored and is not traced. The call does not count toward the rate limit. No `request_id` is assigned. |
| The 21st accepted `/ask` in 10 minutes in this process | HTTP 429 `{ "error": "rate_limited" }`. The model is not called. Nothing is traced. The counter resets when the process stops. |
| `caller` is not `demo` before a second caller is registered, or a later caller has a missing or wrong secret | HTTP 401 `{ "error": "unauthorized" }`. The model is not called. Nothing is traced. v1 has no secret header. |
| Search is down, or the model times out | HTTP 503 `{ "error": "unavailable", "request_id": "…" }`. No answer text. No second try. The trace is logged and is not returned. |
| Chat JSON still fails schema validation after one retry | HTTP 503, same body as a timeout. No answer text. The log span records both attempts. The trace is not returned. |
| A KID has no text layer, or the known cost or risk indicator is split across chunks | That file fails ingest. M1 stops before the index exists. |
| Two cost figures assume different holding periods | The sentence states both periods and does not rank the funds. |
| A sheet cell fails its check | `not_extracted`. The claimed value is not stored. |
| Ingest fails after a good `sheet.json` already exists | The previous file stays. The new file is written only when that run finishes its checks. |
| The Free search service is removed while idle | Run ingest again. It must rebuild the index and the sheet. |

## Eval

The golden file is the judge. Each item has a path label and an expected outcome.

| Path label | The run must |
| --- | --- |
| `sheet` | Answer from `sheet.json`. The trace has a router span and no embed, grade, or answer span. |
| `retrieve` | Search, then answer or abstain from the kept chunks. |
| `refuse` | Return `advice_refused` and not search. |

The outcome is one of: a source id that must be cited, a number that must match, or a reason code. CI fails when the path label and the outcome disagree with the run.

Pull-request CI runs that file against fakes. It fails if an `advice_refused` item returns an answer body. The file includes near-misses: similar fund names, a fact the corpus does not state, and a comparison whose holding periods differ. The live Azure run is manual and writes one MLflow run with the prompt versions and the eval-set version.

Do not add a model-as-judge score to that gate.

## Code layout

Modules, ownership, and the dependency rule are in `07-code-architecture.md`. That file is the map when adding a file. The responsibilities in this document do not move: verify and arithmetic stay in domain code, and `pipeline.py` stays the only orchestrator.

## Rejected for v1

Recorded in `05-open-questions.md` so they are not reopened here.

- LangChain, LangGraph, LlamaIndex, and Semantic Kernel. The path is one function. A follow-up the sheet cannot answer is one embedding and three chat calls. A sheet-column question is the router plus `sheet.json`. A sure advice refusal is one chat call. A graph runtime would hide the loop this project exists to show.
- Microsoft Foundry Agent Service as the orchestrator. The hosted loop would own tools and traces. This repo has to own the citation check and the eval gate.
- Foundry IQ agentic retrieval. It spends extra model tokens inside the search service. Direct hybrid search is testable on the free tier.
- RAGAS, or any second model scoring faithfulness. The quote check is stricter and runs in CI for free.
- Multi-turn chat and query-rewrite loops. A follow-up question is a new question. History makes the golden file ambiguous.
- A second chat model for grading. One deployment is enough at this corpus size.
- OCR, Document Intelligence, and a model that reads the PDF straight through.
