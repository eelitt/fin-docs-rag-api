# fin-docs-rag

A research aid over a fixed shelf of public fund documents. It builds a cited fact sheet from those documents, and it answers a follow-up with a citation or an abstention.

The shelf is twelve public PRIIPs key information documents for Finnish funds, from more than one company, plus one longer quarterly review. Titles, publishers, and source URLs are in `sources/manifest.json`. The PDFs stay out of git.

The sheet is the product. Indexing reads one row per fund: what the product is, the risk indicator, the recommended holding period, and the entry, exit, and ongoing costs. Opening the sheet does not call a model. A comparison of two funds is filled in Python from those stored cells. The sentence states both figures, both holding periods, and the difference. It does not rank the funds.

`POST /ask` is the only live model path. A question about a sheet column is read back from the stored row. A question outside those columns is embedded, retrieved with hybrid keyword and vector search, graded, and returned only when every quote is a substring of a chunk retrieved on that turn and every figure matches the number printed in the quote. A high-confidence request for a recommendation stops before search. A question the documents do not support comes back as an abstention, with the titles that were searched.

## What is in the repo

The service is Python 3.12 and FastAPI. It parses the PDFs, chunks them on the KID section headings, and can upload the files, embed them, and query an Azure AI Search index. Chat and extraction use Azure OpenAI. Embeddings are a separate deployment. Original files go to a private blob container. The sheet file is written there when an ingest run finishes.

`eval/golden.json` holds 29 questions. Each one has a path (`sheet`, `retrieve`, or `refuse`) and an expected outcome: a number, a source id, or a reason code. The set includes two funds with similar names, a fact the corpus does not state, and a comparison whose holding periods differ. Pull-request CI runs the suite on fakes. A refusal that returns an answer body fails the check, and so does a run that takes a path other than its label. Retrieval hit rate is measured at the search depth of 8.

`uv run pytest` is the offline suite. One hybrid-search test runs only when Azure credentials are already in the environment.

Resource templates are in `infra/`. The demo page is the Vite app in `frontend/`. The container image builds it, and the same process serves it at `GET /`. The running app is `https://ca-fin-docs-rag.thankfulflower-24c321f8.swedencentral.azurecontainerapps.io`. That URL still serves the previous image until the next deploy.

The public site does not serve MCP. A local process exposes `retrieve` and `compare_sentence`, the same functions the API uses. `compare_sentence` fills the comparison template from the stored sheet. It does not take an expression. One client call:

```python
import asyncio

from mcp import Client
from mcp.client.stdio import StdioServerParameters

async def main():
    server = StdioServerParameters(
        command="uv",
        args=["run", "python", "-m", "fin_docs_rag.mcp_server"],
    )
    async with Client(server) as client:
        result = await client.call_tool(
            "compare_sentence",
            {
                "isin_a": "FI0008804729",
                "isin_b": "FI0008804687",
                "field": "ongoing_charge",
            },
        )
        print(result.structured_content)

asyncio.run(main())
```

## Run locally

