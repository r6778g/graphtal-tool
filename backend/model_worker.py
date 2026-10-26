"""RQ background worker that trains isolated, versioned candidate models."""

from __future__ import annotations

import io
import os
from uuid import UUID

import joblib
import pandas as pd
from redis import Redis
from rq import Queue, Retry
from sklearn.base import clone
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import Lasso, Ridge
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVR

import model_registry as registry
from predict import predictor as upstream_predictor
from predict_formulation import formulation_predictor

MODEL_REGISTRY = {
    "ridge": Ridge(alpha=1.0),
    "lasso": Lasso(alpha=0.1, max_iter=10_000),
    "svm": SVR(kernel="rbf", C=10, epsilon=0.1),
    "random_forest": RandomForestRegressor(
        n_estimators=100, random_state=42, n_jobs=1
    ),
}


def training_queue() -> Queue:
    redis_url = os.getenv("REDIS_URL")
    if not redis_url:
        raise RuntimeError("REDIS_URL is required to queue model training")
    connection = Redis.from_url(redis_url, socket_connect_timeout=5)
    connection.ping()
    return Queue("model-training", connection=connection)


def _set_job(job_id: UUID, status: str, progress: int, message: str,
             candidate_ids: list[str] | None = None) -> None:
    with registry.connect() as connection:
        if candidate_ids is None:
            connection.execute(
                """
                UPDATE training_jobs
                SET status = %s, progress = %s, message = %s, updated_at = now()
                WHERE id = %s
                """,
                (status, progress, message[:500], job_id),
            )
        else:
            connection.execute(
                """
                UPDATE training_jobs
                SET status = %s, progress = %s, message = %s,
                    candidate_ids = %s, updated_at = now()
                WHERE id = %s
                """,
                (
                    status, progress, message[:500],
                    [UUID(candidate_id) for candidate_id in candidate_ids], job_id,
                ),
            )


def _read_dataset(row: dict) -> pd.DataFrame:
    body = registry.storage_client().get_object(
        Bucket=registry.bucket_name(), Key=row["storage_key"]
    )["Body"].read()
    if registry.sha256(body) != row["checksum"]:
        raise ValueError(f"Dataset {row['id']} failed checksum verification")
    if row["data_format"] == "csv":
        return pd.read_csv(io.BytesIO(body))
    engine = "xlrd" if row["data_format"] == "xls" else "openpyxl"
    return pd.read_excel(io.BytesIO(body), engine=engine)


def _load_active_metrics_and_score(module: str, target: str, algorithm: str,
                                   X_test: pd.DataFrame, y_test: pd.Series) -> float | None:
    row = registry.active_version(module, target, algorithm)
    if row:
        bundle = registry.validate_model_artifact(row, list(X_test.columns))
        baseline_model, baseline_scaler = bundle["model"], bundle["scaler"]
    else:
        predictor = (
            upstream_predictor if module == "upstream" else formulation_predictor
        )
        predictor.refresh_active(force=True)
        baseline_model, baseline_scaler = predictor._get_model_and_scaler(
            algorithm, target
        )
        if baseline_model is None or baseline_scaler is None:
            return None
    features = baseline_scaler.transform(X_test)
    return float(baseline_model.score(features, y_test))


