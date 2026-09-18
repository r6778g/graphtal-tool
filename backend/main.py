from flask import Flask, request, jsonify
from flask_cors import CORS
import predict

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


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
