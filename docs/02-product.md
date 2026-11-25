# Product

Status: **decided**
Updated: 2026-11-25

## One sentence

A research aid turns a fixed shelf of public fund KIDs into a cited fact sheet, and answers a follow-up from those documents or refuses.

## User

A person comparing a shortlist of public funds, including an advisor preparing for a client conversation. They would otherwise open each KID and copy the same fields by hand. They do not receive a personal portfolio recommendation, and the sheet does not say which fund to buy.

## Corpus

Confirmed 2026-11-24.

- 8–15 public PRIIPs KIDs from Finnish fund companies, more than one company.
- One longer public report section so a follow-up question is not only short-form.
- A `sources` manifest in the repo: title, publisher, URL, retrieved date, license note.
- Prefer documents the publisher makes public for investors. Do not commit a PDF if the license is unclear. Store the manifest and a download script, and gitignore the binaries.
- The repo, the UI, and these docs name no bank and no fund company. The sources manifest lists the public documents that were indexed. Pick them from more than one company.

## Fact sheet

The sheet is the product. It is built when the KIDs are indexed, one row per fund. Loading it does not call the model. `POST /ask` is the only live model path.

Columns:

| Column | What it holds |
| --- | --- |
| Product | One sentence from the KID on what the product is. |
| Risk indicator | The printed risk indicator. |
| Recommended holding period | The printed period. |
| Ongoing cost | The main ongoing cost row, with the horizon that table assumes. |
| Entry cost | The printed entry cost, when the KID has one. |
| Exit cost | The printed exit cost, when the KID has one. |

The two printed ongoing-cost rows are in `STATUS.md`. They do not share one wording. The column key is `ongoing_charge`, chosen 2026-11-25. There is no alias.

Each cell is one of three states:

- `stated` — the value, plus a citation (source id, title, page or section, quote). The quote passed the same check as a live answer: it is a substring of the kept chunk, it is at most 400 characters after whitespace collapse, and a Finnish figure in the quote matches the stored number. A longer quote fails the check.
- `not_stated` — the KID does not print that field.
- `not_extracted` — a value was claimed and the quote or figure check failed. The cell is empty. The failed value is not stored.

A comparison of two funds is computed from those stored cells. It does not call the model. For two stated numbers, the sentence states both figures, both holding periods, and the difference. It does not say which fund to buy. If the holding periods differ, the sentence says both periods and does not rank the funds. If either cell is `not_stated` or `not_extracted`, the sentence says so and does not invent a difference. The page shows the two product sentences side by side from `GET /sheet`, with no arithmetic. `GET /compare` compares the ongoing-cost column only. `POST /ask` compares the column the router names.

## Questions the system must handle

`POST /ask` is for a question the columns do not cover. The five checks stay:

1. Fact in a KID: a cost row, the risk indicator, or the recommended holding period. The answer cites document, section, and page when known. The sheet already holds these when extraction succeeded. A follow-up still has to cite them.
2. Comparison across two funds on a field that both KIDs state, including the holding period each figure assumes. The numbers come from the stored cells. The model does not write the difference. "Which is cheaper?" is this comparison, not `advice_refused`.
3. Absence: a question the corpus does not answer. The system abstains and says what it looked at.
4. Advice bait: "Should I buy this fund?" The system refuses and points back to the sheet. It does not produce a recommendation.
5. Long document: a question whose answer is a specific passage in the longer report, so hybrid search has to find it. The longer report is not a row on the sheet.

## Responses

Answer prose is English, including the comparison sentence, the page, and the disclaimer. A question may be Finnish or English. A quote is copied from the document and is not translated. The product cell on the sheet is the printed sentence, in whatever language the KID uses. A holding period stays the printed phrase inside the English sentence.

The model never writes a holding, a price, or a personal allocation. The sheet never writes those either.

A citation is `source_id`, `title`, `page` when the chunk has one, `section` when the chunk has one, and `quote`. The quote is the printed text that passed the check.

### `GET /sheet`

Returns the stored `sheet.json` document. No model call and no trace.

