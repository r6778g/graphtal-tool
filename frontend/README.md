# Intraclone ML Prediction UI

A modern, dynamic Next.js frontend for the Intraclone ML Prediction Demo.

## Features

- **Dynamic Input Form**: Automatically generates input fields based on metadata from the backend
- **Output Selection**: Choose from multiple prediction targets (Titer, VCD, DCC, etc.)
- **Dynamic Visualizations**: Select which visualizations to display:
  - Prediction Card with confidence levels
  - Trend Analysis charts
  - Feature Importance rankings
  - Correlation Heatmaps
  - Actual vs Predicted scatter plots
  - Rule-based Recommendations
- **Modern UI**: Built with Tailwind CSS, featuring a clean, professional design
- **Responsive**: Works seamlessly on desktop and mobile devices

## Tech Stack

- **Next.js 14**: React framework with App Router
- **TypeScript**: Type-safe development
- **Tailwind CSS**: Utility-first styling
- **Recharts**: Data visualization library
- **Lucide React**: Modern icon library

## Getting Started

### Prerequisites

- Node.js 18+ installed
- npm or yarn package manager

### Installation

1. Navigate to the frontend directory:
```bash
cd frontend
```

2. Install dependencies:
```bash
npm install
```

3. Run the development server:
```bash
npm run dev
```

4. Open [http://localhost:3000](http://localhost:3000) in your browser

## Project Structure

```
frontend/
├── app/
│   ├── layout.tsx          # Root layout with metadata
│   ├── page.tsx            # Main page integrating all components
│   └── globals.css         # Global styles with Tailwind
├── components/
│   ├── DynamicForm.tsx     # Dynamic input form component
│   ├── OutputSelector.tsx  # Target selection component
│   ├── VisualizationSelector.tsx  # Viz selection component
│   ├── PredictionCard.tsx  # Prediction result display
│   ├── TrendChart.tsx      # Trend line chart
│   ├── FeatureImportance.tsx  # Feature importance bar chart
│   ├── CorrelationHeatmap.tsx   # Correlation matrix
│   ├── ActualPrediction.tsx     # Actual vs Predicted scatter
│   └── Recommendation.tsx  # Rule-based recommendations
├── lib/
│   └── utils.ts            # Utility functions (cn helper)
├── package.json           # Dependencies and scripts
├── tsconfig.json          # TypeScript configuration
├── tailwind.config.ts     # Tailwind CSS configuration
└── next.config.js         # Next.js configuration
```

## API Integration

The frontend connects to the backend through `NEXT_PUBLIC_API_URL`. For production builds, the app falls back to:

```bash
https://graphtal-tool-production-07b7.up.railway.app
```

To override it locally, create `frontend/.env.local` with:

```bash
NEXT_PUBLIC_API_URL=https://graphtal-tool-production-07b7.up.railway.app
```

The frontend is designed to work with a FastAPI backend. Currently, it uses mock data for demonstration. To connect to the real backend:

1. Update the API calls in `app/page.tsx` to fetch from your FastAPI endpoints:
   - `GET /metadata` - Get available inputs, outputs, and visualizations
   - `POST /predict` - Submit prediction request

Example:
```typescript
const response = await fetch('http://localhost:8000/predict', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    target: selectedOutput,
    features: formData
  })
})
```

## Customization

### Adding New Visualizations

1. Create a new component in `components/`
2. Add it to the `mockVisualizations` array in `app/page.tsx`
3. Import and render it in the visualizations section

### Styling

The UI uses Tailwind CSS with custom CSS variables for theming. Modify `app/globals.css` to customize colors and styles.

## Build for Production

```bash
npm run build
npm start
```

## Future Enhancements

- Connect to real FastAPI backend
- Add SHAP explanations for model interpretability
- Implement user authentication
- Add batch comparison features
- Export reports as PDF
- Add model retraining interface
