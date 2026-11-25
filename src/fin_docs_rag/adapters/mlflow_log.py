def log_run(report: dict, prompt_versions: dict[str, str], tracking_uri: str) -> None:
    import os

    import mlflow

    os.environ["MLFLOW_ALLOW_FILE_STORE"] = "true"
    mlflow.set_tracking_uri(tracking_uri)
    mlflow.set_experiment("fin-docs-rag")
    with mlflow.start_run():
        mlflow.log_param("eval_set_version", report["eval_set_version"])
        mlflow.log_param("k", str(report["k"]))
        mlflow.log_param("ok", str(report["ok"]).lower())
        for name, version in prompt_versions.items():
            mlflow.log_param(name, version)
        rate = report["hit_rate_at_k"]
        mlflow.log_metric("hit_rate_at_k", 0.0 if rate is None else rate)
        mlflow.log_metric("items", report["items"])
        mlflow.log_metric("failures", len(report["failures"]))