def run_training_job(job_id: str) -> None:
    job_uuid = UUID(job_id)
    with registry.connect() as connection:
        job = connection.execute(
            "SELECT * FROM training_jobs WHERE id = %s",
            (job_uuid,),
        ).fetchone()
    if not job:
        raise LookupError(f"Training job {job_id} was not found")
    if job["status"] == "candidate":
        return

    try:
        _set_job(job_uuid, "training", 2, "Loading validated dataset versions")
        with registry.connect() as connection:
            datasets = connection.execute(
                """
                SELECT d.* FROM datasets d
                JOIN datasets selected ON selected.id = %s
                WHERE d.tenant_id = %s AND d.module = %s
                  AND d.created_at <= selected.created_at
                ORDER BY d.created_at, d.id
                """,
                (job["dataset_id"], job["tenant_id"], job["module"]),
            ).fetchall()
        max_rows = max(8, int(os.getenv("MAX_TRAINING_ROWS", "100000")))
        if sum(dataset["row_count"] for dataset in datasets) > max_rows:
            raise ValueError(f"Combined approved datasets exceed the {max_rows} row limit")
        frames = [_read_dataset(dataset) for dataset in datasets]
        data = pd.concat(frames, ignore_index=True).drop_duplicates()
        if len(data) > max_rows:
            raise ValueError(f"Combined dataset exceeds the {max_rows} row limit")
        schema = registry.expected_schema(job["module"])
        inputs = schema["inputs"]
        outputs = schema["outputs"]
        missing = [name for name in inputs + outputs if name not in data.columns]
        if missing:
            raise ValueError(f"Training data is missing schema columns: {missing}")
        data = data[inputs + outputs].apply(pd.to_numeric, errors="raise").dropna()
        if len(data) < 8:
            raise ValueError("At least 8 complete, unique rows are required for evaluation")

        candidate_ids: list[str] = []
        total = len(outputs) * len(MODEL_REGISTRY)
        completed = 0
        for algorithm, base_model in MODEL_REGISTRY.items():
            for target in outputs:
                X_train, X_test, y_train, y_test = train_test_split(
                    data[inputs], data[target], test_size=0.2, random_state=42
                )
                scaler = StandardScaler()
                X_train_scaled = scaler.fit_transform(X_train)
                X_test_scaled = scaler.transform(X_test)
                model = clone(base_model)
                model.fit(X_train_scaled, y_train)
                test_r2 = float(model.score(X_test_scaled, y_test))
                active_test_r2 = _load_active_metrics_and_score(
                    job["module"], target, algorithm, X_test, y_test
                )
                schema_record = {
                    "inputs": inputs,
                    "target": target,
                    "algorithm": algorithm,
                    "schema_version": 1,
                }
                metrics = {
                    "train_r2": float(model.score(X_train_scaled, y_train)),
                    "test_r2": test_r2,
                    "active_test_r2": active_test_r2,
                    "test_r2_delta": (
                        test_r2 - active_test_r2 if active_test_r2 is not None else None
                    ),
                    "eligible_for_promotion": (
                        active_test_r2 is None or test_r2 >= active_test_r2
                    ),
                    "evaluation_rows": len(y_test),
                    "training_rows": len(y_train),
                }
                serialized = io.BytesIO()
                joblib.dump(
                    {
                        "model": model,
                        "scaler": scaler,
                        "feature_schema": schema_record,
                    },
                    serialized,
                    compress=3,
                )
                candidate = registry.create_model_version(
                    owner_id=job["owner_id"],
                    tenant_id=job["tenant_id"],
                    module=job["module"],
                    training_job_id=job_uuid,
                    target=target,
                    algorithm=algorithm,
                    dataset_id=job["dataset_id"],
                    artifact=serialized.getvalue(),
                    feature_schema=schema_record,
                    training_config={
                        "seed": 42,
                        "test_size": 0.2,
                        "approved_dataset_ids": [str(row["id"]) for row in datasets],
                        "rows_after_deduplication": len(data),
                    },
                    metrics=metrics,
                )
                candidate_ids.append(str(candidate["id"]))
                completed += 1
                _set_job(
                    job_uuid, "training", int(5 + completed / total * 90),
                    f"Trained {completed} of {total} candidate models",
                    candidate_ids,
                )

        _set_job(
            job_uuid, "candidate", 100,
            "Training and evaluation complete; candidates require administrator promotion",
            candidate_ids,
        )
    except Exception as exc:
        _set_job(job_uuid, "failed", 100, f"Training failed: {exc}")
        raise