```json
{
  "funds": [
    {
      "isin": "FI0000000000",
      "product": {
        "state": "stated",
        "quote": "…",
        "citation": { "source_id": "…", "title": "…", "page": 2, "section": "…", "quote": "…" }
      },
      "sri": {
        "state": "stated",
        "number": 4,
        "quote": "4",
        "citation": { "source_id": "…", "title": "…", "page": 3, "section": "…", "quote": "4" }
      },
      "holding_period": { "state": "stated", "number": 5, "quote": "5 years", "citation": { "source_id": "…", "title": "…", "section": "…", "quote": "5 years" } },
      "ongoing_charge": { "state": "stated", "number": 1.2, "quote": "1,20 %", "citation": { "source_id": "…", "title": "…", "page": 4, "section": "…", "quote": "1,20 %" } },
      "entry_cost": { "state": "not_stated" },
      "exit_cost": { "state": "not_extracted" }
    }
  ]
}
```

`isin` is the row key. The cell keys are `product`, `sri`, `holding_period`, `ongoing_charge`, `entry_cost`, and `exit_cost`.

`stated` has `quote` and `citation`. The citation `quote` is the same string as the cell `quote`. The numeric columns are `sri`, `holding_period`, `ongoing_charge`, `entry_cost`, and `exit_cost`. A stated numeric cell also has `number`, the parsed figure with a dot decimal. `product` has no `number`. A numeric column is `stated` only when one printed figure matches `number`. The model saying the field is absent stores `not_stated`. A claimed value that fails the quote or figure check stores `not_extracted`. Those two states are `{ "state": "…" }` and nothing else.

### `GET /compare`

Demo route. Query parameters are `isin_a` and `isin_b`, two ISINs from the public shelf. The access log may store them. Another app does not call this route. That app loads `GET /sheet` and compares on its own server, so a user's pair never arrives here.

The compared column is the ongoing-cost column. No model call and no trace.

```json
{
  "isin_a": "FI0000000000",
  "isin_b": "FI0000000001",
  "field": "ongoing_charge",
  "sentence": "…",
  "cell_a": {},
  "cell_b": {}
}
```

`field` is the ongoing-cost column key. `cell_a` and `cell_b` are sheet cells. The empty objects in the example stand in for those cells. A difference is filled only when both cells are `stated` and both have `number`. Otherwise the sentence names the cell that is `not_stated` or `not_extracted` and does not invent a difference.

A missing parameter, a value that is not an ISIN, or the same ISIN twice is HTTP 400 with `{ "error": "invalid_instrument_id" }`. An ISIN that is not a row is HTTP 200. That cell is `null`, and the sentence says the fund is not on the sheet.

### `POST /ask`

Every HTTP 200 uses one object. A refusal or abstention is HTTP 200, and `answer` is `null`.

```json
{
  "request_id": "…",
  "reason": null,
  "answer": "…",
  "citations": [],
  "chunk_ids": [],
  "documents_searched": [],
  "trace": {}
}
```

`reason` is `null` for a lookup or comparison that produced prose. It is `advice_refused`, `not_in_corpus`, or `ungrounded` otherwise. On those three, `answer` is `null` and `citations` is empty. The empty `trace` in the example stands in for the span object below. A citation in `citations` has the same fields as a sheet citation.

`chunk_ids` is the kept set offered to the answer model. It is empty when the answer comes from the sheet, and empty for `advice_refused`. For `not_in_corpus` it is the kept set, which is empty when grading kept nothing. `documents_searched` lists the document titles that were searched, and only for `not_in_corpus`. It is empty on every other path.

A sheet hit cites the stored cell. A comparison cites the two stored cells. Both leave `chunk_ids` and `documents_searched` empty.

`trace` is the root span and its child spans. The root holds `request_id`, `caller`, latency in milliseconds, total tokens, cost in USD from the prices in `03-architecture.md`, the pre-grade chunk ids under `chunk_ids`, and `reason`. It holds `instrument_ids` only for `caller: demo`. Each child holds `name` (`embed`, `router`, `grade`, `answer`, or `extract`), `prompt_id`, deployment name, model version, latency, and token counts. The question is not in the trace. A sheet hit has only the router child.

### Errors

A failed `/ask` check returns a different object, so a client cannot treat it as an abstention. HTTP 400, 401, and 429 are `{ "error": "<code>" }` and nothing else. HTTP 503 is `{ "error": "unavailable", "request_id": "…" }`. The 503 trace stays in the log. It is not returned.

Checks run in this order and stop at the first failure. A failure here is not traced, the body is not stored, and the call does not count toward the rate limit. The server assigns `request_id` only after every check has passed.

