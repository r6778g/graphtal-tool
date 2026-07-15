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
        data = request.get_json()
        target = data.get("target")
        file_data = data.get("file_data", {})
        model_type = data.get("model", "ridge")

        if not file_data:
            return jsonify({"error": "No file data provided"}), 400

        metadata = predict.predictor.get_metadata()
        input_columns = metadata.get("inputs", [])

        if not input_columns:
            return jsonify({"error": "No input columns configured"}), 400

        predictions = []
        num_rows = len(file_data.get(input_columns[0], []))

        for row_index in range(num_rows):
            features = {}
            for col in input_columns:
                if col in file_data and row_index < len(file_data[col]):
                    features[col] = file_data[col][row_index]

            result = predict.predictor.predict(target, features, model_type=model_type)

            if "error" not in result:
                predictions.append({
                    "row": row_index + 1,
                    "prediction": result["prediction"],
                    "unit": result["unit"],
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


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
