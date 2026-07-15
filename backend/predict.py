import joblib
import numpy as np
import json
import os

SUPPORTED_MODELS = ['ridge', 'lasso', 'svm', 'random_forest']
DEFAULT_MODEL = 'ridge'


class Predictor:
    def __init__(self):
        self.models = {}   # {model_type: {target: model}}
        self.scalers = {}  # {model_type: {target: scaler}}
        self.columns_config = None
        self.load_models()

    def load_models(self):
        """Load all trained models and configuration."""
        try:
            with open('model/columns.json', 'r') as f:
                self.columns_config = json.load(f)
        except Exception as e:
            print(f"Error loading columns config: {e}")
            self.columns_config = {"inputs": [], "outputs": []}

        outputs = self.columns_config.get('outputs', [])

        for model_type in SUPPORTED_MODELS:
            self.models[model_type] = {}
            self.scalers[model_type] = {}

            for output in outputs:
                model_path = f'model/{model_type}/{output.lower()}_model.pkl'
                scaler_path = f'model/{model_type}/{output.lower()}_scaler.pkl'

                if os.path.exists(model_path) and os.path.exists(scaler_path):
                    self.models[model_type][output] = joblib.load(model_path)
                    self.scalers[model_type][output] = joblib.load(scaler_path)

            # Fallback: load legacy flat models for the 'ridge' type
            if model_type == DEFAULT_MODEL and not self.models[model_type]:
                for output in outputs:
                    flat_model = f'model/{output.lower()}_model.pkl'
                    flat_scaler = f'model/{output.lower()}_scaler.pkl'
                    if os.path.exists(flat_model) and os.path.exists(flat_scaler):
                        self.models[model_type][output] = joblib.load(flat_model)
                        self.scalers[model_type][output] = joblib.load(flat_scaler)

        total = sum(len(v) for v in self.models.values())
        print(f"Loaded {total} model/target combinations across {len(SUPPORTED_MODELS)} model types")

    def _get_model_and_scaler(self, model_type: str, target: str):
        """Return (model, scaler) for the given type and target, with fallbacks."""
        mt = model_type if model_type in SUPPORTED_MODELS else DEFAULT_MODEL

        # Try requested type first
        if target in self.models.get(mt, {}):
            return self.models[mt][target], self.scalers[mt][target]

        # Fallback to ridge
        if target in self.models.get(DEFAULT_MODEL, {}):
            print(f"Warning: {mt} model not found for {target}, falling back to {DEFAULT_MODEL}")
            return self.models[DEFAULT_MODEL][target], self.scalers[DEFAULT_MODEL][target]

        # Fallback to any available model for this target
        for fallback_type in SUPPORTED_MODELS:
            if target in self.models.get(fallback_type, {}):
                print(f"Warning: falling back to {fallback_type} for {target}")
                return self.models[fallback_type][target], self.scalers[fallback_type][target]

        return None, None

    def predict(self, target: str, features: dict, model_type: str = DEFAULT_MODEL) -> dict:
        """Make prediction for a specific target using the selected model type."""
        try:
            model, scaler = self._get_model_and_scaler(model_type, target)
            if model is None:
                return {"prediction": 0, "unit": "", "confidence": 0,
                        "feature_importance": {}, "error": f"No model available for {target}"}

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

            return {
                "prediction": float(prediction),
                "unit": "mg/L" if target == "Titer" else "",
                "confidence": 0.85,
                "feature_importance": importance,
                "model_type": model_type
            }

        except Exception as e:
            print(f"Prediction error: {e}")
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


# Global predictor instance
predictor = Predictor()
