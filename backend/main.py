from flask import Flask, request, jsonify
from flask_cors import CORS
import numpy as np
import predict
import predict_formulation
import model_registry as registry
import os
from uuid import UUID, uuid4

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = registry.ARTIFACT_MAX_BYTES
allowed_origins = [
    origin.strip()
    for origin in os.getenv(
        "CORS_ALLOWED_ORIGINS",
        "https://graphtal-tool.vercel.app,http://localhost:3000",
    ).split(",")
    if origin.strip()
]
CORS(app, resources={r"/*": {"origins": allowed_origins}})


def _identity_or_response():
    try:
        return registry.authenticate(), None
    except PermissionError as exc:
        return None, (jsonify({"error": str(exc)}), 401)
    except RuntimeError as exc:
        return None, (jsonify({"error": str(exc)}), 503)


def _registry_error(exc):
    if isinstance(exc, PermissionError):
        return jsonify({"error": str(exc)}), 403
    if isinstance(exc, LookupError):
        return jsonify({"error": str(exc)}), 404
    if isinstance(exc, ValueError):
        return jsonify({"error": str(exc)}), 400
    app.logger.exception("Model registry operation failed", exc_info=exc)
    return jsonify({"error": "Model registry operation failed"}), 503


@app.errorhandler(413)
def upload_too_large(_error):
    return jsonify({"error": "Upload exceeds the 100 MB limit"}), 413


@app.route("/api/datasets/upload", methods=["POST"])
def upload_dataset():
    identity, error = _identity_or_response()
    if error:
        return error
    upload = request.files.get("file")
    module = request.form.get("module", "")
    if not upload or not upload.filename:
        return jsonify({"error": "A CSV or Excel file is required"}), 400
    if module not in registry.SUPPORTED_MODULES:
        return jsonify({"error": "module must be upstream or formulation"}), 400

    extension = upload.filename.rsplit(".", 1)[-1].lower()
    if extension not in {"csv", "xls", "xlsx"}:
        return jsonify({"error": "Only CSV, XLS, and XLSX files are supported"}), 400
    raw = upload.read(registry.ARTIFACT_MAX_BYTES + 1)
    if not raw or len(raw) > registry.ARTIFACT_MAX_BYTES:
        return jsonify({"error": "Dataset is empty or exceeds the 100 MB limit"}), 400

    try:
        import csv
        import io
        import zipfile
        import pandas as pd

        max_rows = max(8, int(os.getenv("MAX_TRAINING_ROWS", "100000")))
        try:
            if extension == "csv":
                with io.TextIOWrapper(
                    io.BytesIO(raw), encoding="utf-8-sig", newline=""
                ) as csv_file:
                    reader = csv.reader(csv_file, strict=True)
                    next(reader, None)
                    for row_count, _row in enumerate(reader, start=1):
                        if row_count > max_rows:
                            return jsonify({
                                "error": f"Dataset exceeds the {max_rows} row training limit"
                            }), 413
                frame = pd.read_csv(io.BytesIO(raw), nrows=max_rows + 1)
            else:
                if extension == "xlsx":
                    with zipfile.ZipFile(io.BytesIO(raw)) as workbook:
                        expanded_size = sum(
                            item.file_size for item in workbook.infolist()
                        )
                    max_expanded_size = int(os.getenv(
                        "MAX_EXCEL_UNCOMPRESSED_BYTES", str(256 * 1024 * 1024)
                    ))
                    if expanded_size > max_expanded_size:
                        return jsonify({
                            "error": "Expanded Excel workbook exceeds the configured size limit"
                        }), 413
                frame = pd.read_excel(
                    io.BytesIO(raw), engine="xlrd" if extension == "xls" else "openpyxl"
                )
        except Exception:
            return jsonify({"error": "Unable to parse the uploaded CSV or Excel file"}), 400
        data_format = extension
        if len(frame) > max_rows:
            return jsonify({"error": f"Dataset exceeds the {max_rows} row training limit"}), 413
        schema = registry.expected_schema(module)
        required_columns = schema["inputs"] + schema["outputs"]
        missing = [column for column in required_columns if column not in frame.columns]
        if missing:
            return jsonify({"error": "Missing required columns", "columns": missing}), 400
        normalized = frame[required_columns].copy()
        for column in required_columns:
            converted = pd.to_numeric(normalized[column], errors="coerce")
            invalid = converted.isna() & normalized[column].notna()
            if invalid.any() or converted.isna().any() or not np.isfinite(converted).all():
                return jsonify({
                    "error": "Required columns must contain complete numeric values",
                    "column": column,
                }), 400
            normalized[column] = converted
        duplicate_rows = int(normalized.duplicated().sum())
        normalized = normalized.drop_duplicates()
        if normalized.empty:
            return jsonify({"error": "Dataset has no complete unique records"}), 400
        dataset = registry.store_dataset(
            identity.user_id, identity.tenant_id, module, raw, len(normalized),
            list(frame.columns), upload.filename, data_format,
        )
        return jsonify({
            "dataset": registry.serialize_row(dataset),
            "duplicate_rows_removed": duplicate_rows,
            "validated_rows": len(normalized),
        }), 201
    except (ValueError, RuntimeError) as exc:
        return _registry_error(exc)
    except Exception:
        app.logger.exception("Dataset upload failed")
        return jsonify({"error": "Dataset could not be persisted"}), 503


