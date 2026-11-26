# Handoff

Updated: 2026-11-26

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

Phase: `deployed`. M1, M2, M3, M4, and M5 passed. M3, M4, and M5 passed on fakes. M6 is deployed. M7 passed on fakes. M8 is deployed. The public URL is `https://ca-fin-docs-rag.thankfulflower-24c321f8.swedencentral.azurecontainerapps.io`. The page was added in `ghcr.io/eelitt/fin-docs-rag-api:7f341cfd66171397422f027a372c231563989246`. `GET /` returns the Vite page. `GET /health` returned status ok. `GET /sheet` returned 22 funds. The scripted `POST /ask` returned HTTP 200 and said the ongoing cost of `FI0008804729` was not extracted. `sheet.json` is in the blob. Every `ongoing_charge` cell is `not_extracted`.

Next action: do not start M9. Do not deploy again unless the human asks. A fresh sheet extract is what would fill the cost cells. A rerun uses the same one-figure check, so it can write the same empty cells. The ongoing-cost column key is `ongoing_charge`. `uv run eval-run` on 2026-11-26 was not ok: 9 of 29 items passed, and the retrieval hit rate at 8 was 0.6 (3 of 5). The README records that run and one live trace. The manual GitHub workflow still needs the model endpoints as secrets.

## Done

- Corpus: 12 KIDs and one quarterly review. Manifest at `sources/manifest.json`. PDFs are gitignored under `data/pdfs/`. `scripts/download_sources.py` downloads them.
- Parser and chunker. Chunk id is `{doc_id}:{section}:{page}:{window}`. Sizes are in `STATUS.md`. Do not retune 1200/100 or 800/120.
- Ingest: `uv run ingest index` creates the private `documents` container if needed, uploads the PDFs, embeds, and pushes index `chunks`. `uv run ingest query "..."` runs hybrid search.
- The known-charge query returns `FI0008804729:costs:3:0`, and that chunk contains `0,30 %`.
- Search document key is `chunk_key` (colons replaced with underscores). The `id` field keeps the colon form.
- A KID chunk stores every checksum-valid ISIN in that file. A report chunk stores only the ISINs in that chunk.
- `uv run pytest`: 64 passed, 1 skipped, without Azure variables in the environment. The skip is the live hybrid query. With those variables it runs too.
- M3: sheet extract, quote check, `GET /sheet`, `GET /compare`, and `POST /ask`. The five question types pass on fakes. `GET /sheet` does not call the model. The column key is `ongoing_charge`.
- M4: `eval/golden.json` (29 items, k = 8). `uv run pytest` scores it on fakes. `.github/workflows/tests.yml` runs that on pull requests. `.github/workflows/eval.yml` is manual and runs `uv run eval-run`. GitHub's last pytest run failed because the PDFs are gitignored and the workflow does not download them.
- M5: one root span per accepted `/ask`, one child per model call. The log gets that object. Application Insights gets it only when `APPLICATIONINSIGHTS_CONNECTION_STRING` is set. A rejected envelope is not traced. A schema retry stores both attempts on the child. Bicep names `log-fin-docs-rag` and `appi-fin-docs-rag`, daily cap 0.1 GB. Those resources exist. The pasted live trace is M8.
- M6: `Dockerfile`, placeholder `GET /`, and keyless calls when the API keys are unset. `id-fin-docs-rag-web` is the app identity. `id-fin-docs-rag-ingest` can write and is not on the app. `.github/workflows/deploy.yml` pushes `ghcr.io/eelitt/fin-docs-rag-api:<sha>` and updates `ca-fin-docs-rag`. No Azure Container Registry. Teardown is one `az group delete` in `azure_setup.md`. Deployed on 2026-11-26. The image installs `uvicorn`. The GitHub OIDC subject includes the owner and repository ids.
- M7: `mcp_server.py` is a local stdio server. Tools are `retrieve` and `compare_sentence`. They call `steps/retrieve.py` and `domain/calculate.py`. The public app has no MCP route. `mcp` is a dev dependency, so the container image does not install it. The README shows one local client call.
- Root `README.md` tells a recruiter what the project is and carries the disclaimer. M8 added local run steps, deploy steps, the 2026-11-26 live eval numbers, a cost note, one live trace, and a short map onto `01-gap-map.md`.
- Bicep is in `infra/` and has been deployed to `rg-fin-docs-rag`. A later deploy updates the portal resources that already exist, including search authentication and the Foundry account. Azure CLI 2.93.0 is installed. A new terminal is needed before `az` is on `PATH`.

`4c0358a` (`Fix the container start and the Bicep deploy.`) is the image the app was checked against. `STATUS.md` records the public URL. Trust `STATUS.md` over an older note that says the app is not deployed.

## Do not

- Implement `idea_one.md`. The decisions are in `docs/`.
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
uv run ingest query "Hallinnolliset maksut ja muut hallinto- tai toimintakulut 0,30 %"
```

`ingest` loads `.env`. `pytest` does not. The integration test runs only when `AZURE_SEARCH_API_KEY` is already in the environment.

Resource names, the OpenAI endpoint, and the deployment names are in the record table in `azure_setup.md`. The deployment type was not written down. Do not guess it.
