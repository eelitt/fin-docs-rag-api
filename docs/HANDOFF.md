# Handoff

Updated: 2026-11-27

This file briefs the next agent. It is not the coding rules.

Before any code change, read `Claude.md` and follow it. That file holds the coding instructions. Do not copy them here, and do not put session state in `Claude.md`.

`docs/` is the source of truth. If this file and `STATUS.md` disagree, `STATUS.md` wins. At the end of a session, update `STATUS.md` and the "Now" section here.

## Read first

1. This file.
2. `Claude.md`, before writing or editing code.
3. `STATUS.md` — phase, next action, blockers, measurements.
4. The current milestone in `04-milestones.md`.
5. `05-open-questions.md` only if the next action is blocked.

Then open the doc the task touches. Do not re-decide a choice marked **decided**. Record a reversal in `STATUS.md` before changing it.

## Now

Phase: `deployed`. M1 through M8 are done. M3, M4, M5, and M7 passed on fakes. M6 and M8 are deployed. The public URL is `https://ca-fin-docs-rag.thankfulflower-24c321f8.swedencentral.azurecontainerapps.io`. `GET /` returns the Vite page from image `ghcr.io/eelitt/fin-docs-rag-api:7f341cfd66171397422f027a372c231563989246`. That tag is a container image, not a commit on current `main`. `GET /health` returned status ok. `GET /sheet` returned 22 funds. `ongoing_charge`, `sri`, and `holding_period` are `stated` on every row. `uv run ingest sheet` wrote those cells from the local KIDs and did not call a model. Entry cost and exit cost are unchanged. The public page does not mark the passage, because it was not deployed again.

Next action: do not start M9. Do not deploy again unless the human asks. Known limits are parked in `05-open-questions.md` and are not the next task. The empty-cell `uv run eval-run` on 2026-11-26 was 9 of 29, with retrieval hit rate at 8 of 0.6 (3 of 5). The later run was 21 of 29: sheet 12 of 15, retrieve 6 of 10, refuse 3 of 4, and the same hit rate. Retrieval misses are `near-pharos-phoebus` and `near-eurooppa`. The README records both runs and one live trace. The manual GitHub workflow still needs the model endpoints as secrets.

## Done

