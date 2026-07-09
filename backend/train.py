import pandas as pd
import numpy as np
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
import joblib
import json
import os

def train_model(csv_path: str):
    """
    Train ML model on CSV data and save model, scaler, and column configuration.
    """
    # Load data
    df = pd.read_csv(csv_path)
    
    # Separate features and targets
    # Assume all numeric columns are potential features
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    
    # Define common output columns (targets)
    output_columns = ['Titer', 'VCD', 'DCC', 'TCC', 'Viability', 'G0F', 'G1F', 'G2F', 'HM', 'Gal']
    
    # Filter to only include output columns that exist in the data
    available_outputs = [col for col in output_columns if col in df.columns]
    
    # Input columns are all numeric columns except output columns
    input_columns = [col for col in numeric_cols if col not in available_outputs]
    
    # If no output columns found, use the last column as target
    if not available_outputs:
        available_outputs = [numeric_cols[-1]]
        input_columns = numeric_cols[:-1]
    
    print(f"Input columns: {input_columns}")
    print(f"Output columns: {available_outputs}")
    
    # Create column configuration
    columns_config = {
        "inputs": input_columns,
        "outputs": available_outputs,
        "visualizations": [
            "Prediction Card",
            "Trend",
            "Feature Importance",
            "Correlation",
            "Actual vs Predicted",
            "Recommendation"
        ]
    }
    
    # Save column configuration
    with open('model/columns.json', 'w') as f:
        json.dump(columns_config, f, indent=2)
    
    # Train a model for each output
    models = {}
    scalers = {}
    
    for target in available_outputs:
        # Prepare data for this target
        X = df[input_columns].fillna(df[input_columns].mean())
        y = df[target].fillna(df[target].mean())
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
        
        # Scale features
        scaler = StandardScaler()
        X_train_scaled = scaler.fit_transform(X_train)
        X_test_scaled = scaler.transform(X_test)
        
        # Train Ridge regression model
        model = Ridge(alpha=1.0)
        model.fit(X_train_scaled, y_train)
        
        # Evaluate
        train_score = model.score(X_train_scaled, y_train)
        test_score = model.score(X_test_scaled, y_test)
        
        print(f"{target} - Train R²: {train_score:.4f}, Test R²: {test_score:.4f}")
        
        # Save model and scaler
        models[target] = model
        scalers[target] = scaler
    
    # Save models and scalers
    os.makedirs('model', exist_ok=True)
    
    for target in available_outputs:
        joblib.dump(models[target], f'model/{target.lower()}_model.pkl')
        joblib.dump(scalers[target], f'model/{target.lower()}_scaler.pkl')
    
    # Save a default model (first output)
    default_target = available_outputs[0]
    joblib.dump(models[default_target], 'model/model.pkl')
    joblib.dump(scalers[default_target], 'model/scaler.pkl')
    
    print(f"\nTraining complete!")
    print(f"Models saved to model/ directory")
    print(f"Column configuration saved to model/columns.json")

if __name__ == "__main__":
    # Use the sample CSV file
    csv_path = 'sample_data.csv'
    
    if not os.path.exists(csv_path):
        print(f"Error: CSV file not found at {csv_path}")
        print("Please place your CSV file in the correct location.")
    else:
        train_model(csv_path)
