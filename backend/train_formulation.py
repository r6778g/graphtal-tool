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

# Formulation-specific outputs
FORMULATION_OUTPUTS = [
    "Particle Size (nm)",
    "Spreadability (h)", 
    "% in vitro Drug Release (t24)",
    "% in vitro Drug Release (t40)",
    "% Ex vivo drug release (t24)",
    "Viscocity (cps)"
]

FORMULATION_INPUTS = ["Oil", "Smix", "Water"]


def train_formulation_model(csv_path: str):
    """Train all model types on formulation CSV data and save everything under model/formulation/."""
    df = pd.read_csv(csv_path)
    
    # Remove Run Order column if present
    if "Run Order" in df.columns:
        df = df.drop(columns=["Run Order"])
    
    # Ensure we have the expected columns
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    
    available_outputs = [c for c in FORMULATION_OUTPUTS if c in df.columns]
    if not available_outputs:
        # Fallback to last numeric columns if expected outputs not found
        available_outputs = numeric_cols[-6:] if len(numeric_cols) >= 6 else [numeric_cols[-1]]
    
    input_columns = [c for c in numeric_cols if c not in available_outputs]
    
    # If no inputs found, use the first 3 numeric columns
    if not input_columns:
        input_columns = numeric_cols[:3]
    
    print(f"Formulation Inputs  : {input_columns}")
    print(f"Formulation Outputs : {available_outputs}")
    print(f"Total samples       : {len(df)}")

    # Save column config
    formulation_model_dir = "model/formulation"
    os.makedirs(formulation_model_dir, exist_ok=True)
    
    columns_config = {
        "inputs": input_columns,
        "outputs": available_outputs,
        "model_types": list(MODEL_REGISTRY.keys()),
        "visualizations": [
            "Prediction Card", "Trend", "Feature Importance",
            "Correlation", "Actual vs Predicted", "Recommendation",
            "Distribution Histogram", "Residual Plot", "Model Metrics"
        ],
        "data_type": "formulation"
    }
    
    config_path = os.path.join(formulation_model_dir, "columns.json")
    with open(config_path, "w") as f:
        json.dump(columns_config, f, indent=2)

    # ── Train every model type for every target ────────────────────────────
    for model_type, base_estimator in MODEL_REGISTRY.items():
        save_dir = os.path.join(formulation_model_dir, model_type)
        os.makedirs(save_dir, exist_ok=True)
        print(f"\n{'─'*50}")
        print(f"Training Formulation: {model_type.upper()}")

        for target in available_outputs:
            X = df[input_columns].fillna(df[input_columns].mean())
            y = df[target].fillna(df[target].mean())

            # For small datasets, use simpler cross-validation
            if len(df) < 30:
                print(f"  Warning: Small dataset ({len(df)} samples), using 80/20 split")
            
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=0.2, random_state=42
            )

            scaler = StandardScaler()
            X_train_s = scaler.fit_transform(X_train)
            X_test_s = scaler.transform(X_test)

            # Fresh clone for each target so fit() doesn't interfere
            from sklearn.base import clone
            model = clone(base_estimator)
            
            try:
                model.fit(X_train_s, y_train)
                
                train_r2 = model.score(X_train_s, y_train)
                test_r2 = model.score(X_test_s, y_test)
                print(f"  {target:30s} | Train R²: {train_r2:.4f}  Test R²: {test_r2:.4f}")

                # Sanitize filename for target
                safe_target_name = target.lower().replace(" ", "_").replace("(", "").replace(")", "").replace("%", "pct").replace("/", "_")
                
                joblib.dump(model, os.path.join(save_dir, f"{safe_target_name}_model.pkl"))
                joblib.dump(scaler, os.path.join(save_dir, f"{safe_target_name}_scaler.pkl"))
            except Exception as e:
                print(f"  Error training {target}: {e}")
                continue

    # Keep legacy flat files (ridge, first target) for backwards-compat
    first_target = available_outputs[0]
    safe_first_target = first_target.lower().replace(" ", "_").replace("(", "").replace(")", "").replace("%", "pct").replace("/", "_")
    
    legacy_model_path = os.path.join(formulation_model_dir, "ridge", f"{safe_first_target}_model.pkl")
    legacy_scaler_path = os.path.join(formulation_model_dir, "ridge", f"{safe_first_target}_scaler.pkl")
    
    if os.path.exists(legacy_model_path) and os.path.exists(legacy_scaler_path):
        legacy_model = joblib.load(legacy_model_path)
        legacy_scaler = joblib.load(legacy_scaler_path)
        joblib.dump(legacy_model, os.path.join(formulation_model_dir, "model.pkl"))
        joblib.dump(legacy_scaler, os.path.join(formulation_model_dir, "scaler.pkl"))

    print(f"\n✓ Formulation training complete — all models saved under {formulation_model_dir}/")


if __name__ == "__main__":
    possible_paths = [
        "backend/formulation_data.csv",
        "formulation_data.csv",
    ]
    csv_path = None
    for p in possible_paths:
        if os.path.exists(p):
            csv_path = p
            break

    if not csv_path:
        print(f"Error: Formulation CSV file not found in paths: {possible_paths}")
    else:
        print(f"Training formulation models using dataset: {csv_path}")
        train_formulation_model(csv_path)