# Intraclone ML Prediction Demo - Functional Specification

## Goal

Build a simple MVP using:

-   Next.js (Frontend)
-   FastAPI (Python Backend)
-   Scikit-learn Model
-   No Database
-   CSV file used for training
-   Dynamic prediction and dynamic visualization

Reference: The uploaded Intraclone analysis report defines the available
process parameters, prediction targets, and optimization ideas.

------------------------------------------------------------------------

# Data Flow

CSV Dataset │ ▼ Train ML Model │ Save model (.pkl) │ ▼ FastAPI │ POST
/predict │ ▼ Next.js │ Dynamic UI │ Prediction │ Visualization

------------------------------------------------------------------------

# Input Parameters

The UI loads all available input columns dynamically.

Examples

-   Batch
-   Day
-   pH Online
-   pH Offline
-   Glucose
-   Lactate
-   Glutamine
-   Glutamate
-   Ammonia
-   Na+
-   K+
-   Ca++
-   Osmolality
-   pCO2
-   VCD
-   Viability
-   (Any future input column)

Instead of hardcoding fields, create a configuration file:

columns.json

{ "inputs":\[...\], "outputs":\[...\] }

The frontend generates the form from this file.

------------------------------------------------------------------------

# Prediction Output

The user selects ONE prediction target.

Dropdown

Predict

▼ Titer

Possible outputs

-   Titer
-   VCD
-   DCC
-   TCC
-   Viability
-   G0F
-   G1F
-   G2F
-   HM
-   Gal
-   Any numeric output column

No frontend changes are needed when a new output is added.

------------------------------------------------------------------------

# Dynamic Visualization

After prediction the user chooses what to display.

Visualization Menu

□ Prediction Card

□ Trend

□ Feature Importance

□ Correlation

□ Actual vs Predicted

□ Recommendation

Each visualization is an independent React component.

components/ PredictionCard.tsx TrendChart.tsx FeatureImportance.tsx
CorrelationHeatmap.tsx ActualPrediction.tsx Recommendation.tsx

The selected visualization is rendered dynamically.

------------------------------------------------------------------------

# Recommendation Engine

Initially use rule-based logic.

Example

IF

Ammonia \> 5

Show

Reduce ammonia concentration.

IF

Viability \> 98

Suggest extending culture.

Later this can be replaced by AI-generated recommendations.

------------------------------------------------------------------------

# Backend API

GET /metadata

Returns

{ "inputs":\[...\], "outputs":\[...\], "visualizations":\[ "Prediction
Card", "Trend", "Feature Importance", "Correlation", "Actual vs
Predicted", "Recommendation" \] }

POST /predict

Input

{ "target":"Titer", "features":{ "...":"..." } }

Output

{ "prediction":652.4, "unit":"mg/L" }

The frontend never hardcodes input fields, outputs, or visualization
options. Everything comes from the metadata API.

------------------------------------------------------------------------

# Folder Structure

frontend/

components/ DynamicForm.tsx OutputSelector.tsx VisualizationSelector.tsx
PredictionCard.tsx TrendChart.tsx FeatureImportance.tsx
CorrelationHeatmap.tsx Recommendation.tsx

app/ page.tsx

backend/

model/ ridge.pkl scaler.pkl columns.json

main.py train.py predict.py

------------------------------------------------------------------------

# MVP Scope

Included

-   Dynamic input fields
-   Dynamic output selection
-   Dynamic visualization selection
-   One trained ML model
-   FastAPI backend
-   Next.js frontend

Not Included

-   Database
-   Login
-   User management
-   Cloud deployment
-   History
-   Model retraining

------------------------------------------------------------------------

# Future

-   Multiple ML models
-   SHAP explanations
-   Database
-   Authentication
-   Batch comparison
-   Report generation
-   PDF export
