# Plan index

This folder is the source of truth. A new session starts here and must not re-decide things already marked decided.

Two goals. Show the production AI work missing from portfolio-tracker, for later wealth-management AI engineer roles. Run that system on Azure for real, so the Azure experience is the work, not a write-up. An example role of this type closes on 2026-12-01. That date does not set the build order. The order is `04-milestones.md`.

## Read order for a new session

1. `HANDOFF.md` — briefing for a new agent. Before any code change, read `Claude.md`.
2. `STATUS.md` — phase, next action, blockers. If it disagrees with `HANDOFF.md`, this file wins.
3. `00-context.md` — why the project exists.
4. The current milestone in `04-milestones.md`. `STATUS.md` says which one is next.
5. `05-open-questions.md` only if the next action is blocked.

Skip the rest unless the task touches it.

## Files

| File | Role |
| --- | --- |
| `HANDOFF.md` | Briefing for the next agent. Update its "Now" section with `STATUS.md`. |
| `STATUS.md` | Living handoff. Update it at the end of every session. Holds the measurements and the interview-ready bar. |
| `00-context.md` | Portfolio gap, the two goals, and what a hiring reader still cannot see. |
| `01-gap-map.md` | Job signal → portfolio evidence → what this repo shows, and the non-goals. |
| `02-product.md` | User, corpus, fact sheet, follow-up questions, response bodies, demo. |
| `03-architecture.md` | Stack, request path, deploy shape, cost, forbidden resources. Decided for v1. |
| `04-milestones.md` | Build order, M1 through M9. One milestone at a time. |
| `05-open-questions.md` | Closed choices and parked items. The remaining column-key choice is in `STATUS.md`. |
| `06-ai-architecture.md` | Model calls, index, chunking, quote check, eval, libraries left out. |
| `07-code-architecture.md` | Python modules, one job each, and the dependency rule. |
| `azure_setup.md` | Portal setup record. Done before M2. No secrets in that file. |

`idea_one.md` at the repo root is the original note. Do not implement it. The living decisions are the files in this folder.

## Rules for agents

- Treat a decision marked **decided** as fixed. Record a reversal in `STATUS.md` with the reason before changing it.
- Do not add services, agents, or datasets to look more complete. Scope is the gap map.
- Do not start implementation while `STATUS.md` says phase `planning` unless the human asks to build.
- At the end of a session, update `STATUS.md`: phase, last session, next action, blockers. Leave the other docs alone if nothing was decided.
- Public financial documents only. No customer data, no scraped paywalled research, and no claim of affiliation with a bank or fund company. Name none of them in the docs, the UI, or the repo.
- Azure is part of the running system. A migration essay is not a deliverable. Create only the resources in `azure_setup.md`. Do not create Azure AI Search Basic. A budget alert does not stop spend.
- The first code commit includes a `.gitignore` for `.env`, downloaded PDFs, and MLflow runs. Do not commit those.
