import mlflow

from fin_docs_rag.adapters.mlflow_log import log_run


def test_log_run_records_the_hit_rate(tmp_path, monkeypatch):
    monkeypatch.setenv("MLFLOW_DISABLE_TELEMETRY", "true")
    report = {
        "ok": True,
        "eval_set_version": "1",
        "k": 8,
        "items": 1,
        "hit_rate_at_k": 1.0,
        "failures": [],
    }
    log_run(report, {"router_v1": "abc123"}, tmp_path.as_uri())
    mlflow.set_tracking_uri(tmp_path.as_uri())
    runs = mlflow.search_runs(experiment_names=["fin-docs-rag"])
    assert runs.iloc[0]["metrics.hit_rate_at_k"] == 1
    assert runs.iloc[0]["params.eval_set_version"] == "1"
    assert runs.iloc[0]["params.router_v1"] == "abc123"
