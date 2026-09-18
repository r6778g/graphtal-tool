'use client'

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
      <div className="bg-[#f4efe8] border border-[#e8dfd3] rounded-2xl p-6 shadow-2xs">
        <h3 className="text-base font-extrabold text-[#1e293b] mb-4">{title}</h3>
        <div className="text-center py-8 text-[#64748b]">
          <p className="text-xs font-medium">No correlation data available</p>
        </div>
      </div>
    )
  }

  const getColor = (value: number) => {
    const intensity = Math.abs(value)
    if (value > 0) {
      return `rgba(217, 119, 6, ${intensity})`
    } else {
      return `rgba(225, 29, 72, ${intensity})`
    }
  }

  const uniqueX = [...new Set(data.map(d => d.x))]
  const uniqueY = [...new Set(data.map(d => d.y))]

  return (
    <div className="bg-[#f4efe8] border border-[#e8dfd3] rounded-2xl p-6 shadow-2xs">
      <h3 className="text-base font-extrabold text-[#1e293b] mb-4">{title}</h3>
      <div className="overflow-x-auto">
        <div className="min-w-[380px]">
          <div className="grid gap-1" style={{ 
            gridTemplateColumns: `auto repeat(${uniqueX.length}, minmax(55px, 1fr))` 
          }}>
            <div></div>
            {uniqueX.map(x => (
              <div key={x} className="text-xs font-bold text-center p-1.5 text-[#64748b] truncate">
                {x}
              </div>
            ))}
            
            {uniqueY.map(y => (
              <div key={`row-${y}`} className="contents">
                <div className="text-xs font-bold p-1.5 text-[#64748b] text-right truncate">
                  {y}
                </div>
                {uniqueX.map(x => {
                  const cell = data.find(d => d.x === x && d.y === y)
                  return (
                    <div
                      key={`${x}-${y}`}
                      className="aspect-square flex items-center justify-center text-[11px] font-bold rounded-lg transition-all hover:scale-105"
                      style={{ 
                        backgroundColor: cell ? getColor(cell.value) : 'transparent',
                        color: Math.abs(cell?.value || 0) > 0.4 ? 'white' : '#1e293b'
                      }}
                      title={`${x} vs ${y}: ${cell ? cell.value.toFixed(3) : 'N/A'}`}
                    >
                      {cell ? cell.value.toFixed(2) : '-'}
                    </div>
                  )
                })}
              </div>
            ))}
          </div>
        </div>
      </div>
      
      <div className="flex items-center justify-center gap-6 mt-4 text-xs font-semibold text-[#64748b]">
        <div className="flex items-center gap-1.5">
          <div className="w-3.5 h-3.5 rounded bg-rose-500" />
          <span>Negative</span>
        </div>
        <div className="flex items-center gap-1.5">
          <div className="w-3.5 h-3.5 rounded bg-[#d97706]" />
          <span>Positive</span>
        </div>
      </div>
    </div>
  )
}
