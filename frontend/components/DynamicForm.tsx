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
    <div className="bg-[#f4efe8] border border-[#e8dfd3] rounded-2xl p-6 shadow-2xs">
      <div className="flex items-center gap-2 mb-4">
        <Play className="w-5 h-5 text-[#d97706]" />
        <h2 className="text-base font-extrabold text-[#1e293b]">Generate Predictions</h2>
        {fileData && (
          <span className="text-xs text-[#64748b] ml-auto font-medium bg-[#e5dcd0] px-2.5 py-1 rounded-full">
            {getRowCount()} rows loaded
          </span>
        )}
      </div>
      
      {!fileData ? (
        <div className="text-center py-6 text-[#64748b]">
          <Play className="w-10 h-10 mx-auto mb-2 opacity-40 text-[#1e293b]" />
          <p className="text-xs font-medium">Upload a CSV or Excel file (or click &quot;Load Sample Dataset&quot; above) to generate predictions</p>
        </div>
      ) : (
        <div className="space-y-4">
          <p className="text-xs text-[#64748b]">
            Click to generate predictions for all <span className="font-bold text-[#1e293b]">{getRowCount()}</span> rows in the dataset.
          </p>
          
          <button
            onClick={onSubmit}
            disabled={loading}
            className={cn(
              "w-full py-3 px-4 rounded-xl font-bold text-xs tracking-wide cursor-pointer",
              "bg-[#1e293b] text-white",
              "hover:bg-[#0f172a]",
              "disabled:opacity-50 disabled:cursor-not-allowed",
              "transition-all shadow-sm"
            )}
          >
            {loading ? 'Generating Predictions...' : 'Generate Predictions for All Rows'}
          </button>
        </div>
      )}
    </div>
  )
}
