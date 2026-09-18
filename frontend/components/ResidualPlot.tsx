'use client'

import { ScatterChart, Scatter, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine } from 'recharts'

interface ResidualPlotProps {
  data: Array<{ predicted: number; residual: number }>
  title?: string
}

export default function ResidualPlot({ 
  data, 
  title = 'Residual Plot' 
}: ResidualPlotProps) {
  if (!data || data.length === 0) {
    return (
      <div className="bg-[#f4efe8] border border-[#e8dfd3] rounded-2xl p-6 shadow-2xs">
        <h3 className="text-base font-extrabold text-[#1e293b] mb-4">{title}</h3>
        <div className="text-center py-8 text-[#64748b]">
          <p className="text-xs font-medium">No residual data available</p>
        </div>
      </div>
    )
  }

  return (
    <div className="bg-[#f4efe8] border border-[#e8dfd3] rounded-2xl p-6 shadow-2xs">
      <h3 className="text-base font-extrabold text-[#1e293b] mb-4">{title}</h3>
      <div className="h-64">
        <ResponsiveContainer width="100%" height="100%">
          <ScatterChart data={data}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e5dcd0" />
            <XAxis 
              type="number"
              dataKey="predicted"
              name="Predicted"
              className="text-xs font-semibold"
              stroke="#64748b"
            />
            <YAxis 
              type="number"
              dataKey="residual"
              name="Residual"
              className="text-xs font-semibold"
              stroke="#64748b"
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
            <ReferenceLine y={0} stroke="#d97706" strokeDasharray="5 5" strokeWidth={2} />
            <Scatter 
              fill="#1e293b"
              r={5}
            />
          </ScatterChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}