Install [uv](https://docs.astral.sh/uv/) and Node.js. From the repo root, put the Azure settings in a `.env` file that is not committed. The names are `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_CHAT_DEPLOYMENT` (`gpt-4.1-mini`), `AZURE_OPENAI_EMBEDDING_DEPLOYMENT` (`text-embedding-3-small`), `AZURE_SEARCH_ENDPOINT`, `AZURE_STORAGE_ACCOUNT`, and `AZURE_STORAGE_CONTAINER` (`documents`). `AZURE_OPENAI_API_KEY`, `AZURE_SEARCH_API_KEY`, and `AZURE_STORAGE_KEY` are optional when the Azure CLI login can call those services. Do not commit the file.

The app reads the sheet and the index that are already in that account. `uv run python scripts/download_sources.py` downloads the PDFs, which stay out of git. `uv run ingest index` parses them, embeds them, and writes the sheet again.

Build the page, then start the API. Open `http://127.0.0.1:8000`.

```
npm ci --prefix frontend
npm run build --prefix frontend
uv run uvicorn fin_docs_rag.http.serve:app --host 127.0.0.1 --port 8000
```

`GET /` is the fact sheet, the two-fund comparison, and the follow-up box. The page sends `caller: demo`. It does not offer the original PDF.

## Deploy

A push to `main` runs `.github/workflows/deploy.yml`. The workflow builds `ghcr.io/eelitt/fin-docs-rag-api:<sha>` and updates the container app `ca-fin-docs-rag` in resource group `rg-fin-docs-rag`. The workflow uses GitHub secrets `AZURE_CLIENT_ID`, `AZURE_TENANT_ID`, and `AZURE_SUBSCRIPTION_ID`. There is no Azure Container Registry and no second host for the page.

One command removes the group, including the models, the search service, the storage account, and the corpus:

```
az group delete --name rg-fin-docs-rag --yes --no-wait
```

## Evaluation

`eval/golden.json` version `1` has 29 items, scored at k = 8. Pull-request CI runs that file on fakes. On fakes the retrieval hit rate at 8 is 1, a refusal with an answer body fails, and a run that takes a path other than its label fails.

`uv run eval-run` scores the same file against Azure and writes one MLflow run under `mlruns/`, experiment `fin-docs-rag`. The live run on 2026-11-26 was not ok: 9 of 29 items passed, and the retrieval hit rate at 8 was 0.6 (3 of 5 items that name a chunk). Many sheet items missed the expected number. The stored ongoing-cost cells are `not_extracted`.

## Cost

Retail prices used for the estimate, USD, Sweden Central, read on 2026-11-24. Chat is GPT-4.1-mini global at $0.40 / 1M input tokens and $1.60 / 1M output tokens, about $0.004 for one follow-up. Embeddings are text-embedding-3-small global at $0.02 / 1M tokens. Loading the sheet does not call a model. Search stays on the free tier. Container Apps scale to zero. A careful month of demos stays around a few dollars, almost all of it tokens. The trace below records one real call.

One accepted `POST /ask` on the deployed app, 2026-11-26. The question is not a trace field.

```json
{
  "request_id": "54ae2dfe-724d-440e-b12b-ac25ab6686d5",
  "caller": "demo",
  "latency_ms": 6291,
  "total_tokens": 4633,
  "cost_usd": 0.00220258,
  "chunk_ids": [
    "FI0008801907:what:1:0",
    "report-2026-q3:pharos:10:0",
    "report-2026-q3:rahaston-avaintiedot:9:0",
    "report-2026-q3:aktiiviset-rahastot:2:0",
    "report-2026-q3:pharos:10:2",
    "report-2026-q3:pharos:10:3",
    "report-2026-q3:pharos-ja-vertailuindeksi:9:0",
    "report-2026-q3:pharos:11:0"
  ],
  "reason": null,
  "children": [
    {
      "name": "router",
      "prompt_id": "router_v1",
      "deployment": "gpt-4.1-mini",
      "model_version": "gpt-4.1-mini-2025-04-14",
      "latency_ms": 1306,
      "input_tokens": 344,
      "output_tokens": 34
    },
    {
      "name": "embed",
      "prompt_id": "",
      "deployment": "text-embedding-3-small",
      "model_version": "text-embedding-3-small",
      "latency_ms": 779,
      "input_tokens": 9,
      "output_tokens": 0
    },
    {
      "name": "grade",
      "prompt_id": "grade_v1",
      "deployment": "gpt-4.1-mini",
      "model_version": "gpt-4.1-mini-2025-04-14",
      "latency_ms": 2789,
      "input_tokens": 3592,
      "output_tokens": 188
    },
    {
      "name": "answer",
      "prompt_id": "answer_v1",
      "deployment": "gpt-4.1-mini",
      "model_version": "gpt-4.1-mini-2025-04-14",
      "latency_ms": 1330,
      "input_tokens": 394,
      "output_tokens": 72
    }
  ],
  "instrument_ids": []
}
```

## What the project shows

The longer table is `docs/01-gap-map.md`.

| Signal | Where it shows up |
| --- | --- |
| Python for a production service | FastAPI app, pytest, `uv` packaging |
| Azure AI | Azure OpenAI chat and embeddings, Azure AI Search, Blob, Key Vault, Container Apps |
| RAG | Parse, chunk, embed, hybrid search, a cited sheet, follow-up citations |
| One orchestration path | Route, then the stored sheet or retrieve, grade, and a cited answer. Comparison math is Python |
| Evaluation | `eval/golden.json`, retrieval hit rate, citation checks, refusals, pull-request CI, a manual live run |
| Observability | One trace per accepted `/ask`: latency, tokens, cost, retrieved ids, reason. Application Insights when the connection string is set |
| LLMOps | GitHub Actions, versioned prompts, the golden file, the container image, Bicep |
| MCP | Local stdio tools `retrieve` and `compare_sentence`. Not on the public URL |
| Security and cost | Separate web and ingest identities, no prompt text in the trace, an envelope that rejects extra fields, cost on the trace, one delete command for the group |
| Regulated finance setting | A cited sheet over public fund documents, and an explicit non-advice boundary |

This is a research aid over public documents. It is not investment advice, and it is not a product of any bank or fund company.