@app.route("/api/training/jobs", methods=["POST"])
def submit_training_job():
    identity, error = _identity_or_response()
    if error:
        return error
    payload = request.get_json(silent=True) or {}
    try:
        dataset_id = UUID(str(payload.get("dataset_id", "")))
    except ValueError:
        return jsonify({"error": "dataset_id must be a UUID"}), 400
    job_id = uuid4()
    idempotency_key = request.headers.get("Idempotency-Key") or payload.get("idempotency_key")
    if idempotency_key is None:
        return jsonify({"error": "Idempotency-Key is required"}), 400
    if (
        not isinstance(idempotency_key, str) or len(idempotency_key) > 200
    ):
        return jsonify({"error": "Idempotency-Key must be at most 200 characters"}), 400
    try:
        job = registry.create_training_job(
            job_id=job_id, identity=identity, module=payload.get("module", ""),
            dataset_id=dataset_id, idempotency_key=idempotency_key,
        )
        if job.get("created"):
            from model_worker import Retry, training_queue
            try:
                training_queue().enqueue(
                    "model_worker.run_training_job", str(job["id"]),
                    job_id=str(job["id"]),
                    job_timeout=int(os.getenv("TRAINING_TIMEOUT_SECONDS", "1800")),
                    retry=Retry(max=2),
                )
            except Exception as queue_error:
                with registry.connect() as connection:
                    connection.execute(
                        "UPDATE training_jobs SET status = 'failed', progress = 100, "
                        "message = %s, updated_at = now() WHERE id = %s",
                        (f"Unable to queue training job: {queue_error}"[:500], job["id"]),
                    )
                return jsonify({"error": "Training queue is unavailable"}), 503
        return jsonify({"job": registry.serialize_row(job)}), 202
    except Exception as exc:
        return _registry_error(exc)


@app.route("/api/training/jobs")
def list_training_jobs():
    identity, error = _identity_or_response()
    if error:
        return error
    try:
        with registry.connect() as connection:
            rows = connection.execute(
                "SELECT id, module, dataset_id, status, progress, message, "
                "candidate_ids, created_at, updated_at FROM training_jobs "
                "WHERE owner_id = %s ORDER BY created_at DESC LIMIT 100",
                (identity.user_id,),
            ).fetchall()
        return jsonify({"jobs": registry.serialize_row(rows)})
    except Exception as exc:
        return _registry_error(exc)


@app.route("/api/training/jobs/<job_id>")
def get_training_job(job_id):
    identity, error = _identity_or_response()
    if error:
        return error
    try:
        parsed_id = UUID(job_id)
    except ValueError:
        return jsonify({"error": "job_id must be a UUID"}), 400
    try:
        with registry.connect() as connection:
            row = connection.execute(
                "SELECT id, module, dataset_id, status, progress, message, "
                "candidate_ids, created_at, updated_at FROM training_jobs "
                "WHERE id = %s AND owner_id = %s",
                (parsed_id, identity.user_id),
            ).fetchone()
        if not row:
            return jsonify({"error": "Training job not found"}), 404
        return jsonify({"job": registry.serialize_row(row)})
    except Exception as exc:
        return _registry_error(exc)


