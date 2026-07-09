# Intraclone ML Prediction Backend

FastAPI backend for the Intraclone ML Prediction Demo with scikit-learn models.

## Features

- **ML Model Training**: Train Ridge regression models on CSV data
- **REST API**: FastAPI endpoints for predictions and metadata
- **Dynamic Configuration**: Auto-generates column configuration from data
- **Multiple Targets**: Supports predicting multiple output variables
- **Feature Importance**: Returns feature importance for predictions

## Project Structure

```
backend/
├── main.py              # FastAPI application
├── train.py             # Model training script
├── predict.py           # Prediction logic
├── requirements.txt     # Python dependencies
├── model/               # Trained models and configuration
│   ├── model.pkl        # Default trained model
│   ├── scaler.pkl       # Feature scaler
│   ├── columns.json     # Column configuration
│   └── {target}_model.pkl  # Target-specific models
└── README.md            # This file
```

## Installation

1. Navigate to the backend directory:
```bash
cd backend
```

2. Create a virtual environment (recommended):
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

## Training the Model

Before running the API, you need to train the ML model on your data:

1. Place your CSV file in the parent directory (e.g., `Intraclone(RD).csv`)
2. Run the training script:
```bash
python train.py
```

This will:
- Load the CSV data
- Identify input and output columns
- Train Ridge regression models for each output
- Save models and scalers to the `model/` directory
- Generate `columns.json` configuration

**Note**: The training script looks for `../Intraclone(RD).csv` by default. Modify the `csv_path` in `train.py` if your file is elsewhere.

## Running the API

Start the FastAPI server:

```bash
python main.py
```

Or using uvicorn directly:

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000`

## API Endpoints

### GET `/`
Root endpoint with API status.

**Response:**
```json
{
  "message": "Intraclone ML Prediction API",
  "status": "running"
}
```

### GET `/metadata`
Get available inputs, outputs, and visualizations.

**Response:**
```json
{
  "inputs": ["Batch", "Day", "pH Online", "pH Offline", ...],
  "outputs": ["Titer", "VCD", "DCC", "TCC", ...],
  "visualizations": ["Prediction Card", "Trend", ...]
}
```

### POST `/predict`
Make a prediction for a specific target.

**Request:**
```json
{
  "target": "Titer",
  "features": {
    "Batch": 1,
    "Day": 5,
    "pH Online": 7.2,
    ...
  }
}
```

**Response:**
```json
{
  "prediction": 652.4,
  "unit": "mg/L",
  "confidence": 0.85,
  "feature_importance": {
    "Glucose": 0.45,
    "Viability": 0.32,
    ...
  }
}
```

### GET `/feature-importance/{target}`
Get feature importance for a specific target.

**Response:**
```json
{
  "target": "Titer",
  "importance": [
    {"feature": "Glucose", "importance": 0.45},
    {"feature": "Viability", "importance": 0.32},
    ...
  ]
}
```

## API Documentation

Once the server is running, visit:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Connecting to Frontend

The frontend is configured to connect to `http://localhost:8000`. Make sure:

1. Backend is running on port 8000
2. CORS is enabled (already configured in `main.py`)
3. Models are trained and available in `model/` directory

## Model Details

- **Algorithm**: Ridge Regression (L2 regularization)
- **Scaling**: StandardScaler for feature normalization
- **Training**: 80/20 train-test split
- **Multiple Models**: Separate model for each output variable

## Troubleshooting

**Model not found error:**
- Run `python train.py` to train models
- Check that `model/` directory exists and contains `.pkl` files

**CORS errors:**
- Ensure CORS middleware is configured in `main.py`
- Check that frontend URL is in `allow_origins`

**Import errors:**
- Make sure all dependencies are installed: `pip install -r requirements.txt`
- Activate your virtual environment

**CSV parsing errors:**
- Ensure CSV file exists at the specified path
- Check that CSV has numeric columns for training
- Verify column names match expected format

## Development

To add new features:

1. **Add new endpoint**: Add route in `main.py`
2. **Modify model**: Update `train.py` for training logic
3. **Update prediction**: Modify `predict.py` for prediction logic
4. **Add dependencies**: Update `requirements.txt`

## Production Deployment

For production deployment:

1. Use a production ASGI server (e.g., Gunicorn with Uvicorn workers)
2. Set up environment variables for configuration
3. Enable HTTPS
4. Add authentication/authorization
5. Set up logging and monitoring
6. Use a proper database for storing predictions/history

Example production command:
```bash
gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```
