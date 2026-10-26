"""Persistence, authentication, and artifact-storage helpers for model versions."""

from __future__ import annotations

import hashlib
import io
import json
import math
import os
from pathlib import Path
from urllib.parse import urlparse
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

import boto3
import joblib
import jwt
import psycopg
from botocore.config import Config
from flask import request
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

SUPPORTED_MODULES = {"upstream", "formulation"}
SUPPORTED_ALGORITHMS = {"ridge", "lasso", "svm", "random_forest"}
ARTIFACT_PREFIX = "model-artifacts/"
DATASET_PREFIX = "datasets/"
ARTIFACT_MAX_BYTES = 100 * 1024 * 1024
_jwks_client = None


@dataclass(frozen=True)
class Identity:
    user_id: str
    tenant_id: str
    is_admin: bool


def registry_configured() -> bool:
    return bool(os.getenv("DATABASE_URL") and os.getenv("SUPABASE_STORAGE_BUCKET"))


def connect() -> psycopg.Connection:
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL is required for model registry operations")
    return psycopg.connect(database_url, row_factory=dict_row, connect_timeout=5)


def storage_client():
    required = (
        "SUPABASE_STORAGE_ENDPOINT",
        "SUPABASE_STORAGE_REGION",
        "SUPABASE_STORAGE_BUCKET",
        "SUPABASE_S3_ACCESS_KEY_ID",
        "SUPABASE_S3_SECRET_ACCESS_KEY",
    )
    missing = [name for name in required if not os.getenv(name)]
    if missing:
        raise RuntimeError(f"Object storage is not configured; missing {', '.join(missing)}")
    return boto3.client(
        "s3",
        endpoint_url=os.environ["SUPABASE_STORAGE_ENDPOINT"].rstrip("/"),
        aws_access_key_id=os.environ["SUPABASE_S3_ACCESS_KEY_ID"],
        aws_secret_access_key=os.environ["SUPABASE_S3_SECRET_ACCESS_KEY"],
        region_name=os.environ["SUPABASE_STORAGE_REGION"],
        config=Config(
            signature_version="s3v4", connect_timeout=5, read_timeout=30,
            retries={"max_attempts": 3},
            s3={"addressing_style": "path"},
        ),
    )


def bucket_name() -> str:
    bucket = os.getenv("SUPABASE_STORAGE_BUCKET")
    if not bucket:
        raise RuntimeError("SUPABASE_STORAGE_BUCKET is required for artifact storage")
    return bucket


def supabase_url() -> str:
    """Return the project URL used to validate Supabase token issuers.

    ``NEXT_PUBLIC_SUPABASE_URL`` is the standard frontend name and contains
    only the public project URL.  Accepting it here lets a shared deployment
    environment verify tokens when the server-specific alias was not added.
    ``SUPABASE_URL`` takes precedence so backend configuration remains
    explicit where it is present.
    """
    configured_url = (
        os.getenv("SUPABASE_URL")
        or os.getenv("NEXT_PUBLIC_SUPABASE_URL")
        or ""
    ).rstrip("/")
    if configured_url:
        return configured_url

    # Storage is configured only on the server and uses a project-specific
    # endpoint such as https://<project-ref>.storage.supabase.co/storage/v1/s3.
    # Its project reference is safe to use as the expected JWT issuer; unlike
    # reading ``iss`` from an unverified token, it cannot be attacker supplied.
    storage_host = urlparse(os.getenv("SUPABASE_STORAGE_ENDPOINT", "")).hostname
    if storage_host:
        marker = ".storage.supabase.co"
        if storage_host.endswith(marker):
            project_ref = storage_host[: -len(marker)]
            if project_ref:
                return f"https://{project_ref}.supabase.co"

    # Render's PostgreSQL connection string is another server-only setting
    # already required by the registry. Supabase database hosts are named
    # db.<project-ref>.supabase.co.
    database_host = urlparse(os.getenv("DATABASE_URL", "")).hostname
    if database_host:
        marker = "db."
        suffix = ".supabase.co"
        if database_host.startswith(marker) and database_host.endswith(suffix):
            project_ref = database_host[len(marker) : -len(suffix)]
            if project_ref:
                return f"https://{project_ref}.supabase.co"
    return ""


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def authenticate() -> Identity:
    """Verify a Supabase access token and return server-controlled role claims."""
    auth_header = request.headers.get("Authorization", "")
    scheme, _, token = auth_header.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise PermissionError("A valid Supabase bearer token is required")

    issuer_base = supabase_url()
    if not issuer_base:
        raise RuntimeError(
            "SUPABASE_URL (or NEXT_PUBLIC_SUPABASE_URL) must be configured "
            "for token issuer verification; SUPABASE_STORAGE_ENDPOINT can "
            "also provide the project URL, as can a Supabase DATABASE_URL"
        )
    issuer = f"{issuer_base}/auth/v1"
    secret = os.getenv("SUPABASE_JWT_SECRET")
    try:
        if secret:
            claims = jwt.decode(
                token, secret, algorithms=["HS256"], audience="authenticated",
                issuer=issuer, options={"require": ["exp", "iat", "sub"]},
            )
        else:
            global _jwks_client
            if _jwks_client is None:
                _jwks_client = jwt.PyJWKClient(f"{issuer}/.well-known/jwks.json")
            signing_key = _jwks_client.get_signing_key_from_jwt(token)
            claims = jwt.decode(
                token, signing_key.key, algorithms=["ES256", "RS256"],
                audience="authenticated", issuer=issuer,
                options={"require": ["exp", "iat", "sub"]},
            )
    except (jwt.PyJWTError, ValueError) as exc:
        raise PermissionError("Invalid or expired Supabase access token") from exc

    user_id = claims.get("sub")
    app_metadata = claims.get("app_metadata")
    app_metadata = app_metadata if isinstance(app_metadata, dict) else {}
    if not isinstance(user_id, str) or not user_id:
        raise PermissionError("Supabase token does not contain a user identity")

    tenant_id = app_metadata.get("organization_id")
    tenant_id = tenant_id if isinstance(tenant_id, str) and tenant_id else user_id
    roles = app_metadata.get("roles", [])
    is_admin = app_metadata.get("graphtal_role") == "admin" or (
        isinstance(roles, list) and "graphtal_admin" in roles
    )
    return Identity(user_id=user_id, tenant_id=tenant_id, is_admin=is_admin)