@app.route("/api/training/jobs/<job_id>/retry", methods=["POST"])
def retry_training_job(job_id):
    identity, error = _identity_or_response()
    if error:
        return error
    try:
        parsed_id = UUID(job_id)
    except ValueError:
        return jsonify({"error": "job_id must be a UUID"}), 400
    try:
        with registry.connect() as connection:
            row = connection.execute(
                "UPDATE training_jobs SET status = 'queued', progress = 0, "
                "message = 'Retry queued', updated_at = now() "
                "WHERE id = %s AND owner_id = %s AND status = 'failed' "
                "RETURNING id",
                (parsed_id, identity.user_id),
            ).fetchone()
        if not row:
            return jsonify({"error": "Failed training job not found"}), 404
        from model_worker import Retry, training_queue
        training_queue().enqueue(
            "model_worker.run_training_job", str(parsed_id), job_id=str(uuid4()),
            job_timeout=int(os.getenv("TRAINING_TIMEOUT_SECONDS", "1800")),
            retry=Retry(max=2),
        )
        return jsonify({"job_id": str(parsed_id), "status": "queued"}), 202
    except Exception as exc:
        try:
            with registry.connect() as connection:
                connection.execute(
                    "UPDATE training_jobs SET status = 'failed', progress = 100, "
                    "message = 'Unable to queue retry', updated_at = now() WHERE id = %s",
                    (UUID(job_id),),
                )
        except Exception:
            app.logger.exception("Could not record training retry enqueue failure")
        return _registry_error(exc)


@app.route("/api/models")
def get_models():
    identity, error = _identity_or_response()
    if error:
        return error
    module = request.args.get("module")
    if module and module not in registry.SUPPORTED_MODULES:
        return jsonify({"error": "module must be upstream or formulation"}), 400
    try:
        return jsonify({"models": registry.serialize_row(
            registry.list_models(identity, module)
        )})
    except Exception as exc:
        return _registry_error(exc)


@app.route("/api/models/active")
def get_active_models():
    identity, error = _identity_or_response()
    if error:
        return error
    module = request.args.get("module")
    if module and module not in registry.SUPPORTED_MODULES:
        return jsonify({"error": "module must be upstream or formulation"}), 400
    try:
        query = (
            "SELECT m.id, m.module, m.target, m.algorithm, m.version, "
            "d.version AS dataset_version, m.metrics, "
            "m.activated_at FROM active_models a JOIN model_versions m ON m.id = a.model_id "
            "JOIN datasets d ON d.id = m.dataset_id "
            "WHERE (%s::text IS NULL OR m.module = %s) "
            "ORDER BY m.module, m.target, m.algorithm"
        )
        with registry.connect() as connection:
            rows = connection.execute(query, (module, module)).fetchall()
        return jsonify({"models": registry.serialize_row(rows)})
    except Exception as exc:
        return _registry_error(exc)


@app.route("/api/models/<model_id>")
def get_model(model_id):
    identity, error = _identity_or_response()
    if error:
        return error
    try:
        parsed_id = UUID(model_id)
        with registry.connect() as connection:
            row = connection.execute(
                "SELECT m.id, m.module, m.target, m.algorithm, m.version, m.dataset_id, "
                "d.version AS dataset_version, m.metrics, m.status, m.created_at, "
                "m.approved_at, m.activated_at FROM model_versions m "
                "JOIN datasets d ON d.id = m.dataset_id "
                "WHERE m.id = %s AND m.tenant_id = %s",
                (parsed_id, identity.tenant_id),
            ).fetchone()
        if not row:
            return jsonify({"error": "Model version not found"}), 404
        return jsonify({"model": registry.serialize_row(row)})
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:
        return _registry_error(exc)


