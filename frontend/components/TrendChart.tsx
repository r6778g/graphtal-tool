'use client'

import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'

interface TrendChartProps {
  data: Array<{ name: string; value: number }>
  title?: string
  color?: string
}

export default function TrendChart({ data, title = 'Trend Analysis', color = '#d97706' }: TrendChartProps) {
  if (!data || data.length === 0) {
    return (
      <div className="bg-[#f4efe8] border border-[#e8dfd3] rounded-2xl p-6 shadow-2xs">
        <h3 className="text-base font-extrabold text-[#1e293b] mb-4">{title}</h3>
        <div className="text-center py-8 text-[#64748b]">
          <p className="text-xs">No trend data available</p>
        </div>
      </div>
    )
  }

  return (
    <div className="bg-[#f4efe8] border border-[#e8dfd3] rounded-2xl p-6 shadow-2xs">
      <h3 className="text-base font-extrabold text-[#1e293b] mb-4">{title}</h3>
      <div className="h-64">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e5dcd0" />
            <XAxis 
              dataKey="name" 
              className="text-xs font-semibold"
              stroke="#64748b"
            />
            <YAxis 
              className="text-xs font-semibold"
              stroke="#64748b"
            />
            <Tooltip 
              contentStyle={{
                backgroundColor: '#faf8f5',
                border: '1px solid #e8dfd3',
                borderRadius: '0.75rem',
                color: '#1e293b',
                fontWeight: 'bold',
                fontSize: '12px'
              }}
            />
            <Line 
              type="monotone" 
              dataKey="value" 
              stroke={color}
              strokeWidth={2.5}
              dot={{ fill: color, r: 4 }}
              activeDot={{ r: 6 }}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}