- Corpus: 12 KIDs and one quarterly review. Manifest at `sources/manifest.json`. PDFs are gitignored under `data/pdfs/`. `scripts/download_sources.py` downloads them.
- Parser and chunker. Chunk id is `{doc_id}:{section}:{page}:{window}`. Sizes are in `STATUS.md`. Do not retune 1200/100 or 800/120.
- Ingest: `uv run ingest index` creates the private `documents` container if needed, uploads the PDFs, embeds, and pushes index `chunks`. `uv run ingest query "..."` runs hybrid search. `uv run ingest sheet` replaces the ongoing cost, the risk indicator, and the recommended holding period from the local KIDs and does not call a model.
- The known-charge query returns `FI0008804729:costs:3:0`, and that chunk contains `0,30 %`.
- Search document key is `chunk_key` (colons replaced with underscores). The `id` field keeps the colon form.
- A KID chunk stores every checksum-valid ISIN in that file. A report chunk stores only the ISINs in that chunk.
- `uv run pytest` scores the repo on fakes. The latest count is in `STATUS.md`. The skip is the live hybrid query. With Azure variables in the environment it runs too.
- M3: sheet extract, quote check, `GET /sheet`, `GET /compare`, and `POST /ask`. The five question types pass on fakes. `GET /sheet` does not call the model. The column key is `ongoing_charge`.
- M4: `eval/golden.json` (29 items, k = 8). `uv run pytest` scores it on fakes. `.github/workflows/tests.yml` downloads the PDFs, then runs pytest, on pull requests and on push. `.github/workflows/eval.yml` is manual and runs `uv run eval-run`. The PDFs stay gitignored.
- M5: one root span per accepted `/ask`, one child per model call. The log gets that object. Application Insights gets it only when `APPLICATIONINSIGHTS_CONNECTION_STRING` is set. A rejected envelope is not traced. A schema retry stores both attempts on the child. Bicep names `log-fin-docs-rag` and `appi-fin-docs-rag`, daily cap 0.1 GB. Those resources exist. The pasted live trace is M8.
- M6: `Dockerfile`, placeholder `GET /`, and keyless calls when the API keys are unset. `id-fin-docs-rag-web` is the app identity. `id-fin-docs-rag-ingest` can write and is not on the app. `.github/workflows/deploy.yml` pushes `ghcr.io/eelitt/fin-docs-rag-api:<sha>` and updates `ca-fin-docs-rag`. No Azure Container Registry. Teardown is `az group delete --name rg-fin-docs-rag --yes --no-wait`, also in the root README. Deployed on 2026-11-26. The image installs `uvicorn`. The GitHub OIDC subject includes the owner and repository ids.
- M7: `mcp_server.py` is a local stdio server. Tools are `retrieve` and `compare_sentence`. They call `steps/retrieve.py` and `domain/calculate.py`. The public app has no MCP route. `mcp` is a dev dependency, so the container image does not install it. The README shows one local client call.
- Root `README.md` tells a recruiter what the project is and carries the disclaimer. M8 added local run steps, deploy steps, the 2026-11-26 live eval numbers, a cost note, one live trace, and a short map of what the project shows.
- Bicep is in `infra/` and has been deployed to `rg-fin-docs-rag`. A later deploy updates the portal resources that already exist, including search authentication and the Foundry account. Azure CLI 2.93.0 is installed. A new terminal is needed before `az` is on `PATH`.

Image tags `7f341cfd66171397422f027a372c231563989246` and `4c0358ab339a74809b612e4eb66f90f6c6e389ba` are GHCR tags. They are not commits on current `main`. Do not check them out. `STATUS.md` records the public URL. Trust `STATUS.md` over an older note that says the app is not deployed.

## Do not

- Implement gitignored `idea_one.md`. The decisions are in `docs/`.
- Treat the known limits in `05-open-questions.md` as the next task. They are parked.
- Open M9 or later to fill out the repo. `07-code-architecture.md` is the full map. `frontend/` is the deployed M8 page. Do not deploy again unless the human asks.
- Create Azure AI Search Basic, a second search service, semantic ranker, provisioned throughput, Document Intelligence, Container Registry, or SFTP.
- Put secrets, connection strings, or keys in docs, chat, or git. They stay in `.env`.
- Name a bank or a fund company in docs, UI, README, or code. The sources manifest is the exception. Chunk text may contain whatever the PDF prints.
- Commit unless the human asks.

## Run

From the repo root, in PowerShell. `&&` is not available. `uv` is at `C:\Users\Eerik\.local\bin` and is not on `PATH` until you prepend it. Python is not on `PATH`.

This machine sets `REQUESTS_CA_BUNDLE` to a missing certificate file. Before `uv run`, set `REQUESTS_CA_BUNDLE` and `SSL_CERT_FILE` to `.venv\Lib\site-packages\certifi\cacert.pem`.

```
uv run pytest
uv run python scripts/download_sources.py
uv run ingest index
uv run ingest sheet
uv run ingest query "Hallinnolliset maksut ja muut hallinto- tai toimintakulut 0,30 %"
```

`ingest` loads `.env`. `pytest` does not. The integration test runs only when `AZURE_SEARCH_API_KEY` is already in the environment.

The chat deployment is `gpt-4.1-mini`, Global Standard. `gpt-4-1-mini` is not a live deployment. The endpoint and keys stay in `.env`. Resource names and the forbidden list are in `infra/` and `03-architecture.md`. The portal diary is the local gitignored file `docs/azure_setup.md`. Do not copy endpoints into a committed doc.
