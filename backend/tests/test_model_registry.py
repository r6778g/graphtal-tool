import io
import json
import tempfile
import threading
import unittest
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4

import joblib
import pandas as pd
from sklearn.linear_model import Ridge

import main
import model_registry
import model_worker
from predict import Predictor
from scripts import sync_models


class Cursor:
    def __init__(self, one=None, many=None):
        self.one = one
        self.many = many or []

    def fetchone(self):
        return self.one

    def fetchall(self):
        return self.many


class RegistryTests(unittest.TestCase):
    def setUp(self):
        main.app.config["TESTING"] = True
        self.client = main.app.test_client()

    def test_prediction_endpoint_response_shape_is_unchanged(self):
        result = {
            "prediction": 123.4,
            "unit": "mg/L",
            "confidence": 0.85,
            "feature_importance": {"Glucose": 0.5},
            "model_type": "ridge",
        }
        with patch.object(main.predict.predictor, "predict", return_value=result):
            response = self.client.post(
                "/predict",
                json={"target": "Titer", "features": {"Glucose": 1}, "model": "ridge"},
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            set(response.json),
            {"prediction", "unit", "confidence", "feature_importance", "model_type"},
        )
        self.assertEqual(response.json["prediction"], 123.4)

    def test_supabase_url_uses_backend_setting_before_public_setting(self):
        with patch.dict(
            "os.environ",
            {
                "SUPABASE_URL": "https://server-project.supabase.co/",
                "NEXT_PUBLIC_SUPABASE_URL": "https://public-project.supabase.co",
            },
            clear=True,
        ):
            self.assertEqual(
                model_registry.supabase_url(), "https://server-project.supabase.co"
            )

    def test_supabase_url_accepts_public_project_url_for_shared_deployments(self):
        with patch.dict(
            "os.environ",
            {"NEXT_PUBLIC_SUPABASE_URL": "https://project.supabase.co/"},
            clear=True,
        ):
            self.assertEqual(model_registry.supabase_url(), "https://project.supabase.co")

    def test_supabase_url_derives_issuer_from_storage_endpoint(self):
        with patch.dict(
            "os.environ",
            {
                "SUPABASE_STORAGE_ENDPOINT": (
                    "https://project-ref.storage.supabase.co/storage/v1/s3"
                )
            },
            clear=True,
        ):
            self.assertEqual(
                model_registry.supabase_url(), "https://project-ref.supabase.co"
            )

    def test_supabase_url_derives_issuer_from_database_url(self):
        with patch.dict(
            "os.environ",
            {
                "DATABASE_URL": (
                    "postgresql://user:password@db.project-ref.supabase.co:5432/postgres"
                )
            },
            clear=True,
        ):
            self.assertEqual(
                model_registry.supabase_url(), "https://project-ref.supabase.co"
            )

    def test_formulation_prediction_endpoint_response_shape_is_unchanged(self):
        result = {
            "prediction": 15.2,
            "unit": "nm",
            "confidence": 0.85,
            "feature_importance": {},
            "model_type": "ridge",
        }
        with patch.object(
            main.predict_formulation.formulation_predictor, "predict", return_value=result
        ):
            response = self.client.post(
                "/formulation-predict",
                json={"target": "Particle Size (nm)", "features": {}, "model": "ridge"},
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            set(response.json),
            {"prediction", "unit", "confidence", "feature_importance", "model_type"},
        )

    def test_legacy_retraining_cannot_overwrite_local_models(self):
        self.assertEqual(self.client.post("/retrain", json={"file_data": {}}).status_code, 410)
        self.assertEqual(
            self.client.post("/formulation-retrain", json={"file_data": {}}).status_code,
            410,
        )

    def test_training_submission_returns_202_and_queues_worker(self):
        identity = model_registry.Identity("user-1", "tenant-1", False)
        job = {
            "id": uuid4(), "status": "queued", "progress": 0,
            "message": "", "created_at": datetime.now(timezone.utc),
            "created": True,
        }

        class Queue:
            def __init__(self):
                self.calls = []

            def enqueue(self, *args, **kwargs):
                self.calls.append((args, kwargs))

        queue = Queue()
        dataset_id = uuid4()
        with (
            patch.object(model_registry, "authenticate", return_value=identity),
            patch.object(model_registry, "create_training_job", return_value=job),
            patch.object(model_worker, "training_queue", return_value=queue),
        ):
            response = self.client.post(
                "/api/training/jobs",
                json={"module": "upstream", "dataset_id": str(dataset_id)},
                headers={"Idempotency-Key": "request-1"},
            )
        self.assertEqual(response.status_code, 202)
        self.assertEqual(len(queue.calls), 1)
        self.assertEqual(queue.calls[0][0][0], "model_worker.run_training_job")

    def test_training_submission_requires_idempotency_key(self):
        identity = model_registry.Identity("user-1", "tenant-1", False)
        with patch.object(model_registry, "authenticate", return_value=identity):
            response = self.client.post(
                "/api/training/jobs",
                json={"module": "upstream", "dataset_id": str(uuid4())},
            )
        self.assertEqual(response.status_code, 400)

    def test_upload_validates_schema_deduplicates_and_stores_original(self):
        identity = model_registry.Identity("user-1", "tenant-1", False)
        schema = {"inputs": ["x"], "outputs": ["y"]}
        stored = {
            "id": uuid4(), "module": "upstream", "version": 1,
            "checksum": "abc", "row_count": 1,
            "created_at": datetime.now(timezone.utc),
        }
        with (
            patch.object(model_registry, "authenticate", return_value=identity),
            patch.object(model_registry, "expected_schema", return_value=schema),
            patch.object(model_registry, "store_dataset", return_value=stored) as store,
        ):
            response = self.client.post(
                "/api/datasets/upload",
                data={
                    "module": "upstream",
                    "file": (io.BytesIO(b"x,y\n1,2\n1,2\n"), "data.csv"),
                },
                content_type="multipart/form-data",
            )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json["duplicate_rows_removed"], 1)
        self.assertEqual(response.json["validated_rows"], 1)
        self.assertEqual(store.call_args.args[2], "upstream")
        self.assertEqual(store.call_args.args[3], b"x,y\n1,2\n1,2\n")

    def test_upload_rejects_missing_required_columns(self):
        identity = model_registry.Identity("user-1", "tenant-1", False)
        with (
            patch.object(model_registry, "authenticate", return_value=identity),
            patch.object(
                model_registry, "expected_schema",
                return_value={"inputs": ["x"], "outputs": ["y"]},
            ),
        ):
            response = self.client.post(
                "/api/datasets/upload",
                data={
                    "module": "upstream",
                    "file": (io.BytesIO(b"x\n1\n"), "data.csv"),
                },
                content_type="multipart/form-data",
            )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json["columns"], ["y"])

    def test_checksum_mismatch_rejects_artifact(self):
        row = {
            "artifact_key": f"{model_registry.ARTIFACT_PREFIX}upstream/test.joblib",
            "checksum": "wrong",
            "schema_version": 1,
        }

        class Storage:
            def get_object(self, **_kwargs):
                return {"Body": io.BytesIO(b"artifact")}

        with (
            patch.object(model_registry, "storage_client", return_value=Storage()),
            patch.object(model_registry, "bucket_name", return_value="private"),
        ):
            with self.assertRaisesRegex(ValueError, "checksum"):
                model_registry.download_artifact(row)

    def test_supabase_storage_client_uses_configured_s3_endpoint_and_path_style(self):
        settings = {
            "SUPABASE_STORAGE_ENDPOINT": "https://project.storage.supabase.co/storage/v1/s3/",
            "SUPABASE_STORAGE_REGION": "project-region",
            "SUPABASE_STORAGE_BUCKET": "private-models",
            "SUPABASE_S3_ACCESS_KEY_ID": "access-key",
            "SUPABASE_S3_SECRET_ACCESS_KEY": "secret-key",
        }
        with (
            patch.dict("os.environ", settings, clear=True),
            patch.object(model_registry.boto3, "client") as create_client,
        ):
            model_registry.storage_client()

        kwargs = create_client.call_args.kwargs
        self.assertEqual(kwargs["endpoint_url"], settings["SUPABASE_STORAGE_ENDPOINT"].rstrip("/"))
        self.assertEqual(kwargs["region_name"], settings["SUPABASE_STORAGE_REGION"])
        self.assertEqual(kwargs["aws_access_key_id"], settings["SUPABASE_S3_ACCESS_KEY_ID"])
        self.assertEqual(kwargs["aws_secret_access_key"], settings["SUPABASE_S3_SECRET_ACCESS_KEY"])
        self.assertEqual(kwargs["config"].s3, {"addressing_style": "path"})

    def test_registry_requires_supabase_storage_bucket_configuration(self):
        with (
            patch.dict("os.environ", {"DATABASE_URL": "postgresql://db"}, clear=True),
        ):
            self.assertFalse(model_registry.registry_configured())
        with patch.dict(
            "os.environ",
            {"DATABASE_URL": "postgresql://db", "SUPABASE_STORAGE_BUCKET": "models"},
            clear=True,
        ):
            self.assertTrue(model_registry.registry_configured())

    def test_refresh_replaces_registry_model_only_after_successful_validation(self):
        predictor = Predictor.__new__(Predictor)
        old_model, old_scaler = object(), object()
        new_model, new_scaler = object(), object()
        predictor.models = {"ridge": {"Titer": old_model}}
        predictor.scalers = {"ridge": {"Titer": old_scaler}}
        predictor._fallback_models = {"ridge": {"Titer": old_model}}
        predictor._fallback_scalers = {"ridge": {"Titer": old_scaler}}
        predictor._registry_models = {}
        predictor._registry_versions = {}
        predictor._last_registry_check = 0
        predictor._lock = threading.RLock()
        predictor._sync_lock = threading.Lock()
        predictor.columns_config = {"inputs": ["x"]}
        active = {"ridge": {"Titer": (new_model, new_scaler)}}
        with (
            patch.object(model_registry, "registry_configured", return_value=True),
            patch.object(
                model_registry, "load_active_models",
                return_value=(active, {"Titer:ridge": "model-1"}),
            ),
        ):
            result = predictor.refresh_active(force=True)
        self.assertEqual(result["status"], "refreshed")
        self.assertIs(predictor.models["ridge"]["Titer"], new_model)
        self.assertIs(predictor.scalers["ridge"]["Titer"], new_scaler)

    def test_failed_refresh_retains_previous_working_model(self):
        predictor = Predictor.__new__(Predictor)
        old_model, old_scaler = object(), object()
        predictor.models = {"ridge": {"Titer": old_model}}
        predictor.scalers = {"ridge": {"Titer": old_scaler}}
        predictor._fallback_models = {"ridge": {"Titer": old_model}}
        predictor._fallback_scalers = {"ridge": {"Titer": old_scaler}}
        predictor._registry_models = {}
        predictor._registry_versions = {}
        predictor._last_registry_check = 0
        predictor._lock = threading.RLock()
        predictor._sync_lock = threading.Lock()
        predictor.columns_config = {"inputs": ["x"]}
        with (
            patch.object(model_registry, "registry_configured", return_value=True),
            patch.object(
                model_registry, "load_active_models",
                side_effect=ValueError("bad checksum"),
            ),
        ):
            result = predictor.refresh_active(force=True)
        self.assertEqual(result["status"], "failed")
        self.assertIs(predictor.models["ridge"]["Titer"], old_model)
        self.assertIs(predictor.scalers["ridge"]["Titer"], old_scaler)

    def test_registry_refresh_is_cached_between_configured_intervals(self):
        predictor = Predictor.__new__(Predictor)
        predictor.models = {"ridge": {}}
        predictor.scalers = {"ridge": {}}
        predictor._fallback_models = {"ridge": {}}
        predictor._fallback_scalers = {"ridge": {}}
        predictor._registry_models = {}
        predictor._registry_versions = {}
        predictor._last_registry_check = 0
        predictor._lock = threading.RLock()
        predictor._sync_lock = threading.Lock()
        predictor.columns_config = {"inputs": ["x"]}
        with (
            patch.object(model_registry, "registry_configured", return_value=True),
            patch.object(
                model_registry, "load_active_models", return_value=({}, {})
            ) as load,
            patch.dict("os.environ", {"MODEL_REGISTRY_REFRESH_SECONDS": "60"}),
        ):
            predictor.refresh_active(force=True)
            self.assertEqual(predictor.refresh_active()["status"], "cached")
        load.assert_called_once()

    def test_only_admin_can_promote_or_rollback(self):
        identity = model_registry.Identity("user-1", "tenant-1", False)
        with self.assertRaises(PermissionError):
            model_registry.approve_and_promote(uuid4(), identity)
        with self.assertRaises(PermissionError):
            model_registry.rollback_model(uuid4(), identity)

    def test_worker_creates_candidates_without_switching_active_pointer(self):
        job_id, dataset_id = uuid4(), uuid4()
        job = {
            "id": job_id, "status": "queued", "owner_id": "user-1",
            "tenant_id": "tenant-1", "module": "upstream", "dataset_id": dataset_id,
        }
        dataset = {"id": dataset_id, "row_count": 20}
        updates = []

        class FakeConnection:
            def execute(self, query, params=None):
                if "SELECT * FROM training_jobs" in query:
                    return Cursor(one=job)
                if "SELECT d.* FROM datasets" in query:
                    return Cursor(many=[dataset])
                if "UPDATE training_jobs" in query:
                    updates.append(params[0])
                return Cursor()

        @contextmanager
        def fake_connect():
            yield FakeConnection()

        frame = pd.DataFrame({"x": range(20), "y": [n * 2 for n in range(20)]})
        candidate_ids = []

        def create_candidate(**kwargs):
            candidate_ids.append(kwargs)
            return {"id": uuid4()}

        with (
            patch.object(model_registry, "connect", side_effect=fake_connect),
            patch.object(model_registry, "expected_schema", return_value={
                "inputs": ["x"], "outputs": ["y"],
            }),
            patch.object(model_worker, "_read_dataset", return_value=frame),
            patch.object(model_worker, "_load_active_metrics_and_score", return_value=None),
            patch.object(model_registry, "create_model_version", side_effect=create_candidate),
            patch.dict(model_worker.MODEL_REGISTRY, {"ridge": Ridge(alpha=1.0)}, clear=True),
        ):
            model_worker.run_training_job(str(job_id))
        self.assertEqual(len(candidate_ids), 1)
        self.assertEqual(candidate_ids[0]["training_job_id"], job_id)
        self.assertIn("candidate", updates)
        self.assertNotIn("active", updates)

    def test_promotion_route_refreshes_both_prediction_modules(self):
        identity = model_registry.Identity("admin-1", "tenant-1", True)
        first = {"status": "refreshed"}
        second = {"status": "refreshed"}
        with (
            patch.object(model_registry, "authenticate", return_value=identity),
            patch.object(
                model_registry, "approve_and_promote",
                return_value={"id": uuid4(), "target": "Titer"},
            ),
            patch.object(main.predict.predictor, "refresh_active", return_value=first),
            patch.object(
                main.predict_formulation.formulation_predictor,
                "refresh_active", return_value=second,
            ),
        ):
            response = self.client.post(f"/api/models/{uuid4()}/promote")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["refresh"]["upstream"], first)
        self.assertEqual(response.json["refresh"]["formulation"], second)

    def test_job_status_query_is_scoped_to_authenticated_owner(self):
        identity = model_registry.Identity("user-1", "tenant-1", False)
        captured = {}

        class FakeConnection:
            def execute(self, query, params):
                captured["query"] = query
                captured["params"] = params
                return Cursor()

        @contextmanager
        def fake_connect():
            yield FakeConnection()

        job_id = uuid4()
        with (
            patch.object(model_registry, "authenticate", return_value=identity),
            patch.object(model_registry, "connect", side_effect=fake_connect),
        ):
            response = self.client.get(f"/api/training/jobs/{job_id}")
        self.assertEqual(response.status_code, 404)
        self.assertIn("owner_id = %s", captured["query"])
        self.assertEqual(captured["params"], (job_id, "user-1"))

    def test_non_admin_cannot_promote_via_api(self):
        identity = model_registry.Identity("user-1", "tenant-1", False)
        with (
            patch.object(model_registry, "authenticate", return_value=identity),
        ):
            response = self.client.post(f"/api/models/{uuid4()}/promote")
        self.assertEqual(response.status_code, 403)

    def test_local_sync_activates_verified_versioned_artifact(self):
        row = {
            "id": uuid4(), "module": "upstream", "target": "Titer",
            "algorithm": "ridge", "version": 4, "schema_version": 1,
        }
        args = SimpleNamespace(
            module="upstream", version="latest", target=None, algorithm=None,
            cache_dir=None,
        )
        with tempfile.TemporaryDirectory() as cache:
            args.cache_dir = cache
            with (
                patch.object(sync_models, "resolve_models", return_value=[row]),
                patch.object(model_registry, "validate_model_artifact"),
                patch.object(model_registry, "download_artifact", return_value=b"trusted"),
            ):
                self.assertEqual(sync_models.sync(args), 0)
            pointer = json.loads((Path(cache) / "active.json").read_text())
            entry = pointer["upstream"]["Titer:ridge"]
            model_path = Path(cache) / entry["path"]
            self.assertEqual(model_path.read_bytes(), b"trusted")
            self.assertEqual(entry["version"], 4)
            self.assertEqual(entry["checksum"], model_registry.sha256(b"trusted"))

    def test_failed_local_sync_keeps_existing_pointer(self):
        row = {
            "id": uuid4(), "module": "upstream", "target": "Titer",
            "algorithm": "ridge", "version": 4, "schema_version": 1,
        }
        args = SimpleNamespace(
            module="upstream", version="latest", target=None, algorithm=None,
            cache_dir=None,
        )
        with tempfile.TemporaryDirectory() as cache:
            args.cache_dir = cache
            pointer_path = Path(cache) / "active.json"
            original = {"upstream": {"Titer:ridge": {"model_id": "old"}}}
            pointer_path.write_text(json.dumps(original))
            with (
                patch.object(sync_models, "resolve_models", return_value=[row]),
                patch.object(
                    model_registry, "validate_model_artifact",
                    side_effect=ValueError("incompatible features"),
                ),
            ):
                with self.assertRaisesRegex(ValueError, "incompatible"):
                    sync_models.sync(args)
            self.assertEqual(json.loads(pointer_path.read_text()), original)


if __name__ == "__main__":
    unittest.main()
