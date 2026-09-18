'use client'

import { BarChart3 } from 'lucide-react'
import { cn } from '@/lib/utils'

interface VisualizationSelectorProps {
  visualizations: string[]
  selected: string[]
  onToggle: (viz: string) => void
  disabled?: boolean
}

export default function VisualizationSelector({ 
  visualizations, 
  selected, 
  onToggle,
  disabled 
}: VisualizationSelectorProps) {
  return (
    <div className="bg-[#f4efe8] border border-[#e8dfd3] rounded-2xl p-6 shadow-2xs">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <BarChart3 className="w-5 h-5 text-[#d97706]" />
          <h2 className="text-base font-extrabold text-[#1e293b]">Visualizations</h2>
        </div>
        <span className="text-xs text-[#64748b] font-medium">
          {selected.length}/{visualizations.length} Selected
        </span>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-2.5">
        {visualizations.map((viz) => {
          const isSelected = selected.includes(viz)
          return (
            <button
              key={viz}
              onClick={() => onToggle(viz)}
              disabled={disabled}
              className={cn(
                "px-3 py-2.5 rounded-xl text-xs font-bold transition-all cursor-pointer",
                "border text-left flex items-center gap-2 min-w-0",
                isSelected
                  ? "border-[#d97706] bg-[#d97706]/15 text-[#b45309] shadow-xs"
                  : "border-[#e5dcd0] bg-[#faf8f5] text-[#1e293b] hover:border-[#d97706]/50",
                disabled && "opacity-50 cursor-not-allowed"
              )}
            >
              <div className={cn(
                "w-4 h-4 rounded border flex items-center justify-center shrink-0 transition-colors",
                isSelected ? "border-[#d97706] bg-[#d97706]" : "border-[#cbd5e1]"
              )}>
                {isSelected && (
                  <svg className="w-2.5 h-2.5 text-white stroke-[3]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                  </svg>
                )}
              </div>
              <span className="truncate leading-tight">{viz}</span>
            </button>
          )
        })}
      </div>
    </div>
  )
}
