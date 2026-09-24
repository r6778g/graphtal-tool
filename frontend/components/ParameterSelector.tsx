'use client'

import { cn } from '@/lib/utils'
import { Check } from 'lucide-react'

interface ParameterSelectorProps {
  fileData?: Record<string, number[]>
  selectedParameters?: string[]
  onParameterToggle?: (parameter: string) => void
  onSelectAll?: () => void
  onDeselectAll?: () => void
  loading?: boolean
}

export default function ParameterSelector({ 
  fileData, 
  selectedParameters, 
  onParameterToggle, 
  onSelectAll, 
  onDeselectAll,
  loading 
}: ParameterSelectorProps) {
  const getAllParameters = () => {
    if (!fileData) return []
    return Object.keys(fileData)
  }

  if (!fileData) return null

  return (
    <div className="bg-[#f4efe8] border border-[#e8dfd3] rounded-2xl p-6 shadow-2xs">
      <div className="flex items-center gap-2 mb-4">
        <div className="w-5 h-5 rounded-lg bg-[#e5dcd0] flex items-center justify-center border border-[#d8cebf]">
          <Check className="w-3 h-3 text-[#1e293b]" />
        </div>
        <h2 className="text-base font-extrabold text-[#1e293b]">Select Input Parameters</h2>
      </div>
      
      <div className="bg-[#faf8f5] border border-[#e8dfd3] rounded-lg p-3">
        <div className="flex items-center justify-between mb-2">
          <p className="text-xs font-semibold text-[#1e293b]">Selected Input Parameters ({selectedParameters?.length || 0}):</p>
          <div className="flex gap-1">
            <button
              onClick={onSelectAll}
              disabled={loading}
              className="text-xs px-2 py-0.5 bg-[#d97706]/10 hover:bg-[#d97706]/20 text-[#b45309] rounded transition-colors disabled:opacity-50"
            >
              Select All
            </button>
            <button
              onClick={onDeselectAll}
              disabled={loading}
              className="text-xs px-2 py-0.5 bg-[#1e293b]/10 hover:bg-[#1e293b]/20 text-[#1e293b] rounded transition-colors disabled:opacity-50"
            >
              Deselect All
            </button>
          </div>
        </div>
        <div className="flex flex-wrap gap-1.5">
          {getAllParameters().map((param) => (
            <button
              key={param}
              onClick={() => onParameterToggle?.(param)}
              disabled={loading}
              className={cn(
                "px-2 py-0.5 text-xs rounded-full border transition-colors cursor-pointer flex items-center gap-1",
                selectedParameters?.includes(param)
                  ? "bg-[#d97706]/10 text-[#b45309] border-[#d97706]/20 hover:bg-[#d97706]/20"
                  : "bg-[#e8dfd3]/30 text-[#64748b] border-[#e8dfd3]/50 hover:bg-[#e8dfd3]/50",
                loading && "opacity-50 cursor-not-allowed"
              )}
            >
              {selectedParameters?.includes(param) ? <Check className="w-3 h-3" /> : null}
              {param}
            </button>
          ))}
        </div>
      </div>
    </div>
  )
}
