'use client'

import { cn } from '@/lib/utils'
import { Play } from 'lucide-react'

interface DynamicFormProps {
  fileData?: Record<string, number[]>
  onSubmit: () => void
  loading?: boolean
}

export default function DynamicForm({ fileData, onSubmit, loading }: DynamicFormProps) {
  const getRowCount = () => {
    if (!fileData) return 0
    const firstKey = Object.keys(fileData)[0]
    return fileData[firstKey]?.length || 0
  }

  return (
    <div className="bg-card border rounded-lg p-6 shadow-sm">
      <div className="flex items-center gap-2 mb-4">
        <Play className="w-5 h-5 text-primary" />
        <h2 className="text-lg font-semibold">Generate Predictions</h2>
        {fileData && (
          <span className="text-xs text-muted-foreground ml-auto">
            {getRowCount()} rows loaded
          </span>
        )}
      </div>
      
      {!fileData ? (
        <div className="text-center py-8 text-muted-foreground">
          <Play className="w-12 h-12 mx-auto mb-2 opacity-50" />
          <p className="text-sm">Upload a CSV or Excel file to generate predictions</p>
        </div>
      ) : (
        <div className="space-y-4">
          <p className="text-sm text-muted-foreground">
            Click to generate predictions for all {getRowCount()} rows in the uploaded file.
          </p>
          
          <button
            onClick={onSubmit}
            disabled={loading}
            className={cn(
              "w-full py-3 px-4 rounded-md font-medium text-sm",
              "bg-primary text-primary-foreground",
              "hover:bg-primary/90",
              "focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2",
              "disabled:opacity-50 disabled:cursor-not-allowed",
              "transition-colors"
            )}
          >
            {loading ? 'Generating Predictions...' : 'Generate Predictions for All Rows'}
          </button>
        </div>
      )}
    </div>
  )
}