def expected_schema(module: str) -> dict[str, Any]:
    if module not in SUPPORTED_MODULES:
        raise ValueError(f"Unsupported module: {module}")
    backend_root = Path(__file__).resolve().parent
    relative = Path("formulation/columns.json") if module == "formulation" else Path("columns.json")
    candidates = (
        backend_root / "model" / relative,
        backend_root.parent / "model" / relative,
        backend_root.parent / "backend" / "model" / relative,
    )
    for path in candidates:
        try:
            with path.open(encoding="utf-8") as config_file:
                schema = json.load(config_file)
            if schema.get("inputs") and schema.get("outputs"):
                return schema
        except FileNotFoundError:
            continue
    raise RuntimeError(f"Feature schema is unavailable for {module}")


def store_dataset(owner_id: str, tenant_id: str, module: str, raw: bytes,
                  row_count: int, columns: list[str], file_name: str,
                  data_format: str) -> dict[str, Any]:
    if module not in SUPPORTED_MODULES:
        raise ValueError("module must be upstream or formulation")
    if not raw or len(raw) > ARTIFACT_MAX_BYTES:
        raise ValueError("Dataset is empty or exceeds the 100 MB upload limit")
    dataset_id = uuid4()
    digest = sha256(raw)
    if data_format not in {"csv", "xls", "xlsx"}:
        raise ValueError("Unsupported dataset file format")
    key = f"{DATASET_PREFIX}{tenant_id}/{dataset_id}.{data_format}"
    storage_client().put_object(
        Bucket=bucket_name(), Key=key, Body=raw,
        ContentType=(
            "text/csv" if data_format == "csv" else (
                "application/vnd.ms-excel" if data_format == "xls"
                else "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        ),
        Metadata={"sha256": digest},
    )
    try:
        with connect() as connection:
            connection.execute(
                "SELECT pg_advisory_xact_lock(hashtext(%s))",
                (f"{owner_id}:{module}",),
            )
            version = connection.execute(
                "SELECT COALESCE(MAX(version), 0) + 1 AS version FROM datasets "
                "WHERE owner_id = %s AND module = %s",
                (owner_id, module),
            ).fetchone()["version"]
            row = connection.execute(
                """
                INSERT INTO datasets
                    (id, owner_id, tenant_id, module, version, checksum, storage_key,
                     file_name, data_format, row_count, feature_schema)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id, module, version, checksum, row_count, created_at
                """,
                (dataset_id, owner_id, tenant_id, module, version, digest, key,
                 file_name, data_format, row_count, Jsonb({"columns": columns})),
            ).fetchone()
    except Exception:
        storage_client().delete_object(Bucket=bucket_name(), Key=key)
        raise
    return row


def fetch_dataset(dataset_id: UUID, owner_id: str) -> tuple[dict[str, Any], bytes]:
    with connect() as connection:
        row = connection.execute(
            "SELECT * FROM datasets WHERE id = %s AND owner_id = %s",
            (dataset_id, owner_id),
        ).fetchone()
    if not row:
        raise LookupError("Dataset not found")
    body = storage_client().get_object(Bucket=bucket_name(), Key=row["storage_key"])["Body"].read()
    if sha256(body) != row["checksum"]:
        raise ValueError("Dataset checksum verification failed")
    return row, body


def list_models(identity: Identity, module: str | None = None) -> list[dict[str, Any]]:
    with connect() as connection:
        rows = connection.execute(
            """
            SELECT m.id, m.module, m.target, m.algorithm, m.version, m.dataset_id,
                   d.version AS dataset_version, m.metrics, m.status, m.created_at, m.approved_at,
                   a.model_id = m.id AS is_active
            FROM model_versions m
            JOIN datasets d ON d.id = m.dataset_id
            LEFT JOIN active_models a
              ON a.module = m.module AND a.target = m.target
             AND a.algorithm = m.algorithm
            WHERE m.tenant_id = %s AND (%s::text IS NULL OR m.module = %s)
            ORDER BY m.created_at DESC
            """,
            (identity.tenant_id, module, module),
        ).fetchall()
    return rows


def active_version(module: str, target: str, algorithm: str) -> dict[str, Any] | None:
    with connect() as connection:
        return connection.execute(
            """
            SELECT m.* FROM active_models a JOIN model_versions m ON m.id = a.model_id
            WHERE a.module = %s AND a.target = %s AND a.algorithm = %s
            """,
            (module, target, algorithm),
        ).fetchone()


def load_active_models(module: str, input_columns: list[str],
                       known_versions: dict[str, str] | None = None) -> tuple[
    dict[str, dict[str, tuple[Any, Any]]], dict[str, str]
]:
    with connect() as connection:
        rows = connection.execute(
            """
            SELECT m.* FROM active_models a JOIN model_versions m ON m.id = a.model_id
            WHERE a.module = %s ORDER BY a.target, a.algorithm
            """,
            (module,),
        ).fetchall()
    loaded: dict[str, dict[str, tuple[Any, Any]]] = {}
    versions: dict[str, str] = {}
    for row in rows:
        if row["algorithm"] not in SUPPORTED_ALGORITHMS:
            raise ValueError(f"Unsupported registered algorithm: {row['algorithm']}")
        key = f"{row['target']}:{row['algorithm']}"
        model_id = str(row["id"])
        versions[key] = model_id
        if known_versions and known_versions.get(key) == model_id:
            continue
        bundle = validate_model_artifact(row, input_columns)
        loaded.setdefault(row["algorithm"], {})[row["target"]] = (
            bundle["model"], bundle["scaler"]
        )
    return loaded, versions


def validate_model_artifact(row: dict[str, Any],
                            input_columns: list[str] | None = None) -> dict[str, Any]:
    module_schema = expected_schema(row["module"])
    expected = input_columns or module_schema["inputs"]
    if row["target"] not in module_schema["outputs"]:
        raise ValueError(f"Model target is not part of the {row['module']} schema")
    artifact = download_artifact(row)
    bundle = joblib.load(io.BytesIO(artifact))
    schema = row["feature_schema"]
    if (
        not isinstance(bundle, dict)
        or bundle.get("feature_schema") != schema
        or schema.get("inputs") != expected
        or schema.get("target") != row["target"]
        or schema.get("algorithm") != row["algorithm"]
        or schema.get("schema_version") != row["schema_version"]
        or not hasattr(bundle.get("model"), "predict")
        or not hasattr(bundle.get("scaler"), "transform")
    ):
        raise ValueError(
            f"Registered artifact for {row['module']}/{row['target']} "
            "does not match its trusted feature schema"
        )
    n_features = getattr(bundle["model"], "n_features_in_", len(expected))
    scaler_features = getattr(bundle["scaler"], "n_features_in_", len(expected))
    if n_features != len(expected) or scaler_features != len(expected):
        raise ValueError(f"Model feature count mismatch for target {row['target']}")
    return bundle


def load_pinned_local_models(module: str, input_columns: list[str]) -> dict[
    str, dict[str, tuple[Any, Any]]
]:
    cache_root = Path(os.getenv(
        "MODEL_CACHE_DIR", str(Path(__file__).resolve().parent / "model-cache")
    )).resolve()
    pointer = cache_root / "active.json"
    if not pointer.exists():
        return {}
    try:
        with pointer.open(encoding="utf-8") as pointer_file:
            manifest = json.load(pointer_file)
        module_models = manifest.get(module, {})
        expected_outputs = expected_schema(module)["outputs"]
        result: dict[str, dict[str, tuple[Any, Any]]] = {}
        for key, item in module_models.items():
            target, algorithm = key.rsplit(":", 1)
            if algorithm not in SUPPORTED_ALGORITHMS or target not in expected_outputs:
                raise ValueError(f"Local model cache contains an unsupported model: {key}")
            artifact_path = (cache_root / item["path"]).resolve()
            if not artifact_path.is_relative_to(cache_root):
                raise ValueError("Model cache path is outside the configured cache directory")
            artifact = artifact_path.read_bytes()
            if sha256(artifact) != item["checksum"]:
                raise ValueError(f"Local model cache checksum mismatch for {key}")
            bundle = joblib.load(io.BytesIO(artifact))
            schema = bundle.get("feature_schema", {})
            if (
                schema.get("inputs") != input_columns
                or schema.get("target") != target
                or schema.get("algorithm") != algorithm
                or schema.get("schema_version") != 1
                or item.get("schema_version") != 1
                or not hasattr(bundle.get("model"), "predict")
                or not hasattr(bundle.get("scaler"), "transform")
            ):
                raise ValueError(f"Local cached model has an incompatible schema: {key}")
            result.setdefault(algorithm, {})[target] = (
                bundle["model"], bundle["scaler"]
            )
        return result
    except FileNotFoundError:
        raise
    except Exception as exc:
        raise RuntimeError(f"Unable to load pinned local model cache: {exc}") from exc


def download_artifact(row: dict[str, Any]) -> bytes:
    if not str(row["artifact_key"]).startswith(ARTIFACT_PREFIX):
        raise ValueError("Artifact key is outside the model artifact namespace")
    if row.get("schema_version") != 1:
        raise ValueError("Unsupported model feature-schema version")
    artifact = storage_client().get_object(
        Bucket=bucket_name(), Key=row["artifact_key"]
    )["Body"].read()
    if len(artifact) > ARTIFACT_MAX_BYTES:
        raise ValueError("Model artifact exceeds the configured size limit")
    if sha256(artifact) != row["checksum"]:
        raise ValueError("Model artifact checksum verification failed")
    return artifact


def create_model_version(*, owner_id: str, tenant_id: str, module: str,
                         training_job_id: UUID, target: str, algorithm: str,
                         dataset_id: UUID,
                         artifact: bytes, feature_schema: dict[str, Any],
                         training_config: dict[str, Any],
                         metrics: dict[str, Any]) -> dict[str, Any]:
    model_id = uuid4()
    digest = sha256(artifact)
    key = f"{ARTIFACT_PREFIX}{module}/{model_id}.joblib"
    client = storage_client()
    with connect() as connection:
        existing = connection.execute(
            """
            SELECT id, module, target, algorithm, version, dataset_id, metrics,
                   status, created_at FROM model_versions
            WHERE training_job_id = %s AND module = %s AND target = %s
              AND algorithm = %s
            """,
            (training_job_id, module, target, algorithm),
        ).fetchone()
    if existing:
        return existing
    client.put_object(
        Bucket=bucket_name(), Key=key, Body=artifact,
        ContentType="application/octet-stream", Metadata={"sha256": digest},
    )
    try:
        with connect() as connection:
            connection.execute(
                "SELECT pg_advisory_xact_lock(hashtext(%s))",
                (f"{module}:{target}:{algorithm}",),
            )
            version = connection.execute(
                """
                SELECT COALESCE(MAX(version), 0) + 1 AS version FROM model_versions
                WHERE module = %s AND target = %s AND algorithm = %s
                """,
                (module, target, algorithm),
            ).fetchone()["version"]
            row = connection.execute(
                """
                INSERT INTO model_versions
                    (id, training_job_id, owner_id, tenant_id, module, target, algorithm, version,
                     dataset_id, artifact_key, checksum, feature_schema,
                     training_config, metrics, status)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'candidate')
                RETURNING id, module, target, algorithm, version, dataset_id,
                          metrics, status, created_at
                """,
                (
                    model_id, training_job_id, owner_id, tenant_id, module, target,
                    algorithm, version,
                    dataset_id, key, digest, Jsonb(feature_schema),
                    Jsonb(training_config), Jsonb(metrics),
                ),
            ).fetchone()
    except psycopg.errors.UniqueViolation:
        client.delete_object(Bucket=bucket_name(), Key=key)
        with connect() as connection:
            existing = connection.execute(
                """
                SELECT id, module, target, algorithm, version, dataset_id, metrics,
                       status, created_at FROM model_versions
                WHERE training_job_id = %s AND module = %s AND target = %s
                  AND algorithm = %s
                """,
                (training_job_id, module, target, algorithm),
            ).fetchone()
        if existing:
            return existing
        raise
    except Exception:
        client.delete_object(Bucket=bucket_name(), Key=key)
        raise
    return row


def approve_and_promote(model_id: UUID, identity: Identity) -> dict[str, Any]:
    if not identity.is_admin:
        raise PermissionError("Only Graphtal administrators can promote model versions")
    with connect() as connection:
        candidate = connection.execute(
            "SELECT * FROM model_versions WHERE id = %s AND tenant_id = %s FOR UPDATE",
            (model_id, identity.tenant_id),
        ).fetchone()
        if not candidate:
            raise LookupError("Model version not found")
        connection.execute(
            "SELECT pg_advisory_xact_lock(hashtext(%s))",
            (f"{candidate['module']}:{candidate['target']}:{candidate['algorithm']}",),
        )
        if candidate["status"] not in ("candidate", "active", "archived"):
            raise ValueError("Only eligible model versions can be promoted")
        metrics = candidate["metrics"]
        minimum_score = float(os.getenv("MODEL_MIN_TEST_R2", "-1"))
        test_r2 = metrics.get("test_r2")
        if not math.isfinite(minimum_score):
            raise RuntimeError("MODEL_MIN_TEST_R2 must be a finite number")
        if (
            not isinstance(test_r2, (int, float))
            or not math.isfinite(float(test_r2))
            or test_r2 < minimum_score
        ):
            raise ValueError(f"Model does not meet MODEL_MIN_TEST_R2={minimum_score}")
        if metrics.get("eligible_for_promotion") is not True:
            raise ValueError("Candidate did not match or exceed the active model on its holdout set")
        validate_model_artifact(candidate)
        previous = connection.execute(
            """
            SELECT model_id FROM active_models
            WHERE module = %s AND target = %s AND algorithm = %s FOR UPDATE
            """,
            (candidate["module"], candidate["target"], candidate["algorithm"]),
        ).fetchone()
        previous_id = previous["model_id"] if previous else None
        connection.execute(
            "UPDATE model_versions SET status = 'archived' "
            "WHERE id = %s AND status = 'active'",
            (previous_id,),
        )
        connection.execute(
            """
            UPDATE model_versions
            SET status = 'active', approved_at = COALESCE(approved_at, now()),
                approved_by = COALESCE(approved_by, %s), activated_at = now(),
                activated_by = %s
            WHERE id = %s
            """,
            (identity.user_id, identity.user_id, model_id),
        )
        connection.execute(
            """
            INSERT INTO active_models (module, target, algorithm, model_id, activated_at)
            VALUES (%s, %s, %s, %s, now())
            ON CONFLICT (module, target, algorithm)
            DO UPDATE SET model_id = EXCLUDED.model_id, activated_at = now()
            """,
            (candidate["module"], candidate["target"], candidate["algorithm"], model_id),
        )
        connection.execute(
            """
            INSERT INTO model_audit_log
                (actor_id, tenant_id, action, model_id, previous_model_id)
            VALUES (%s, %s, 'promote', %s, %s)
            """,
            (identity.user_id, identity.tenant_id, model_id, previous_id),
        )
        return {
            "id": model_id,
            "previous_model_id": previous_id,
            "module": candidate["module"],
            "target": candidate["target"],
            "algorithm": candidate["algorithm"],
        }


def rollback_model(model_id: UUID, identity: Identity) -> dict[str, Any]:
    if not identity.is_admin:
        raise PermissionError("Only Graphtal administrators can roll back model versions")
    with connect() as connection:
        row = connection.execute(
            "SELECT * FROM model_versions WHERE id = %s AND tenant_id = %s FOR UPDATE",
            (model_id, identity.tenant_id),
        ).fetchone()
        if not row or row["status"] not in ("archived", "active"):
            raise LookupError("An archived model version was not found")
        connection.execute(
            "SELECT pg_advisory_xact_lock(hashtext(%s))",
            (f"{row['module']}:{row['target']}:{row['algorithm']}",),
        )
        validate_model_artifact(row)
        previous = connection.execute(
            """
            SELECT model_id FROM active_models
            WHERE module = %s AND target = %s AND algorithm = %s FOR UPDATE
            """,
            (row["module"], row["target"], row["algorithm"]),
        ).fetchone()
        previous_id = previous["model_id"] if previous else None
        connection.execute(
            "UPDATE model_versions SET status = 'archived' WHERE id = %s",
            (previous_id,),
        )
        connection.execute(
            "UPDATE model_versions SET status = 'active', activated_at = now(), "
            "activated_by = %s, approved_at = COALESCE(approved_at, now()), "
            "approved_by = COALESCE(approved_by, %s) WHERE id = %s",
            (identity.user_id, identity.user_id, model_id),
        )
        connection.execute(
            """
            INSERT INTO active_models (module, target, algorithm, model_id, activated_at)
            VALUES (%s, %s, %s, %s, now())
            ON CONFLICT (module, target, algorithm)
            DO UPDATE SET model_id = EXCLUDED.model_id, activated_at = now()
            """,
            (row["module"], row["target"], row["algorithm"], model_id),
        )
        connection.execute(
            """
            INSERT INTO model_audit_log
                (actor_id, tenant_id, action, model_id, previous_model_id)
            VALUES (%s, %s, 'rollback', %s, %s)
            """,
            (identity.user_id, identity.tenant_id, model_id, previous_id),
        )
        return {
            "id": model_id, "previous_model_id": previous_id,
            "module": row["module"], "target": row["target"],
            "algorithm": row["algorithm"],
        }


def create_training_job(*, job_id: UUID, identity: Identity, module: str,
                        dataset_id: UUID, idempotency_key: str) -> dict[str, Any]:
    if module not in SUPPORTED_MODULES:
        raise ValueError("module must be upstream or formulation")
    with connect() as connection:
        connection.execute(
            "SELECT pg_advisory_xact_lock(hashtext(%s))",
            (f"training:{identity.user_id}",),
        )
        dataset = connection.execute(
            "SELECT id FROM datasets WHERE id = %s AND owner_id = %s "
            "AND tenant_id = %s AND module = %s",
            (dataset_id, identity.user_id, identity.tenant_id, module),
        ).fetchone()
        if not dataset:
            raise LookupError("Dataset not found")
        existing = connection.execute(
            "SELECT id, status, progress, message, created_at, false AS created "
            "FROM training_jobs WHERE owner_id = %s AND idempotency_key = %s",
            (identity.user_id, idempotency_key),
        ).fetchone()
        if existing:
            return existing
        queued_count = connection.execute(
            "SELECT COUNT(*) AS count FROM training_jobs "
            "WHERE owner_id = %s AND status IN ('queued', 'training')",
            (identity.user_id,),
        ).fetchone()["count"]
        quota = max(1, int(os.getenv("MAX_ACTIVE_TRAINING_JOBS_PER_USER", "3")))
        if queued_count >= quota:
            raise ValueError(f"Active training job limit reached ({quota})")
        row = connection.execute(
            """
            INSERT INTO training_jobs
                (id, owner_id, tenant_id, module, dataset_id, status, idempotency_key)
            VALUES (%s, %s, %s, %s, %s, 'queued', %s)
            ON CONFLICT (owner_id, idempotency_key) DO NOTHING
            RETURNING id, status, progress, message, created_at, true AS created
            """,
            (job_id, identity.user_id, identity.tenant_id, module, dataset_id,
             idempotency_key),
        ).fetchone()
        if row:
            return row
        return connection.execute(
            "SELECT id, status, progress, message, created_at, false AS created FROM training_jobs "
            "WHERE owner_id = %s AND idempotency_key = %s",
            (identity.user_id, idempotency_key),
        ).fetchone()


def serialize_row(value: Any) -> Any:
    if isinstance(value, (datetime, UUID)):
        return value.isoformat() if isinstance(value, datetime) else str(value)
    if isinstance(value, dict):
        return {key: serialize_row(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [serialize_row(item) for item in value]
    return value
