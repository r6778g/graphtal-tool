'use client'

import { ScatterChart, Scatter, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine } from 'recharts'

interface ActualPredictionProps {
  data: Array<{ actual: number; predicted: number }>
  title?: string
}

export default function ActualPrediction({ 
  data, 
  title = 'Actual vs Predicted' 
}: ActualPredictionProps) {
  if (!data || data.length === 0) {
    return (
      <div className="bg-[#f4efe8] border border-[#e8dfd3] rounded-2xl p-6 shadow-2xs">
        <h3 className="text-base font-extrabold text-[#1e293b] mb-4">{title}</h3>
        <div className="text-center py-8 text-[#64748b]">
          <p className="text-xs font-medium">No actual vs predicted data available</p>
        </div>
      </div>
    )
  }

  const maxVal = Math.max(...data.map(d => Math.max(d.actual, d.predicted)))

  return (
    <div className="bg-[#f4efe8] border border-[#e8dfd3] rounded-2xl p-6 shadow-2xs">
      <h3 className="text-base font-extrabold text-[#1e293b] mb-4">{title}</h3>
      <div className="h-80">
        <ResponsiveContainer width="100%" height="100%">
          <ScatterChart data={data}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e5dcd0" />
            <XAxis 
              type="number"
              dataKey="actual"
              name="Actual"
              className="text-xs font-semibold"
              stroke="#64748b"
              domain={[0, maxVal]}
            />
            <YAxis 
              type="number"
              dataKey="predicted"
              name="Predicted"
              className="text-xs font-semibold"
              stroke="#64748b"
              domain={[0, maxVal]}
            />
            <Tooltip 
              cursor={{ strokeDasharray: '3 3' }}
              contentStyle={{
                backgroundColor: '#faf8f5',
                border: '1px solid #e8dfd3',
                borderRadius: '0.75rem',
                color: '#1e293b',
                fontWeight: 'bold',
                fontSize: '12px'
              }}
            />
            <ReferenceLine 
              segment={[
                { x: 0, y: 0 },
                { x: maxVal, y: maxVal }
              ]}
              stroke="#d97706"
              strokeDasharray="5 5"
              strokeWidth={2}
            />
            <Scatter 
              fill="#1e293b"
              r={6}
            />
          </ScatterChart>
        </ResponsiveContainer>
      </div>
      <p className="text-xs text-[#64748b] font-medium mt-2 text-center">
        Points on the dashed diagonal line indicate perfect model prediction
      </p>
    </div>
  )
}
