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
    <div className="bg-card border rounded-lg p-6 shadow-sm">
      <div className="flex items-center gap-2 mb-4">
        <BarChart3 className="w-5 h-5 text-primary" />
        <h2 className="text-lg font-semibold">Visualizations</h2>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
        {visualizations.map((viz) => (
          <button
            key={viz}
            onClick={() => onToggle(viz)}
            disabled={disabled}
            className={cn(
              "px-4 py-3 rounded-md text-sm font-medium transition-all",
              "border-2 text-left",
              selected.includes(viz)
                ? "border-primary bg-primary/10 text-primary"
                : "border-border bg-background text-foreground hover:border-primary/50",
              disabled && "opacity-50 cursor-not-allowed",
              "flex items-center gap-2"
            )}
          >
            <div className={cn(
              "w-4 h-4 rounded border-2 flex items-center justify-center",
              selected.includes(viz) ? "border-primary bg-primary" : "border-border"
            )}>
              {selected.includes(viz) && (
                <svg className="w-3 h-3 text-white" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                </svg>
              )}
            </div>
            {viz}
          </button>
        ))}
      </div>
    </div>
  )
}