@app.route("/api/models/<model_id>/promote", methods=["POST"])
def promote_model(model_id):
    identity, error = _identity_or_response()
    if error:
        return error
    try:
        result = registry.approve_and_promote(UUID(model_id), identity)
        refresh = {
            "upstream": predict.predictor.refresh_active(force=True),
            "formulation": predict_formulation.formulation_predictor.refresh_active(force=True),
        }
        return jsonify({
            "model": registry.serialize_row(result), "status": "active", "refresh": refresh
        })
    except ValueError as exc:
        return _registry_error(exc)
    except Exception as exc:
        return _registry_error(exc)


@app.route("/api/models/<model_id>/rollback", methods=["POST"])
def rollback_model(model_id):
    identity, error = _identity_or_response()
    if error:
        return error
    try:
        result = registry.rollback_model(UUID(model_id), identity)
        refresh = {
            "upstream": predict.predictor.refresh_active(force=True),
            "formulation": predict_formulation.formulation_predictor.refresh_active(force=True),
        }
        return jsonify({
            "model": registry.serialize_row(result), "status": "active", "refresh": refresh
        })
    except Exception as exc:
        return _registry_error(exc)


@app.route("/api/models/refresh", methods=["POST"])
def refresh_models():
    identity, error = _identity_or_response()
    if error:
        return error
    if not identity.is_admin:
        return jsonify({"error": "Administrator role is required"}), 403
    try:
        return jsonify({
            "upstream": predict.predictor.refresh_active(force=True),
            "formulation": predict_formulation.formulation_predictor.refresh_active(force=True),
        })
    except Exception as exc:
        return _registry_error(exc)


@app.route("/")
def read_root():
    return jsonify({"message": "Graphtal Tool ML Prediction API", "status": "running"})


@app.route("/metadata")
def get_metadata():
    """Get available inputs, outputs, model types, and visualizations."""
    try:
        metadata = predict.predictor.get_metadata()
        return jsonify(metadata)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/predict", methods=["POST"])
