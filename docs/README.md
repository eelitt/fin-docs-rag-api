# Plan index

This folder is the source of truth. Code comes later. A new session starts here and must not re-decide things already marked decided.

Two goals. Show the production AI work missing from portfolio-tracker, for later wealth-management AI engineer roles. Run that system on Azure for real, so the Azure experience is the work, not a write-up. An example role of this type closes on 2026-12-01. That date does not set the build order. The order is `04-milestones.md`.

## Read order for a new session

1. `STATUS.md` — phase, next action, blockers.
2. `00-context.md` — why the project exists.
3. The current milestone in `04-milestones.md`. While phase is `planning`, that milestone is M1. M1 needs no Azure. M2 waits until `azure_setup.md` is done.
4. `05-open-questions.md` only if the next action is blocked. It has no open blockers.

Skip the rest unless the task touches it.

## Files

| File | Role |
| --- | --- |
| `STATUS.md` | Living handoff. Update it at the end of every session. Holds the M1 measurements and the interview-ready bar. |
| `00-context.md` | Portfolio gap, the two goals, and what a hiring reader still cannot see. |
| `01-gap-map.md` | Job signal → portfolio evidence → what this repo shows, and the non-goals. |
| `02-product.md` | User, corpus, fact sheet, follow-up questions, response bodies, demo. |
| `03-architecture.md` | Stack, request path, deploy shape, cost, forbidden resources. Decided for v1. |
| `04-milestones.md` | Build order, M1 through M9. One milestone at a time. |
| `05-open-questions.md` | Closed choices and parked items. Nothing in it blocks M1. |
| `06-ai-architecture.md` | Model calls, index, chunking, quote check, eval, libraries left out. |
| `07-code-architecture.md` | Python modules, one job each, and the dependency rule. |
| `azure_setup.md` | Portal setup before M2, the record table, and what to leave uncreated. No secrets in that file. |

`idea_one.md` at the repo root is the original note. Do not implement it. The living decisions are the files in this folder.

## Rules for agents

- Treat a decision marked **decided** as fixed. Record a reversal in `STATUS.md` with the reason before changing it.
- Do not add services, agents, or datasets to look more complete. Scope is the gap map.
- Do not start implementation while `STATUS.md` says phase `planning` unless the human asks to build.
- At the end of a session, update `STATUS.md`: phase, last session, next action, blockers. Leave the other docs alone if nothing was decided.
- Public financial documents only. No customer data, no scraped paywalled research, and no claim of affiliation with a bank or fund company. Name none of them in the docs, the UI, or the repo.
- Azure is part of the running system. A migration essay is not a deliverable. Create only the resources in `azure_setup.md`. Do not create Azure AI Search Basic. A budget alert does not stop spend.
- The first code commit includes a `.gitignore` for `.env`, downloaded PDFs, and MLflow runs. Do not commit those.
