'use client'

import { Target } from 'lucide-react'
import { cn } from '@/lib/utils'

interface OutputSelectorProps {
  outputs: string[]
  selected: string
  onSelect: (output: string) => void
  disabled?: boolean
}

export default function OutputSelector({ outputs, selected, onSelect, disabled }: OutputSelectorProps) {
  return (
    <div className="bg-card border rounded-lg p-6 shadow-sm">
      <div className="flex items-center gap-2 mb-4">
        <Target className="w-5 h-5 text-primary" />
        <h2 className="text-lg font-semibold">Prediction Target</h2>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
        {outputs.map((output) => (
          <button
            key={output}
            onClick={() => onSelect(output)}
            disabled={disabled}
            className={cn(
              "px-4 py-2.5 rounded-md text-sm font-medium transition-all",
              "border-2",
              selected === output
                ? "border-primary bg-primary/10 text-primary"
                : "border-border bg-background text-foreground hover:border-primary/50",
              disabled && "opacity-50 cursor-not-allowed"
            )}
          >
            {output}
          </button>
        ))}
      </div>
    </div>
  )
}
