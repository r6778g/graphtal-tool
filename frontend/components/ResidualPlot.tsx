'use client'

import { ScatterChart, Scatter, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine } from 'recharts'
import { cn } from '@/lib/utils'

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
      <div className="bg-card border rounded-lg p-6 shadow-sm">
        <h3 className="text-lg font-semibold mb-4">{title}</h3>
        <div className="text-center py-8 text-muted-foreground">
          <p className="text-sm">No residual data available</p>
        </div>
      </div>
    )
  }

  const maxResidual = Math.max(...data.map(d => Math.abs(d.residual)))

  return (
    <div className="bg-card border rounded-lg p-6 shadow-sm">
      <h3 className="text-lg font-semibold mb-4">{title}</h3>
      <div className="h-80">
        <ResponsiveContainer width="100%" height="100%">
          <ScatterChart data={data}>
            <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
            <XAxis 
              type="number"
              dataKey="predicted"
              name="Predicted"
              className="text-xs"
              stroke="hsl(var(--muted-foreground))"
            />
            <YAxis 
              type="number"
              dataKey="residual"
              name="Residual"
              className="text-xs"
              stroke="hsl(var(--muted-foreground))"
              domain={[-maxResidual, maxResidual]}
            />
            <Tooltip 
              cursor={{ strokeDasharray: '3 3' }}
              contentStyle={{
                backgroundColor: 'hsl(var(--card))',
                border: '1px solid hsl(var(--border))',
                borderRadius: '0.5rem',
              }}
            />
            <ReferenceLine 
              y={0} 
              stroke="hsl(var(--primary))"
              strokeDasharray="5 5"
              strokeWidth={2}
            />
            <Scatter 
              fill="hsl(var(--primary))"
              r={6}
            />
          </ScatterChart>
        </ResponsiveContainer>
      </div>
      <p className="text-xs text-muted-foreground mt-2 text-center">
        Residuals should be randomly distributed around zero
      </p>
    </div>
  )
}
