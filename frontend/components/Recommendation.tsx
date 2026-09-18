'use client'

import { Lightbulb, AlertTriangle, CheckCircle } from 'lucide-react'

interface RecommendationProps {
  recommendations: Array<{
    type: 'info' | 'warning' | 'success'
    message: string
    parameter?: string
  }>
  title?: string
}

export default function Recommendation({ 
  recommendations, 
  title = 'Optimization Recommendations' 
}: RecommendationProps) {
  if (!recommendations || recommendations.length === 0) {
    return (
      <div className="bg-[#f4efe8] border border-[#e8dfd3] rounded-2xl p-6 shadow-2xs">
        <h3 className="text-base font-extrabold text-[#1e293b] mb-4">{title}</h3>
        <div className="text-center py-8 text-[#64748b]">
          <p className="text-xs font-medium">No recommendations available</p>
        </div>
      </div>
    )
  }

  const getIcon = (type: string) => {
    switch (type) {
      case 'warning':
        return <AlertTriangle className="w-5 h-5 text-amber-700 shrink-0" />
      case 'success':
        return <CheckCircle className="w-5 h-5 text-emerald-700 shrink-0" />
      default:
        return <Lightbulb className="w-5 h-5 text-[#d97706] shrink-0" />
    }
  }

  return (
    <div className="bg-[#f4efe8] border border-[#e8dfd3] rounded-2xl p-6 shadow-2xs">
      <h3 className="text-base font-extrabold text-[#1e293b] mb-4">{title}</h3>
      <div className="space-y-3">
        {recommendations.map((rec, index) => (
          <div
            key={index}
            className="flex items-start gap-3 p-4 rounded-xl bg-[#faf8f5] border border-[#e5dcd0]"
          >
            {getIcon(rec.type)}
            <div className="flex-1">
              {rec.parameter && (
                <span className="text-xs font-bold text-[#b45309] block mb-1">
                  Parameter: {rec.parameter}
                </span>
              )}
              <p className="text-xs font-semibold text-[#1e293b] leading-relaxed">
                {rec.message}
              </p>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
