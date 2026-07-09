'use client'

import { Lightbulb, AlertTriangle, CheckCircle, Info } from 'lucide-react'
import { cn } from '@/lib/utils'

interface RecommendationItem {
  type: 'warning' | 'success' | 'info'
  message: string
  parameter?: string
}

interface RecommendationProps {
  recommendations: RecommendationItem[]
  title?: string
}

export default function Recommendation({ 
  recommendations, 
  title = 'Recommendations' 
}: RecommendationProps) {
  if (!recommendations || recommendations.length === 0) {
    return (
      <div className="bg-card border rounded-lg p-6 shadow-sm">
        <div className="flex items-center gap-2 mb-4">
          <Lightbulb className="w-5 h-5 text-primary" />
          <h3 className="text-lg font-semibold">{title}</h3>
        </div>
        <div className="text-center py-8 text-muted-foreground">
          <Lightbulb className="w-12 h-12 mx-auto mb-2 opacity-50" />
          <p className="text-sm">No recommendations available</p>
        </div>
      </div>
    )
  }

  const getIcon = (type: RecommendationItem['type']) => {
    switch (type) {
      case 'warning':
        return <AlertTriangle className="w-5 h-5 text-yellow-500" />
      case 'success':
        return <CheckCircle className="w-5 h-5 text-green-500" />
      case 'info':
        return <Info className="w-5 h-5 text-blue-500" />
    }
  }

  const getBgColor = (type: RecommendationItem['type']) => {
    switch (type) {
      case 'warning':
        return 'bg-yellow-50 border-yellow-200 dark:bg-yellow-950 dark:border-yellow-800'
      case 'success':
        return 'bg-green-50 border-green-200 dark:bg-green-950 dark:border-green-800'
      case 'info':
        return 'bg-blue-50 border-blue-200 dark:bg-blue-950 dark:border-blue-800'
    }
  }

  return (
    <div className="bg-card border rounded-lg p-6 shadow-sm">
      <div className="flex items-center gap-2 mb-4">
        <Lightbulb className="w-5 h-5 text-primary" />
        <h3 className="text-lg font-semibold">{title}</h3>
      </div>

      <div className="space-y-3">
        {recommendations.map((rec, index) => (
          <div
            key={index}
            className={cn(
              "flex items-start gap-3 p-4 rounded-lg border",
              getBgColor(rec.type)
            )}
          >
            <div className="flex-shrink-0 mt-0.5">
              {getIcon(rec.type)}
            </div>
            <div className="flex-1">
              {rec.parameter && (
                <p className="text-sm font-medium mb-1">
                  {rec.parameter}
                </p>
              )}
              <p className="text-sm text-foreground/80">
                {rec.message}
              </p>
            </div>
          </div>
        ))}

        {recommendations.length === 0 && (
          <div className="text-center py-8 text-muted-foreground">
            <Lightbulb className="w-12 h-12 mx-auto mb-2 opacity-50" />
            <p className="text-sm">No recommendations available</p>
          </div>
        )}
      </div>
    </div>
  )
}
