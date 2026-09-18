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
    <div className="bg-[#f4efe8] border border-[#e8dfd3] rounded-2xl p-6 shadow-2xs h-full flex flex-col justify-between">
      <div>
        <div className="flex items-center gap-2 mb-4">
          <Target className="w-5 h-5 text-[#d97706]" />
          <h2 className="text-base font-extrabold text-[#1e293b]">Prediction Target</h2>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-2.5">
          {outputs.map((output) => (
            <button
              key={output}
              onClick={() => onSelect(output)}
              disabled={disabled}
              className={cn(
                "px-3.5 py-2.5 rounded-xl text-xs font-bold transition-all text-center truncate cursor-pointer",
                "border",
                selected === output
                  ? "border-[#d97706] bg-[#d97706]/15 text-[#b45309] shadow-xs"
                  : "border-[#e5dcd0] bg-[#faf8f5] text-[#1e293b] hover:border-[#d97706]/50",
                disabled && "opacity-50 cursor-not-allowed"
              )}
            >
              {output}
            </button>
          ))}
        </div>
      </div>
    </div>
  )
}
