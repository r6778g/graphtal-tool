import joblib
import numpy as np
import json
import os

class Predictor:
    def __init__(self):
        self.models = {}
        self.scalers = {}
        self.columns_config = None
        self.load_models()
    
    def load_models(self):
        """Load trained models and configuration."""
        try:
            # Load column configuration
            with open('model/columns.json', 'r') as f:
                self.columns_config = json.load(f)
            
            # Load default model and scaler
            if os.path.exists('model/model.pkl'):
                self.default_model = joblib.load('model/model.pkl')
                self.default_scaler = joblib.load('model/scaler.pkl')
            
            # Load all available models
            for output in self.columns_config['outputs']:
                model_path = f'model/{output.lower()}_model.pkl'
                scaler_path = f'model/{output.lower()}_scaler.pkl'
                
                if os.path.exists(model_path) and os.path.exists(scaler_path):
                    self.models[output] = joblib.load(model_path)
                    self.scalers[output] = joblib.load(scaler_path)
            
            print(f"Loaded {len(self.models)} models")
        except Exception as e:
            print(f"Error loading models: {e}")
    
    def predict(self, target: str, features: dict) -> dict:
        """
        Make prediction for a specific target.
        
        Args:
            target: The output column to predict
            features: Dictionary of input features
        
        Returns:
            Dictionary with prediction and metadata
        """
        try:
            # Get model and scaler for target
            if target in self.models:
                model = self.models[target]
                scaler = self.scalers[target]
            else:
                # Fall back to default model
                model = self.default_model
                scaler = self.default_scaler
            
            # Prepare features in correct order
            input_columns = self.columns_config['inputs']
            feature_values = [features.get(col, 0) for col in input_columns]
            
            # Scale features
            features_scaled = scaler.transform([feature_values])
            
            # Make prediction
            prediction = model.predict(features_scaled)[0]
            
            # Calculate feature importance (coefficients)
            importance = dict(zip(input_columns, np.abs(model.coef_)))
            
            return {
                "prediction": float(prediction),
                "unit": "mg/L" if target == "Titer" else "",
                "confidence": 0.85,  # Placeholder - should be calculated from model
                "feature_importance": importance
            }
        
        except Exception as e:
            print(f"Prediction error: {e}")
            return {
                "prediction": 0,
                "unit": "",
                "confidence": 0,
                "feature_importance": {},
                "error": str(e)
            }
    
    def get_metadata(self) -> dict:
        """Get metadata about available inputs, outputs, and visualizations."""
        if self.columns_config:
            return self.columns_config
        else:
            return {
                "inputs": [],
                "outputs": [],
                "visualizations": []
            }
    
    def get_feature_importance(self, target: str) -> list:
        """Get feature importance for a specific target."""
        if target in self.models:
            model = self.models[target]
            input_columns = self.columns_config['inputs']
            importance = list(zip(input_columns, np.abs(model.coef_)))
            # Sort by importance
            importance.sort(key=lambda x: x[1], reverse=True)
            return [{"feature": k, "importance": float(v)} for k, v in importance]
        return []

# Global predictor instance
predictor = Predictor()
