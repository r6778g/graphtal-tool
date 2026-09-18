'use client'

import { BrainCircuit } from 'lucide-react'
import { cn } from '@/lib/utils'

export const AVAILABLE_MODELS = [
  {
    id: 'random_forest',
    label: 'Random Forest',
    description: 'Ensemble of decision trees, robust to outliers',
  },
  {
    id: 'svm',
    label: 'SVM',
    description: 'Support Vector Machine with RBF kernel',
  },
  {
    id: 'lasso',
    label: 'Lasso Regression',
    description: 'L1-regularized linear regression',
  },
  {
    id: 'ridge',
    label: 'Ridge Regression',
    description: 'L2-regularized linear regression (default)',
  },
]

interface ModelSelectorProps {
  selected: string
  onSelect: (modelId: string) => void
  disabled?: boolean
}

export default function ModelSelector({ selected, onSelect, disabled }: ModelSelectorProps) {
  return (
    <div className="bg-[#f4efe8] border border-[#e8dfd3] rounded-2xl p-6 shadow-2xs h-full flex flex-col justify-between">
      <div>
        <div className="flex items-center gap-2 mb-4">
          <BrainCircuit className="w-5 h-5 text-[#d97706]" />
          <h2 className="text-base font-extrabold text-[#1e293b]">Select Model</h2>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {AVAILABLE_MODELS.map((model) => (
            <button
              key={model.id}
              onClick={() => onSelect(model.id)}
              disabled={disabled}
              className={cn(
                'flex flex-col items-start p-3.5 rounded-xl text-left transition-all min-w-0 cursor-pointer',
                'border',
                selected === model.id
                  ? 'border-[#d97706] bg-[#d97706]/15 text-[#b45309] shadow-xs'
                  : 'border-[#e5dcd0] bg-[#faf8f5] text-[#1e293b] hover:border-[#d97706]/50',
                disabled && 'opacity-50 cursor-not-allowed'
              )}
            >
              <span className="text-xs font-bold leading-tight truncate w-full">{model.label}</span>
              <span
                className={cn(
                  'text-[11px] mt-1 leading-snug line-clamp-2',
                  selected === model.id ? 'text-[#b45309] font-medium' : 'text-[#64748b]'
                )}
              >
                {model.description}
              </span>
            </button>
          ))}
        </div>
      </div>
    </div>
  )
}