| Check | `error` | Status |
| --- | --- | --- |
| The body is not a JSON object, a key is outside the four envelope fields, or a present field has another JSON type | `unknown_field` | 400 |
| `question` is missing, or empty after the surrounding whitespace is removed | `empty_question` | 400 |
| `question` is longer than 1,000 characters after that whitespace is removed | `question_too_long` | 400 |
| `request_id` is present and is not a UUID | `invalid_request_id` | 400 |
| `instrument_ids` is present and is not a list of at most 20 ISINs, or it contains a duplicate | `invalid_instrument_id` | 400 |
| `caller` is present and is not `demo` | `unauthorized` | 401 |
| This process has already accepted 20 `/ask` requests in the last 10 minutes | `rate_limited` | 429 |

Missing `caller` becomes `demo`. Missing `instrument_ids` becomes `[]`. Until a second caller is registered there is no secret header and no Key Vault lookup. Any other `caller` is 401.

Search down, a model timeout, and a chat JSON schema that still fails after one retry are `unavailable` at HTTP 503. No answer prose. Search down and a timeout are not tried again. A schema failure records both attempts on the log span.

`POST /ask` allows 20 accepted requests per 10 minutes in the container process. The next accepted request is HTTP 429, the model is not called, and nothing is traced. The counter resets when the app scales to zero and is not shared across replicas. It is not the spend cap. The tokens-per-minute quota, the budget alert, and taking the app down are.

## Request envelope

Every `POST /ask` body is an envelope. The slot is there so a later app can call the same route. v1 does not accept personal data through it.

| Field | v1 rule |
| --- | --- |
| `request_id` | Optional UUID string. The server assigns one only after the error checks pass, returns it, and writes it on the trace. |
| `caller` | Optional string. Missing becomes `demo`. `demo` is the same-origin page. Any other value is 401 until a second app is registered, and then needs the server secret from `03-architecture.md`. |
| `instrument_ids` | Optional list of ISINs, at most 20, with no duplicates. Missing becomes an empty list. When the list is present, those ISINs are the subject of the call. The question text is not scanned for a second set of ids. |
| `question` | Required string. Empty after the surrounding whitespace is removed, or longer than 1,000 characters after that, is HTTP 400 and does not call the model. |

Any other field is HTTP 400 `unknown_field` and does not call the model. That includes a name, an email, an amount, a cost basis, a holding, an account id, and a user id. The server does not store the rejected body. The check order is in the errors section above.

The trace records `request_id` and `caller`. For `caller: demo` it also records `instrument_ids`. For any other caller it does not. Those ids stay in the calling app's log. The trace does not record the question. The model sees the question and, when the list is non-empty, the instrument ids. It does not see `caller`.

A later caller may send `caller` set to another app the human owns, and ISINs from that app's screen. The call comes from that app's server, with a Key Vault secret in a header. The secret is not an envelope field. That app's browser does not call `/ask` and does not see the secret. Until that registration, the only caller is `demo`. Putting a holding or an amount in the envelope is a new decision: a named field, a retention rule, and a model deployment that stays in the EU. Global Standard does not qualify. The other app keeps its ledger. This API does not read it.

## Demo surface

The product is an HTTP API. The demo is one page on the same service, so a reviewer opens one URL.

The page opens on the fact sheet: one row per fund, each cell a value with its short citation, or `not_stated`, or `not_extracted`. Choosing two funds shows the comparison sentence. The question box is secondary. Its examples are a passage in the longer report, a fact the corpus does not state, and "should I buy this?". An `/ask` response shows the answer, the citations, the refusal state, and a trace panel (chunks, model, tokens, estimated cost, latency). The sheet has no live trace, because that request did not call the model.

The disclaimer says this is a research aid over public documents, not investment advice, and not a product of any bank or fund company. It also says not to type personal holdings, amounts, or other personal data.

Citations are short quotes. The page has no download of the original PDF. The blob container stays private.

No accounts and no separate frontend app. The corpus is public. The demo sends `caller: demo`. A visitor's question is not stored in the trace.

## Interview story

Portfolio-tracker shows agents that respect a ledger. This repo shows a document system a person can use on a public fund shelf: a cited fact sheet built at index time, a follow-up that cites or refuses, eval numbers in CI, and a deployable Azure service. Same domain, different gap.