def predict_endpoint():
    """Make a single prediction for given target, features, and model type."""
    try:
        data = request.get_json()
        target = data.get("target")
        features = data.get("features", {})
        model_type = data.get("model", "ridge")

        result = predict.predictor.predict(target, features, model_type=model_type)

        if "error" in result:
            return jsonify({"error": result["error"]}), 500

        return jsonify({
            "prediction": result["prediction"],
            "unit": result["unit"],
            "confidence": result["confidence"],
            "feature_importance": result["feature_importance"],
            "model_type": result.get("model_type", model_type)
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/predict-batch", methods=["POST"])
def predict_batch_endpoint():
    """Make predictions for all rows in uploaded data using the selected model."""
    try:
        data = request.get_json() or {}
        target = data.get("target", "Titer")
        file_data = data.get("file_data", {})
        model_type = data.get("model", "ridge")

        if not file_data:
            return jsonify({"error": "No file data provided"}), 400

        metadata = predict.predictor.get_metadata()
        input_columns = metadata.get("inputs", [])

        if not input_columns:
            # Fallback to keys present in file_data if metadata inputs are empty
            input_columns = list(file_data.keys())

        # Build normalized dictionary for flexible matching (case-insensitive, trimmed)
        norm_map = {str(k).strip().lower(): v for k, v in file_data.items()}

        # Compute max row count across provided columns
        num_rows = max([len(v) for v in file_data.values() if isinstance(v, list)], default=0)

        if num_rows == 0:
            return jsonify({"error": "No data rows found in uploaded file"}), 400

        predictions = []

        for row_index in range(num_rows):
            features = {}
            for col in input_columns:
                norm_key = str(col).strip().lower()
                val_list = file_data.get(col) or norm_map.get(norm_key, [])
                
                if isinstance(val_list, list) and row_index < len(val_list):
                    val = val_list[row_index]
                    try:
                        features[col] = float(val) if val is not None else 0.0
                    except (ValueError, TypeError):
                        features[col] = 0.0
                else:
                    features[col] = 0.0

            result = predict.predictor.predict(target, features, model_type=model_type)

            if "error" not in result or result.get("prediction") is not None:
                predictions.append({
                    "row": row_index + 1,
                    "prediction": result.get("prediction", 0.0),
                    "unit": result.get("unit", ""),
                    "confidence": result.get("confidence", 0.85),
                    "features": features
                })

        feature_importance = predict.predictor.get_feature_importance(target, model_type=model_type)

        return jsonify({
            "target": target,
            "model_type": model_type,
            "predictions": predictions,
            "feature_importance": feature_importance,
            "total_rows": len(predictions)
        })
    except Exception as e:
        print(f"Error in predict_batch_endpoint: {e}")
        return jsonify({"error": str(e)}), 500



@app.route("/feature-importance/<target>")
def get_feature_importance(target):
    """Get feature importance for a specific target and optional model type."""
    try:
        model_type = request.args.get("model", "ridge")
        importance = predict.predictor.get_feature_importance(target, model_type=model_type)
        return jsonify({"target": target, "model_type": model_type, "importance": importance})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/recommend-model", methods=["POST"])
def recommend_model():
    """Recommend the best model based on dataset analysis."""
    try:
        data = request.get_json()
        target = data.get("target")
        file_data = data.get("file_data", {})

        if not file_data:
            return jsonify({"error": "No file data provided"}), 400

        # Simple model recommendation logic based on dataset characteristics
        num_rows = len(file_data.get(list(file_data.keys())[0], []))
        num_features = len(file_data)

        recommendation = {
            "recommended_model": "random_forest",
            "reason": "Random Forest is recommended for this dataset due to its ability to handle non-linear relationships and feature interactions.",
            "alternatives": [
                {
                    "model": "ridge",
                    "reason": "Good for linear relationships with many features"
                },
                {
                    "model": "lasso",
                    "reason": "Good for feature selection with sparse data"
                },
                {
                    "model": "elastic_net",
                    "reason": "Balanced approach for mixed feature importance"
                }
            ],
            "dataset_info": {
                "num_rows": num_rows,
                "num_features": num_features,
                "target": target
            }
        }

        # Adjust recommendation based on dataset size
        if num_rows < 50:
            recommendation["recommended_model"] = "ridge"
            recommendation["reason"] = "Ridge regression is recommended for smaller datasets to avoid overfitting."
        elif num_features > 15:
            recommendation["recommended_model"] = "lasso"
            recommendation["reason"] = "Lasso is recommended for high-dimensional data to perform feature selection."

        return jsonify(recommendation)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/retrain", methods=["POST"])
def retrain_models():
    return jsonify({
        "error": "Synchronous in-place retraining is disabled. Upload a dataset and submit /api/training/jobs."
    }), 410


@app.route("/training-status")
def get_training_status():
    """Get information about current model training status."""
    try:
        import os
        import json
        from datetime import datetime
        
        metadata_path = os.path.join("model", "training_metadata.json")
        
        if os.path.exists(metadata_path):
            with open(metadata_path, "r") as f:
                metadata = json.load(f)
        else:
            # Return default status if no metadata exists
            metadata = {
                "last_trained": "Unknown",
                "total_samples": 0,
                "new_samples": 0,
                "mode": "initial",
                "columns": []
            }
        
        # Check if models exist
        model_dir = "model"
        model_files = []
        if os.path.exists(model_dir):
            model_files = [f for f in os.listdir(model_dir) if f.endswith('_model.pkl')]
        
        return jsonify({
            "status": "trained" if model_files else "not_trained",
            "last_trained": metadata.get("last_trained", "Unknown"),
            "total_samples": metadata.get("total_samples", 0),
            "model_count": len(model_files),
            "metadata": metadata
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── Formulation Endpoints ────────────────────────────────────────────────────────

@app.route("/formulation-metadata")
def get_formulation_metadata():
    """Get available formulation inputs, outputs, model types, and visualizations."""
    try:
        metadata = predict_formulation.formulation_predictor.get_metadata()
        return jsonify(metadata)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/formulation-predict", methods=["POST"])
def formulation_predict_endpoint():
    """Make a single formulation prediction for given target, features, and model type."""
    try:
        data = request.get_json()
        target = data.get("target")
        features = data.get("features", {})
        model_type = data.get("model", "ridge")

        result = predict_formulation.formulation_predictor.predict(target, features, model_type=model_type)

        if "error" in result:
            return jsonify({"error": result["error"]}), 500

        return jsonify({
            "prediction": result["prediction"],
            "unit": result["unit"],
            "confidence": result["confidence"],
            "feature_importance": result["feature_importance"],
            "model_type": result.get("model_type", model_type)
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/formulation-predict-batch", methods=["POST"])
def formulation_predict_batch_endpoint():
    """Make predictions for all rows in uploaded formulation data using the selected model."""
    try:
        data = request.get_json() or {}
        target = data.get("target", "Particle Size (nm)")
        file_data = data.get("file_data", {})
        model_type = data.get("model", "ridge")

        if not file_data:
            return jsonify({"error": "No file data provided"}), 400

        metadata = predict_formulation.formulation_predictor.get_metadata()
        input_columns = metadata.get("inputs", [])

        if not input_columns:
            # Fallback to keys present in file_data if metadata inputs are empty
            input_columns = list(file_data.keys())

        # Build normalized dictionary for flexible matching (case-insensitive, trimmed)
        norm_map = {str(k).strip().lower(): v for k, v in file_data.items()}

        # Compute max row count across provided columns
        num_rows = max([len(v) for v in file_data.values() if isinstance(v, list)], default=0)

        if num_rows == 0:
            return jsonify({"error": "No data rows found in uploaded file"}), 400

        predictions = []

        for row_index in range(num_rows):
            features = {}
            for col in input_columns:
                norm_key = str(col).strip().lower()
                val_list = file_data.get(col) or norm_map.get(norm_key, [])
                
                if isinstance(val_list, list) and row_index < len(val_list):
                    val = val_list[row_index]
                    try:
                        features[col] = float(val) if val is not None else 0.0
                    except (ValueError, TypeError):
                        features[col] = 0.0
                else:
                    features[col] = 0.0

            result = predict_formulation.formulation_predictor.predict(target, features, model_type=model_type)

            if "error" not in result or result.get("prediction") is not None:
                predictions.append({
                    "row": row_index + 1,
                    "prediction": result.get("prediction", 0.0),
                    "unit": result.get("unit", ""),
                    "confidence": result.get("confidence", 0.85),
                    "features": features
                })

        feature_importance = predict_formulation.formulation_predictor.get_feature_importance(target, model_type=model_type)

        return jsonify({
            "target": target,
            "model_type": model_type,
            "predictions": predictions,
            "feature_importance": feature_importance,
            "total_rows": len(predictions)
        })
    except Exception as e:
        print(f"Error in formulation_predict_batch_endpoint: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/formulation-feature-importance/<target>")
def get_formulation_feature_importance(target):
    """Get feature importance for a specific formulation target and optional model type."""
    try:
        model_type = request.args.get("model", "ridge")
        importance = predict_formulation.formulation_predictor.get_feature_importance(target, model_type=model_type)
        return jsonify({"target": target, "model_type": model_type, "importance": importance})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/formulation-retrain", methods=["POST"])
def retrain_formulation_models():
    return jsonify({
        "error": "Synchronous in-place retraining is disabled. Upload a dataset and submit /api/training/jobs."
    }), 410


@app.route("/formulation-training-status")
def get_formulation_training_status():
    """Get information about current formulation model training status."""
    try:
        import os
        import json
        from datetime import datetime
        
        formulation_metadata_path = os.path.join("model", "formulation", "training_metadata.json")
        
        if os.path.exists(formulation_metadata_path):
            with open(formulation_metadata_path, "r") as f:
                metadata = json.load(f)
        else:
            # Return default status if no metadata exists
            metadata = {
                "last_trained": "Unknown",
                "total_samples": 0,
                "new_samples": 0,
                "mode": "initial",
                "columns": []
            }
        
        # Check if formulation models exist
        formulation_model_dir = "model/formulation"
        model_files = []
        if os.path.exists(formulation_model_dir):
            # Count all .pkl files in subdirectories
            for root, dirs, files in os.walk(formulation_model_dir):
                model_files.extend([f for f in files if f.endswith('_model.pkl')])
        
        return jsonify({
            "status": "trained" if model_files else "not_trained",
            "last_trained": metadata.get("last_trained", "Unknown"),
            "total_samples": metadata.get("total_samples", 0),
            "model_count": len(model_files),
            "metadata": metadata
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
