'use client'

import { TrendingUp, Activity } from 'lucide-react'
import { cn } from '@/lib/utils'

interface PredictionCardProps {
  prediction: number
  target: string
  unit?: string
  confidence?: number
}

export default function PredictionCard({ 
  prediction, 
  target, 
  unit = 'mg/L',
  confidence 
}: PredictionCardProps) {
  return (
    <div className="bg-gradient-to-br from-primary/10 to-primary/5 border border-primary/20 rounded-lg p-6 shadow-sm">
      <div className="flex items-start justify-between mb-4">
        <div className="flex items-center gap-2">
          <TrendingUp className="w-5 h-5 text-primary" />
          <h3 className="text-lg font-semibold">Prediction Result</h3>
        </div>
        <div className="flex items-center gap-1 text-xs text-muted-foreground">
          <Activity className="w-4 h-4" />
          {confidence && `Confidence: ${(confidence * 100).toFixed(1)}%`}
        </div>
      </div>

      <div className="space-y-2">
        <p className="text-sm text-muted-foreground">Target: {target}</p>
        <div className="flex items-baseline gap-2">
          <span className="text-4xl font-bold text-primary">
            {prediction.toFixed(2)}
          </span>
          <span className="text-sm text-muted-foreground">{unit}</span>
        </div>
      </div>

      {confidence && (
        <div className="mt-4 pt-4 border-t border-primary/20">
          <div className="flex items-center justify-between text-xs text-muted-foreground mb-2">
            <span>Confidence Level</span>
            <span>{(confidence * 100).toFixed(1)}%</span>
          </div>
          <div className="w-full bg-secondary rounded-full h-2">
            <div 
              className="bg-primary h-2 rounded-full transition-all duration-500"
              style={{ width: `${confidence * 100}%` }}
            />
          </div>
        </div>
      )}
    </div>
  )
}
