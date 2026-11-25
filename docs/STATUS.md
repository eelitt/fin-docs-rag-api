# Status

Updated: 2026-11-25

## Phase

`planning`

No application code yet. Corpus and the cost cap are decided. Start M1 when the human asks to build.

## Decision

Build a Python RAG service on Azure over a small corpus of public fund documents. The product is a cited fact sheet for that shelf, built when the documents are indexed, plus a follow-up question that cites or refuses. `POST /ask` takes an envelope: `request_id`, `caller`, `instrument_ids`, and `question`. v1 accepts only `caller: demo` and rejects any personal field before a model call. The response bodies and the `/ask` error checks are in `02-product.md`. The trace stores `instrument_ids` for the demo only. A later caller's ISIN list stays in that app's log. The trace does not store the question. The demo is a Vite React app served as static files by the same Container App. Evaluation and a trace of cost and retrieval stay in scope. It is a research aid, not a consumer robo-advisor.

`idea_one.md` is accepted on the domain and the lifecycle (retrieve, judge, answer, evaluate, observe). It is not accepted on Azure: the system runs on Azure. Writing "how this would move to Azure" does not close the gap.

## Last session

2026-11-25. Wrote the six HTTP response rules into `02-product.md`, and pointed the architecture, milestones, and failure table at them. `ongoing_charge` stays a placeholder until M1 records the printed cost-row label here. That key is then renamed in one edit, with no alias, before response models are written.

## Measured during M1

Leave these blank until two real files have been parsed.

| Item | Value |
| --- | --- |
| Heading list | |
| Chunk sizes | |
| Printed cost-row label | |
| Known cost figure used in the parser test | |
| Known risk indicator used in the parser test | |

## Next action

Human: follow `docs/azure_setup.md`, then fill in its record table. Say when to start M1. M1 does not need Azure. M2 needs the setup finished.

## Blockers

None for M1. M2 needs an Azure subscription. Do not create Azure AI Search Basic.

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
