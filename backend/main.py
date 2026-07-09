from flask import Flask, request, jsonify
from flask_cors import CORS
import predict

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "http://localhost:3000"}})

@app.route("/")
def read_root():
    return jsonify({"message": "Intraclone ML Prediction API", "status": "running"})

@app.route("/metadata")
def get_metadata():
    """Get available inputs, outputs, and visualizations."""
    try:
        metadata = predict.predictor.get_metadata()
        return jsonify(metadata)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/predict", methods=["POST"])
def predict_endpoint():
    """Make prediction for given target and features."""
    try:
        data = request.get_json()
        target = data.get("target")
        features = data.get("features", {})
        
        result = predict.predictor.predict(target, features)
        
        if "error" in result:
            return jsonify({"error": result["error"]}), 500
        
        return jsonify({
            "prediction": result["prediction"],
            "unit": result["unit"],
            "confidence": result["confidence"],
            "feature_importance": result["feature_importance"]
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/predict-batch", methods=["POST"])
def predict_batch_endpoint():
    """Make predictions for all rows in uploaded data."""
    try:
        data = request.get_json()
        target = data.get("target")
        file_data = data.get("file_data", {})
        
        if not file_data:
            return jsonify({"error": "No file data provided"}), 400
        
        # Get input columns from metadata
        metadata = predict.predictor.get_metadata()
        input_columns = metadata.get("inputs", [])
        
        # Prepare predictions for all rows
        predictions = []
        num_rows = len(file_data.get(input_columns[0], []))
        
        for row_index in range(num_rows):
            # Extract features for this row
            features = {}
            for col in input_columns:
                if col in file_data and row_index < len(file_data[col]):
                    features[col] = file_data[col][row_index]
            
            # Make prediction
            result = predict.predictor.predict(target, features)
            
            if "error" not in result:
                predictions.append({
                    "row": row_index + 1,
                    "prediction": result["prediction"],
                    "unit": result["unit"],
                    "features": features
                })
        
        # Get feature importance
        feature_importance = predict.predictor.get_feature_importance(target)
        
        return jsonify({
            "target": target,
            "predictions": predictions,
            "feature_importance": feature_importance,
            "total_rows": len(predictions)
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/feature-importance/<target>")
def get_feature_importance(target):
    """Get feature importance for a specific target."""
    try:
        importance = predict.predictor.get_feature_importance(target)
        return jsonify({"target": target, "importance": importance})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
