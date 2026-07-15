import pandas as pd
import numpy as np
from sklearn.linear_model import Ridge, Lasso
from sklearn.svm import SVR
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
import joblib
import json
import os

# ── Model registry ────────────────────────────────────────────────────────────
MODEL_REGISTRY = {
    "ridge": Ridge(alpha=1.0),
    "lasso": Lasso(alpha=0.1, max_iter=10_000),
    "svm": SVR(kernel="rbf", C=10, epsilon=0.1),
    "random_forest": RandomForestRegressor(n_estimators=100, random_state=42, n_jobs=-1),
}

OUTPUT_COLUMNS = ["Titer", "VCD", "DCC", "TCC", "Viability", "G0F", "G1F", "G2F", "HM", "Gal"]


def train_model(csv_path: str):
    """Train all model types on CSV data and save everything under model/."""
    df = pd.read_csv(csv_path)
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()

    available_outputs = [c for c in OUTPUT_COLUMNS if c in df.columns]
    if not available_outputs:
        available_outputs = [numeric_cols[-1]]
    input_columns = [c for c in numeric_cols if c not in available_outputs]

    print(f"Inputs  : {input_columns}")
    print(f"Outputs : {available_outputs}")

    # Save column config
    os.makedirs("model", exist_ok=True)
    columns_config = {
        "inputs": input_columns,
        "outputs": available_outputs,
        "model_types": list(MODEL_REGISTRY.keys()),
        "visualizations": [
            "Prediction Card", "Trend", "Feature Importance",
            "Correlation", "Actual vs Predicted", "Recommendation",
            "Distribution Histogram", "Residual Plot", "Model Metrics"
        ],
    }
    with open("model/columns.json", "w") as f:
        json.dump(columns_config, f, indent=2)

    # ── Train every model type for every target ────────────────────────────
    for model_type, base_estimator in MODEL_REGISTRY.items():
        save_dir = f"model/{model_type}"
        os.makedirs(save_dir, exist_ok=True)
        print(f"\n{'─'*50}")
        print(f"Training: {model_type.upper()}")

        for target in available_outputs:
            X = df[input_columns].fillna(df[input_columns].mean())
            y = df[target].fillna(df[target].mean())

            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=0.2, random_state=42
            )

            scaler = StandardScaler()
            X_train_s = scaler.fit_transform(X_train)
            X_test_s = scaler.transform(X_test)

            # Fresh clone for each target so fit() doesn't interfere
            from sklearn.base import clone
            model = clone(base_estimator)
            model.fit(X_train_s, y_train)

            train_r2 = model.score(X_train_s, y_train)
            test_r2 = model.score(X_test_s, y_test)
            print(f"  {target:15s} | Train R²: {train_r2:.4f}  Test R²: {test_r2:.4f}")

            joblib.dump(model, f"{save_dir}/{target.lower()}_model.pkl")
            joblib.dump(scaler, f"{save_dir}/{target.lower()}_scaler.pkl")

    # Keep legacy flat files (ridge, first target) for backwards-compat
    first_target = available_outputs[0]
    legacy_model = joblib.load(f"model/ridge/{first_target.lower()}_model.pkl")
    legacy_scaler = joblib.load(f"model/ridge/{first_target.lower()}_scaler.pkl")
    joblib.dump(legacy_model, "model/model.pkl")
    joblib.dump(legacy_scaler, "model/scaler.pkl")

    print("\n✓ Training complete — all models saved under model/<type>/")


if __name__ == "__main__":
    csv_path = "sample_data.csv"
    if not os.path.exists(csv_path):
        print(f"Error: CSV file not found at {csv_path}")
    else:
        train_model(csv_path)
