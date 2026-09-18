'use client'

import { TrendingUp, Activity } from 'lucide-react'

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
    <div className="bg-[#f4efe8] border border-[#e8dfd3] rounded-2xl p-6 shadow-2xs flex flex-col justify-between">
      <div>
        <div className="flex items-start justify-between mb-4">
          <div className="flex items-center gap-2">
            <TrendingUp className="w-5 h-5 text-[#d97706]" />
            <h3 className="text-base font-extrabold text-[#1e293b]">Prediction Result</h3>
          </div>
          {confidence && (
            <div className="flex items-center gap-1 text-xs font-semibold text-[#64748b]">
              <Activity className="w-3.5 h-3.5 text-[#d97706]" />
              <span>Confidence: {(confidence * 100).toFixed(1)}%</span>
            </div>
          )}
        </div>

        <div className="space-y-1">
          <p className="text-xs font-bold text-[#64748b]">Target: <span className="text-[#1e293b]">{target}</span></p>
          <div className="flex items-baseline gap-2 pt-1">
            <span className="text-4xl font-extrabold text-[#b45309]">
              {prediction.toFixed(2)}
            </span>
            <span className="text-sm font-semibold text-[#64748b]">{unit}</span>
          </div>
        </div>
      </div>

      {confidence && (
        <div className="mt-6 pt-4 border-t border-[#e5dcd0]">
          <div className="flex items-center justify-between text-xs font-semibold text-[#64748b] mb-1.5">
            <span>Confidence Level</span>
            <span className="text-[#1e293b] font-bold">{(confidence * 100).toFixed(1)}%</span>
          </div>
          <div className="w-full bg-[#e5dcd0] rounded-full h-2 overflow-hidden">
            <div 
              className="bg-[#d97706] h-2 rounded-full transition-all duration-500"
              style={{ width: `${confidence * 100}%` }}
            />
          </div>
        </div>
      )}
    </div>
  )
}
