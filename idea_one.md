# Superseded

Do not implement this note. The living plan is `docs/README.md`.

Two claims below are withdrawn: the system runs on Azure, and the CI gate is the deterministic check in `docs/06-ai-architecture.md`, not a RAGAS-style judge. Comparison math is `domain/calculate.py`, not a general calculator tool.

# Original note

Gaps relative to the job

Stack is Next.js/TypeScript + Vercel AI SDK + Supabase + xAI, not Python + Azure.
Strong on agents and domain logic; lighter on classic ML, RAG pipelines, formal evaluation suites, monitoring/observability beyond app-level logs, CI/CD for models, or Databricks/Spark-style data work.
One project (even a good one) is thin when the ad wants demonstrated production AI/ML experience.

Python agentic RAG system for financial documents (highest ROI)

Build a retrieval-augmented system that answers questions over real financial docs (e.g., fund prospectuses, annual reports, regulatory filings, or Finnish investment product documents).
Orchestrate agents or multi-step workflows (retrieve → evaluate relevance → answer with citations → optional tools for calculations).
Include evaluation: retrieval metrics, answer faithfulness/groundedness (simple RAGAS-style or custom tests), prompt/version tracking.
Add basic observability (logs, token/cost tracking, failure modes).
Deploy as a small API or app. Document how you would move it to Azure AI Search + Azure OpenAI + monitoring.
This directly hits RAG, agents, evaluation, quality, and finance domain.