'use client'

import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'

interface FeatureImportanceProps {
  data: Array<{ feature: string; importance: number }>
  title?: string
}

export default function FeatureImportance({ 
  data, 
  title = 'Feature Importance' 
}: FeatureImportanceProps) {
  if (!data || data.length === 0) {
    return (
      <div className="bg-[#f4efe8] border border-[#e8dfd3] rounded-2xl p-6 shadow-2xs">
        <h3 className="text-base font-extrabold text-[#1e293b] mb-4">{title}</h3>
        <div className="text-center py-8 text-[#64748b]">
          <p className="text-xs font-medium">No feature importance data available</p>
        </div>
      </div>
    )
  }

  const sortedData = [...data].sort((a, b) => b.importance - a.importance).slice(0, 10)

  return (
    <div className="bg-[#f4efe8] border border-[#e8dfd3] rounded-2xl p-6 shadow-2xs">
      <h3 className="text-base font-extrabold text-[#1e293b] mb-4">{title}</h3>
      <div className="h-80">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart 
            data={sortedData} 
            layout="vertical"
            margin={{ left: 90, right: 20 }}
          >
            <CartesianGrid strokeDasharray="3 3" stroke="#e5dcd0" />
            <XAxis 
              type="number"
              className="text-xs font-semibold"
              stroke="#64748b"
            />
            <YAxis 
              type="category"
              dataKey="feature"
              className="text-xs font-semibold"
              stroke="#64748b"
              width={85}
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
            <Bar 
              dataKey="importance" 
              fill="#1e293b"
              radius={[0, 6, 6, 0]}
            />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}
