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
    <div className="bg-card border rounded-lg p-6 shadow-sm">
      <div className="flex items-center gap-2 mb-4">
        <BrainCircuit className="w-5 h-5 text-primary" />
        <h2 className="text-lg font-semibold">Select Model</h2>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
        {AVAILABLE_MODELS.map((model) => (
          <button
            key={model.id}
            onClick={() => onSelect(model.id)}
            disabled={disabled}
            className={cn(
              'flex flex-col items-start px-4 py-3 rounded-md text-left transition-all',
              'border-2',
              selected === model.id
                ? 'border-primary bg-primary/10 text-primary'
                : 'border-border bg-background text-foreground hover:border-primary/50',
              disabled && 'opacity-50 cursor-not-allowed'
            )}
          >
            <span className="text-sm font-semibold">{model.label}</span>
            <span
              className={cn(
                'text-xs mt-1 leading-snug',
                selected === model.id ? 'text-primary/80' : 'text-muted-foreground'
              )}
            >
              {model.description}
            </span>
          </button>
        ))}
      </div>
    </div>
  )
}
