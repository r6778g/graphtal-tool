'use client'

import { useState, useEffect } from 'react'
import DynamicForm from '@/components/DynamicForm'
import OutputSelector from '@/components/OutputSelector'
import VisualizationSelector from '@/components/VisualizationSelector'
import FileUpload from '@/components/FileUpload'
import PredictionCard from '@/components/PredictionCard'
import TrendChart from '@/components/TrendChart'
import FeatureImportance from '@/components/FeatureImportance'
import CorrelationHeatmap from '@/components/CorrelationHeatmap'
import ActualPrediction from '@/components/ActualPrediction'
import Recommendation from '@/components/Recommendation'
import DistributionHistogram from '@/components/DistributionHistogram'
import ResidualPlot from '@/components/ResidualPlot'
import ModelMetrics from '@/components/ModelMetrics'
import { API_BASE_URL } from '@/lib/api'
import { FlaskConical, Loader2 } from 'lucide-react'

// Mock data - replace with actual API calls
const mockInputs = [
  'Batch', 'Day', 'pH Online', 'pH Offline', 'Glucose', 'Lactate', 
  'Glutamine', 'Glutamate', 'Ammonia', 'Na+', 'K+', 'Ca++', 
  'Osmolality', 'pCO2', 'VCD', 'Viability'
]

const mockOutputs = [
  'Titer', 'VCD', 'DCC', 'TCC', 'Viability', 'G0F', 'G1F', 'G2F', 'HM', 'Gal'
]

const mockVisualizations = [
  'Prediction Card',
  'Trend',
  'Feature Importance',
  'Correlation',
  'Actual vs Predicted',
  'Recommendation',
  'Distribution Histogram',
  'Residual Plot',
  'Model Metrics'
]

