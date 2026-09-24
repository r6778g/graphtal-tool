from flask import Flask, request, jsonify
from flask_cors import CORS
import predict
import predict_formulation

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})


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
    """Retrain all models with new data combined with existing training data."""
    try:
        import train
        import pandas as pd
        import os
        from datetime import datetime
        
        data = request.get_json()
        file_data = data.get("file_data", {})
        mode = data.get("mode", "append")  # 'append' or 'replace'
        
        if not file_data:
            return jsonify({"error": "No training data provided"}), 400
        
        # Convert file_data to DataFrame
        new_df = pd.DataFrame(file_data)
        
        # Create training_data directory if it doesn't exist
        training_dir = "training_data"
        os.makedirs(training_dir, exist_ok=True)
        
        # Save new data with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        new_data_path = os.path.join(training_dir, f"training_data_{timestamp}.csv")
        new_df.to_csv(new_data_path, index=False)
        
        # Determine which data to use for training
        if mode == "replace":
            # Use only the new data
            training_df = new_df
        else:
            # Append mode: combine with existing data
            existing_data_files = []
            
            # Check for existing training data files
            if os.path.exists(training_dir):
                existing_data_files = [
                    os.path.join(training_dir, f) 
                    for f in os.listdir(training_dir) 
                    if f.endswith('.csv')
                ]
            
            # Also check for original sample_data.csv
            if os.path.exists("sample_data.csv"):
                existing_data_files.append("sample_data.csv")
            
            # Load and combine all existing data
            all_dfs = [new_df]
            for file_path in existing_data_files:
                if file_path != new_data_path:  # Don't load the file we just saved
                    try:
                        existing_df = pd.read_csv(file_path)
                        all_dfs.append(existing_df)
                    except Exception as e:
                        print(f"Warning: Could not load {file_path}: {e}")
            
            # Combine all dataframes
            if len(all_dfs) > 1:
                training_df = pd.concat(all_dfs, ignore_index=True)
                # Remove duplicates if any
                training_df = training_df.drop_duplicates()
            else:
                training_df = new_df
        
        # Save combined training data
        combined_path = os.path.join(training_dir, "combined_training_data.csv")
        training_df.to_csv(combined_path, index=False)
        
        # Retrain models using the combined data
        print(f"Retraining models with {len(training_df)} total samples...")
        train.train_model(combined_path)
        
        # Reload predictor with new models
        predict.predictor.load_models()
        
        # Save training metadata
        metadata = {
            "last_trained": timestamp,
            "total_samples": len(training_df),
            "new_samples": len(new_df),
            "mode": mode,
            "columns": list(training_df.columns)
        }
        
        import json
        metadata_path = os.path.join("model", "training_metadata.json")
        with open(metadata_path, "w") as f:
            json.dump(metadata, f, indent=2)
        
        return jsonify({
            "message": "Models retrained successfully",
            "total_samples": len(training_df),
            "new_samples": len(new_df),
            "timestamp": timestamp,
            "mode": mode
        })
        
    except Exception as e:
        print(f"Error during retraining: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


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
    """Retrain all formulation models with new data combined with existing training data."""
    try:
        import train_formulation
        import pandas as pd
        import os
        from datetime import datetime
        
        data = request.get_json()
        file_data = data.get("file_data", {})
        mode = data.get("mode", "append")  # 'append' or 'replace'
        
        if not file_data:
            return jsonify({"error": "No training data provided"}), 400
        
        # Convert file_data to DataFrame
        new_df = pd.DataFrame(file_data)
        
        # Create formulation training data directory if it doesn't exist
        formulation_training_dir = "formulation_training_data"
        os.makedirs(formulation_training_dir, exist_ok=True)
        
        # Save new data with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        new_data_path = os.path.join(formulation_training_dir, f"formulation_training_data_{timestamp}.csv")
        new_df.to_csv(new_data_path, index=False)
        
        # Determine which data to use for training
        if mode == "replace":
            # Use only the new data
            training_df = new_df
        else:
            # Append mode: combine with existing data
            existing_data_files = []
            
            # Check for existing formulation training data files
            if os.path.exists(formulation_training_dir):
                existing_data_files = [
                    os.path.join(formulation_training_dir, f) 
                    for f in os.listdir(formulation_training_dir) 
                    if f.endswith('.csv')
                ]
            
            # Also check for original formulation_data.csv
            if os.path.exists("formulation_data.csv"):
                existing_data_files.append("formulation_data.csv")
            elif os.path.exists("backend/formulation_data.csv"):
                existing_data_files.append("backend/formulation_data.csv")
            
            # Load and combine all existing data
            all_dfs = [new_df]
            for file_path in existing_data_files:
                if file_path != new_data_path:  # Don't load the file we just saved
                    try:
                        existing_df = pd.read_csv(file_path)
                        all_dfs.append(existing_df)
                    except Exception as e:
                        print(f"Warning: Could not load {file_path}: {e}")
            
            # Combine all dataframes
            if len(all_dfs) > 1:
                training_df = pd.concat(all_dfs, ignore_index=True)
                # Remove duplicates if any
                training_df = training_df.drop_duplicates()
            else:
                training_df = new_df
        
        # Save combined training data
        combined_path = os.path.join(formulation_training_dir, "combined_formulation_training_data.csv")
        training_df.to_csv(combined_path, index=False)
        
        # Retrain formulation models using the combined data
        print(f"Retraining formulation models with {len(training_df)} total samples...")
        train_formulation.train_formulation_model(combined_path)
        
        # Reload predictor with new models
        predict_formulation.formulation_predictor.load_models()
        
        # Save training metadata
        metadata = {
            "last_trained": timestamp,
            "total_samples": len(training_df),
            "new_samples": len(new_df),
            "mode": mode,
            "columns": list(training_df.columns)
        }
        
        import json
        formulation_metadata_path = os.path.join("model", "formulation", "training_metadata.json")
        os.makedirs(os.path.dirname(formulation_metadata_path), exist_ok=True)
        with open(formulation_metadata_path, "w") as f:
            json.dump(metadata, f, indent=2)
        
        return jsonify({
            "message": "Formulation models retrained successfully",
            "total_samples": len(training_df),
            "new_samples": len(new_df),
            "timestamp": timestamp,
            "mode": mode
        })
        
    except Exception as e:
        print(f"Error during formulation retraining: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


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
