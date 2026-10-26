import joblib
import numpy as np
import json
import logging
import os
from pathlib import Path
import threading
import time
import model_registry

SUPPORTED_MODELS = ['ridge', 'lasso', 'svm', 'random_forest']
DEFAULT_MODEL = 'ridge'


class FormulationPredictor:
    def __init__(self):
        self.models = {}   # {model_type: {target: model}}
        self.scalers = {}  # {model_type: {target: scaler}}
        self.columns_config = None
        self._lock = threading.RLock()
        self._sync_lock = threading.Lock()
        self._registry_models = {}
        self._registry_versions = {}
        self._last_registry_check = 0.0
        self.load_models()

    def load_models(self):
        """Load all trained formulation models and configuration."""
        backend_root = Path(__file__).resolve().parent
        base_dir = next(
            (
                str(path) for path in (
                    backend_root / "model" / "formulation",
                    backend_root.parent / "model" / "formulation",
                )
                if (path / "columns.json").exists()
            ),
            "model/formulation" if os.path.exists("model/formulation/columns.json")
            else "backend/model/formulation",
        )
        columns_file = os.path.join(base_dir, 'columns.json')

        try:
            with open(columns_file, 'r') as f:
                self.columns_config = json.load(f)
        except Exception as e:
            print(f"Error loading formulation columns config from {columns_file}: {e}")
            self.columns_config = {"inputs": [], "outputs": []}

        outputs = self.columns_config.get('outputs', [])

        for model_type in SUPPORTED_MODELS:
            self.models[model_type] = {}
            self.scalers[model_type] = {}

            for output in outputs:
                # Sanitize target name for file system
                safe_target_name = output.lower().replace(" ", "_").replace("(", "").replace(")", "").replace("%", "pct").replace("/", "_")
                
                model_path = os.path.join(base_dir, model_type, f"{safe_target_name}_model.pkl")
                scaler_path = os.path.join(base_dir, model_type, f"{safe_target_name}_scaler.pkl")

                if os.path.exists(model_path) and os.path.exists(scaler_path):
                    self.models[model_type][output] = joblib.load(model_path)
                    self.scalers[model_type][output] = joblib.load(scaler_path)

            # Fallback: load legacy flat models for the 'ridge' type
            if model_type == DEFAULT_MODEL and not self.models[model_type]:
                for output in outputs:
                    safe_target_name = output.lower().replace(" ", "_").replace("(", "").replace(")", "").replace("%", "pct").replace("/", "_")
                    flat_model = os.path.join(base_dir, f"{safe_target_name}_model.pkl")
                    flat_scaler = os.path.join(base_dir, f"{safe_target_name}_scaler.pkl")
                    if os.path.exists(flat_model) and os.path.exists(flat_scaler):
                        self.models[model_type][output] = joblib.load(flat_model)
                        self.scalers[model_type][output] = joblib.load(flat_scaler)

        pinned = model_registry.load_pinned_local_models(
            "formulation", self.columns_config.get("inputs", [])
        )
        for algorithm, targets in pinned.items():
            self.models.setdefault(algorithm, {}).update(
                {target: pair[0] for target, pair in targets.items()}
            )
            self.scalers.setdefault(algorithm, {}).update(
                {target: pair[1] for target, pair in targets.items()}
            )
        self._fallback_models = {kind: dict(values) for kind, values in self.models.items()}
        self._fallback_scalers = {kind: dict(values) for kind, values in self.scalers.items()}
        total = sum(len(v) for v in self.models.values())
        print(f"Loaded {total} formulation model/target combinations across {len(SUPPORTED_MODELS)} model types from {base_dir}")

    def refresh_active(self, force: bool = False) -> dict:
        """Atomically overlay validated registry models over local fallback models."""
        if not model_registry.registry_configured():
            return {"status": "disabled"}
        interval = max(1, int(os.getenv("MODEL_REGISTRY_REFRESH_SECONDS", "30")))
        now = time.monotonic()
        with self._sync_lock:
            if not force and now - self._last_registry_check < interval:
                return {"status": "cached", "versions": self._registry_versions}
            try:
                active_models, versions = model_registry.load_active_models(
                    "formulation", self.columns_config.get("inputs", []),
                    self._registry_versions,
                )
                registry_models = {
                    kind: dict(targets) for kind, targets in self._registry_models.items()
                }
                for algorithm, targets in registry_models.items():
                    for target in list(targets):
                        if f"{target}:{algorithm}" not in versions:
                            del targets[target]
                for algorithm, targets in active_models.items():
                    registry_models.setdefault(algorithm, {}).update(targets)
                models = {kind: dict(values) for kind, values in self._fallback_models.items()}
                scalers = {kind: dict(values) for kind, values in self._fallback_scalers.items()}
                for algorithm, targets in registry_models.items():
                    models.setdefault(algorithm, {}).update(
                        {target: pair[0] for target, pair in targets.items()}
                    )
                    scalers.setdefault(algorithm, {}).update(
                        {target: pair[1] for target, pair in targets.items()}
                    )
                with self._lock:
                    self.models, self.scalers = models, scalers
                    self._registry_models = registry_models
                    self._registry_versions = versions
                self._last_registry_check = now
                return {"status": "refreshed", "versions": versions}
            except Exception as exc:
                self._last_registry_check = now
                logging.getLogger(__name__).warning(
                    "Formulation registry refresh failed; retaining the previous working models: %s",
                    exc,
                )
                return {"status": "failed", "error": str(exc)}


    def _get_model_and_scaler(self, model_type: str, target: str):
        """Return (model, scaler) for the given type and target, with fallbacks."""
        self.refresh_active()
        mt = model_type if model_type in SUPPORTED_MODELS else DEFAULT_MODEL
        with self._lock:
            models, scalers = self.models, self.scalers

        # Try requested type first
        if target in models.get(mt, {}):
            return models[mt][target], scalers[mt][target]

        # Fallback to ridge
        if target in models.get(DEFAULT_MODEL, {}):
            print(f"Warning: {mt} model not found for {target}, falling back to {DEFAULT_MODEL}")
            return models[DEFAULT_MODEL][target], scalers[DEFAULT_MODEL][target]

        # Fallback to any available model for this target
        for fallback_type in SUPPORTED_MODELS:
            if target in models.get(fallback_type, {}):
                print(f"Warning: falling back to {fallback_type} for {target}")
                return models[fallback_type][target], scalers[fallback_type][target]

        return None, None

    def predict(self, target: str, features: dict, model_type: str = DEFAULT_MODEL) -> dict:
        """Make prediction for a specific target using the selected model type."""
        try:
            model, scaler = self._get_model_and_scaler(model_type, target)
            if model is None:
                return {"prediction": 0, "unit": "", "confidence": 0,
                        "feature_importance": {}, "error": f"No formulation model available for {target}"}

            input_columns = self.columns_config['inputs']
            feature_values = [features.get(col, 0) for col in input_columns]
            features_scaled = scaler.transform([feature_values])
            prediction = model.predict(features_scaled)[0]

            # Feature importance
            importance = {}
            if hasattr(model, 'coef_'):
                importance = dict(zip(input_columns, np.abs(model.coef_)))
            elif hasattr(model, 'feature_importances_'):
                importance = dict(zip(input_columns, model.feature_importances_))

            # Determine unit based on target
            unit = ""
            if "Size" in target:
                unit = "nm"
            elif "Spreadability" in target:
                unit = "h"
            elif "Release" in target:
                unit = "%"
            elif "Viscocity" in target:
                unit = "cps"

            return {
                "prediction": float(prediction),
                "unit": unit,
                "confidence": 0.85,
                "feature_importance": importance,
                "model_type": model_type
            }

        except Exception as e:
            print(f"Formulation prediction error: {e}")
            return {"prediction": 0, "unit": "", "confidence": 0,
                    "feature_importance": {}, "error": str(e)}

    def get_metadata(self) -> dict:
        """Get metadata about available inputs, outputs, and model types."""
        meta = dict(self.columns_config) if self.columns_config else {}
        meta['model_types'] = SUPPORTED_MODELS
        return meta

    def get_feature_importance(self, target: str, model_type: str = DEFAULT_MODEL) -> list:
        """Get feature importance for a specific target and model type."""
        model, _ = self._get_model_and_scaler(model_type, target)
        if model is None:
            return []

        input_columns = self.columns_config['inputs']
        if hasattr(model, 'coef_'):
            importance = list(zip(input_columns, np.abs(model.coef_)))
        elif hasattr(model, 'feature_importances_'):
            importance = list(zip(input_columns, model.feature_importances_))
        else:
            return []

        importance.sort(key=lambda x: x[1], reverse=True)
        return [{"feature": k, "importance": float(v)} for k, v in importance]


# Global formulation predictor instance
formulation_predictor = FormulationPredictor()