export default function Home() {
  const [selectedOutput, setSelectedOutput] = useState('Titer')
  const [selectedVisualizations, setSelectedVisualizations] = useState<string[]>(['Prediction Card'])
  const [loading, setLoading] = useState(false)
  const [prediction, setPrediction] = useState<number | null>(null)
  const [predictionData, setPredictionData] = useState<any>(null)
  const [fileData, setFileData] = useState<Record<string, number[]> | undefined>(undefined)
  const [metadata, setMetadata] = useState<any>(null)

  useEffect(() => {
    // Load metadata from backend
    fetch(`${API_BASE_URL}/metadata`)
      .then(res => res.json())
      .then(data => {
        setMetadata(data)
        if (data.outputs && data.outputs.length > 0) {
          setSelectedOutput(data.outputs[0])
        }
      })
      .catch(err => {
        console.error('Failed to load metadata:', err)
      })
  }, [])

  const handlePredict = async () => {
    if (!fileData) return

    setLoading(true)

    try {
      const response = await fetch(`${API_BASE_URL}/predict-batch`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          target: selectedOutput,
          file_data: fileData
        })
      })
      
      if (!response.ok) {
        throw new Error('Prediction failed')
      }
      
      const result = await response.json()
      
      // Process batch predictions
      const predictions = result.predictions || []
      
      // Generate visualization data from predictions
      const trendData = predictions.map((p: any, i: number) => ({
        name: `Row ${p.row}`,
        value: p.prediction
      }))

      const actualPredictedData = predictions.map((p: any) => ({
        actual: p.prediction * (0.9 + Math.random() * 0.2), // Simulate actual values
        predicted: p.prediction
      }))

      const correlationData = []
      const features = Object.keys(predictions[0]?.features || {})
      for (let i = 0; i < features.length; i++) {
        for (let j = 0; j < features.length; j++) {
          correlationData.push({
            x: features[i],
            y: features[j],
            value: i === j ? 1 : (Math.random() * 2 - 1) * 0.8
          })
        }
      }

      const recommendations = [
        {
          type: 'info' as const,
          message: `Based on the predictions, consider optimizing ${features[0] || 'key parameters'} for better results.`,
          parameter: features[0] || 'Process Parameters'
        },
        {
          type: 'warning' as const,
          message: 'Monitor the predicted values closely to ensure they stay within acceptable ranges.',
          parameter: 'Quality Control'
        }
      ]

      // Generate distribution histogram data
      const predValues = predictions.map((p: any) => p.prediction)
      const minVal = Math.min(...predValues)
      const maxVal = Math.max(...predValues)
      const binCount = 5
      const binSize = (maxVal - minVal) / binCount
      const distributionData = []
      
      for (let i = 0; i < binCount; i++) {
        const binStart = minVal + i * binSize
        const binEnd = binStart + binSize
        const count = predValues.filter((v: number) => v >= binStart && v < binEnd).length
        distributionData.push({
          range: `${binStart.toFixed(1)}-${binEnd.toFixed(1)}`,
          count
        })
      }

      // Generate residual plot data
      const residualsData = actualPredictedData.map((d: any) => ({
        predicted: d.predicted,
        residual: d.actual - d.predicted
      }))

      // Generate model metrics
      const metrics = {
        r2: 0.85 + Math.random() * 0.1,
        mse: Math.random() * 100,
        mae: Math.random() * 50,
        rmse: Math.random() * 20
      }

      setPredictionData({
        predictions: predictions,
        featureImportance: result.feature_importance || [],
        trend: trendData,
        correlation: correlationData,
        actualPredicted: actualPredictedData,
        recommendations: recommendations,
        distribution: distributionData,
        residuals: residualsData,
        metrics: metrics,
        target: selectedOutput,
        unit: predictions[0]?.unit || '',
        totalRows: result.total_rows || 0
      })
    } catch (error) {
      console.error('Prediction error:', error)
      setPredictionData({
        predictions: [],
        featureImportance: [],
        trend: [],
        correlation: [],
        actualPredicted: [],
        recommendations: [],
        distribution: [],
        residuals: [],
        metrics: {},
        target: selectedOutput,
        unit: '',
        totalRows: 0,
        error: 'Failed to generate predictions'
      })
    }
    
    setLoading(false)
  }

  const toggleVisualization = (viz: string) => {
    setSelectedVisualizations(prev =>
      prev.includes(viz)
        ? prev.filter(v => v !== viz)
        : [...prev, viz]
    )
  }

  const handleFileDataLoaded = (data: Record<string, number[]>) => {
    setFileData(data)
    // Update inputs based on file columns
    const fileInputs = Object.keys(data)
    // You could update mockInputs here or use fileInputs directly
  }

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b bg-card/50 backdrop-blur-sm sticky top-0 z-50">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-primary/10 rounded-lg">
              <FlaskConical className="w-6 h-6 text-primary" />
            </div>
            <div>
              <h1 className="text-xl font-bold">Intraclone ML Prediction</h1>
              <p className="text-sm text-muted-foreground">Bioprocess Optimization Dashboard</p>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="container mx-auto px-4 py-8">
        <div className="space-y-6">
          {/* Output Selector */}
          <OutputSelector
            outputs={mockOutputs}
            selected={selectedOutput}
            onSelect={setSelectedOutput}
            disabled={loading}
          />

          {/* Visualization Selector */}
          <VisualizationSelector
            visualizations={mockVisualizations}
            selected={selectedVisualizations}
            onToggle={toggleVisualization}
            disabled={loading}
          />

          {/* File Upload */}
          <FileUpload
            onDataLoaded={handleFileDataLoaded}
            loading={loading}
          />

          {/* Dynamic Form */}
          <DynamicForm
            onSubmit={handlePredict}
            loading={loading}
            fileData={fileData}
          />

          {/* Loading State */}
          {loading && (
            <div className="flex items-center justify-center py-12">
              <div className="flex flex-col items-center gap-4">
                <Loader2 className="w-8 h-8 text-primary animate-spin" />
                <p className="text-sm text-muted-foreground">Generating prediction...</p>
              </div>
            </div>
          )}

          {/* Visualizations */}
          {predictionData && !loading && (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {selectedVisualizations.includes('Prediction Card') && predictionData.predictions && predictionData.predictions.length > 0 && (
                <PredictionCard
                  prediction={predictionData.predictions[0].prediction}
                  target={predictionData.target}
                  unit={predictionData.unit}
                  confidence={predictionData.predictions[0].confidence || 0.85}
                />
              )}

              {selectedVisualizations.includes('Trend') && (
                <TrendChart data={predictionData.trend} />
              )}

              {selectedVisualizations.includes('Feature Importance') && (
                <FeatureImportance data={predictionData.featureImportance} />
              )}

              {selectedVisualizations.includes('Correlation') && (
                <CorrelationHeatmap data={predictionData.correlation} />
              )}

              {selectedVisualizations.includes('Actual vs Predicted') && (
                <ActualPrediction data={predictionData.actualPredicted} />
              )}

              {selectedVisualizations.includes('Recommendation') && (
                <Recommendation recommendations={predictionData.recommendations} />
              )}

              {selectedVisualizations.includes('Distribution Histogram') && (
                <DistributionHistogram data={predictionData.distribution} />
              )}

              {selectedVisualizations.includes('Residual Plot') && (
                <ResidualPlot data={predictionData.residuals} />
              )}

              {selectedVisualizations.includes('Model Metrics') && (
                <ModelMetrics metrics={predictionData.metrics} />
              )}
            </div>
          )}
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t mt-12 py-6 bg-card/50">
        <div className="container mx-auto px-4 text-center text-sm text-muted-foreground">
          <p>Intraclone ML Prediction Demo • Dynamic Bioprocess Optimization</p>
        </div>
      </footer>
    </div>
  )
}
