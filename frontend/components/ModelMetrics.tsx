'use client'

import { BarChart3, TrendingUp, Target, Activity } from 'lucide-react'
import { cn } from '@/lib/utils'

interface ModelMetricsProps {
  metrics: {
    r2?: number
    mse?: number
    mae?: number
    rmse?: number
  }
  title?: string
}

export default function ModelMetrics({ 
  metrics, 
  title = 'Model Performance Metrics' 
}: ModelMetricsProps) {
  const metricItems = [
    {
      label: 'R² Score',
      value: metrics.r2 !== undefined ? metrics.r2.toFixed(3) : 'N/A',
      icon: <Target className="w-5 h-5 text-green-500" />,
      description: 'Coefficient of determination',
      color: 'bg-green-50 border-green-200 dark:bg-green-950 dark:border-green-800'
    },
    {
      label: 'MSE',
      value: metrics.mse !== undefined ? metrics.mse.toFixed(3) : 'N/A',
      icon: <BarChart3 className="w-5 h-5 text-blue-500" />,
      description: 'Mean Squared Error',
      color: 'bg-blue-50 border-blue-200 dark:bg-blue-950 dark:border-blue-800'
    },
    {
      label: 'MAE',
      value: metrics.mae !== undefined ? metrics.mae.toFixed(3) : 'N/A',
      icon: <Activity className="w-5 h-5 text-purple-500" />,
      description: 'Mean Absolute Error',
      color: 'bg-purple-50 border-purple-200 dark:bg-purple-950 dark:border-purple-800'
    },
    {
      label: 'RMSE',
      value: metrics.rmse !== undefined ? metrics.rmse.toFixed(3) : 'N/A',
      icon: <TrendingUp className="w-5 h-5 text-orange-500" />,
      description: 'Root Mean Squared Error',
      color: 'bg-orange-50 border-orange-200 dark:bg-orange-950 dark:border-orange-800'
    }
  ]

  return (
    <div className="bg-card border rounded-lg p-6 shadow-sm">
      <h3 className="text-lg font-semibold mb-4">{title}</h3>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        {metricItems.map((item, index) => (
          <div
            key={index}
            className={cn(
              "flex items-start gap-3 p-4 rounded-lg border",
              item.color
            )}
          >
            <div className="flex-shrink-0 mt-0.5">
              {item.icon}
            </div>
            <div className="flex-1">
              <p className="text-sm font-medium mb-1">
                {item.label}
              </p>
              <p className="text-2xl font-bold mb-1">
                {item.value}
              </p>
              <p className="text-xs text-muted-foreground">
                {item.description}
              </p>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
