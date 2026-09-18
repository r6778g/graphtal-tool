'use client'

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
  title = 'Model Evaluation Metrics' 
}: ModelMetricsProps) {
  if (!metrics || Object.keys(metrics).length === 0) {
    return (
      <div className="bg-[#f4efe8] border border-[#e8dfd3] rounded-2xl p-6 shadow-2xs">
        <h3 className="text-base font-extrabold text-[#1e293b] mb-4">{title}</h3>
        <div className="text-center py-8 text-[#64748b]">
          <p className="text-xs font-medium">No metrics available</p>
        </div>
      </div>
    )
  }

  const metricItems = [
    {
      label: 'R² Score (Accuracy)',
      value: metrics.r2 !== undefined ? `${(metrics.r2 * 100).toFixed(2)}%` : 'N/A',
      description: 'Variance explained by model',
      color: 'text-[#b45309]'
    },
    {
      label: 'Root Mean Squared Error (RMSE)',
      value: metrics.rmse !== undefined ? metrics.rmse.toFixed(2) : 'N/A',
      description: 'Standard deviation of residuals',
      color: 'text-[#1e293b]'
    },
    {
      label: 'Mean Absolute Error (MAE)',
      value: metrics.mae !== undefined ? metrics.mae.toFixed(2) : 'N/A',
      description: 'Average magnitude of errors',
      color: 'text-[#1e293b]'
    },
    {
      label: 'Mean Squared Error (MSE)',
      value: metrics.mse !== undefined ? metrics.mse.toFixed(2) : 'N/A',
      description: 'Average squared difference',
      color: 'text-[#1e293b]'
    }
  ]

  return (
    <div className="bg-[#f4efe8] border border-[#e8dfd3] rounded-2xl p-6 shadow-2xs">
      <h3 className="text-base font-extrabold text-[#1e293b] mb-4">{title}</h3>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        {metricItems.map((item, index) => (
          <div
            key={index}
            className="p-4 rounded-xl bg-[#faf8f5] border border-[#e5dcd0]"
          >
            <p className="text-xs font-bold text-[#64748b] mb-1">{item.label}</p>
            <p className={`text-2xl font-extrabold ${item.color} mb-1`}>
              {item.value}
            </p>
            <p className="text-[11px] text-[#94a3b8] font-medium">{item.description}</p>
          </div>
        ))}
      </div>
    </div>
  )
}
