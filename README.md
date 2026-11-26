# fin-docs-rag

A research aid over a fixed shelf of public fund documents. It builds a cited fact sheet from those documents, and it answers a follow-up with a citation or an abstention.

The shelf is twelve public PRIIPs key information documents for Finnish funds, from more than one company, plus one longer quarterly review. Titles, publishers, and source URLs are in `sources/manifest.json`. The PDFs stay out of git.

The sheet is the product. Indexing reads one row per fund: what the product is, the risk indicator, the recommended holding period, and the entry, exit, and ongoing costs. Opening the sheet does not call a model. A comparison of two funds is filled in Python from those stored cells. The sentence states both figures, both holding periods, and the difference. It does not rank the funds.

`POST /ask` is the only live model path. A question about a sheet column is read back from the stored row. A question outside those columns is embedded, retrieved with hybrid keyword and vector search, graded, and returned only when every quote is a substring of a chunk retrieved on that turn and every figure matches the number printed in the quote. A high-confidence request for a recommendation stops before search. A question the documents do not support comes back as an abstention, with the titles that were searched.

## What is in the repo

The service is Python 3.12 and FastAPI. It parses the PDFs, chunks them on the KID section headings, and can upload the files, embed them, and query an Azure AI Search index. Chat and extraction use Azure OpenAI. Embeddings are a separate deployment. Original files go to a private blob container. The sheet file is written there when an ingest run finishes.

`eval/golden.json` holds 29 questions. Each one has a path (`sheet`, `retrieve`, or `refuse`) and an expected outcome: a number, a source id, or a reason code. The set includes two funds with similar names, a fact the corpus does not state, and a comparison whose holding periods differ. Pull-request CI runs the suite on fakes. A refusal that returns an answer body fails the check, and so does a run that takes a path other than its label. Retrieval hit rate is measured at the search depth of 8.

`uv run pytest` is the offline suite. One hybrid-search test runs only when Azure credentials are already in the environment.

Resource templates are in `infra/`. A public demo page and a container deploy are still to come, so there is no demo URL yet. Live eval numbers are not published yet.

This is a research aid over public documents. It is not investment advice, and it is not a product of any bank or fund company.

