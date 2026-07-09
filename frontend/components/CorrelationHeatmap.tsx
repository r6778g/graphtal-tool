'use client'

import { cn } from '@/lib/utils'

interface CorrelationHeatmapProps {
  data: Array<{ x: string; y: string; value: number }>
  title?: string
}

export default function CorrelationHeatmap({ 
  data, 
  title = 'Correlation Heatmap' 
}: CorrelationHeatmapProps) {
  if (!data || data.length === 0) {
    return (
      <div className="bg-card border rounded-lg p-6 shadow-sm">
        <h3 className="text-lg font-semibold mb-4">{title}</h3>
        <div className="text-center py-8 text-muted-foreground">
          <p className="text-sm">No correlation data available</p>
        </div>
      </div>
    )
  }

  const getColor = (value: number) => {
    const intensity = Math.abs(value)
    if (value > 0) {
      return `rgba(59, 130, 246, ${intensity})`
    } else {
      return `rgba(239, 68, 68, ${intensity})`
    }
  }

  const uniqueX = [...new Set(data.map(d => d.x))]
  const uniqueY = [...new Set(data.map(d => d.y))]

  return (
    <div className="bg-card border rounded-lg p-6 shadow-sm">
      <h3 className="text-lg font-semibold mb-4">{title}</h3>
      <div className="overflow-x-auto">
        <div className="min-w-[400px]">
          <div className="grid gap-1" style={{ 
            gridTemplateColumns: `auto repeat(${uniqueX.length}, minmax(60px, 1fr))` 
          }}>
            <div></div>
            {uniqueX.map(x => (
              <div key={x} className="text-xs font-medium text-center p-2 text-muted-foreground">
                {x}
              </div>
            ))}
            
            {uniqueY.map(y => (
              <>
                <div key={y} className="text-xs font-medium p-2 text-muted-foreground text-right">
                  {y}
                </div>
                {uniqueX.map(x => {
                  const cell = data.find(d => d.x === x && d.y === y)
                  return (
                    <div
                      key={`${x}-${y}`}
                      className="aspect-square flex items-center justify-center text-xs font-medium rounded"
                      style={{ 
                        backgroundColor: cell ? getColor(cell.value) : 'transparent',
                        color: Math.abs(cell?.value || 0) > 0.5 ? 'white' : 'black'
                      }}
                    >
                      {cell ? cell.value.toFixed(2) : '-'}
                    </div>
                  )
                })}
              </>
            ))}
          </div>
        </div>
      </div>
      
      <div className="flex items-center justify-center gap-4 mt-4 text-xs text-muted-foreground">
        <div className="flex items-center gap-1">
          <div className="w-4 h-4 rounded bg-red-500" />
          <span>Negative</span>
        </div>
        <div className="flex items-center gap-1">
          <div className="w-4 h-4 rounded bg-blue-500" />
          <span>Positive</span>
        </div>
      </div>
    </div>
  )
}
