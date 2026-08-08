'use client'

import { useEffect, useState } from 'react'
import { Lightbulb, ChevronDown, ChevronUp } from 'lucide-react'
import { cn } from '@/lib/utils'

interface ModelRecommendationProps {
  target: string
  fileData?: Record<string, number[]>
  onModelSelect?: (model: string) => void
  currentModel?: string
}

interface Recommendation {
  recommended_model: string
  reason: string
  alternatives: Array<{
    model: string
    reason: string
  }>
  dataset_info: {
    num_rows: number
    num_features: number
    target: string
  }
}

export default function ModelRecommendation({ 
  target, 
  fileData, 
  onModelSelect,
  currentModel 
}: ModelRecommendationProps) {
  const [recommendation, setRecommendation] = useState<Recommendation | null>(null)
  const [loading, setLoading] = useState(false)
  const [expanded, setExpanded] = useState(true)

  useEffect(() => {
    if (fileData && target) {
      fetchRecommendation()
    }
  }, [fileData, target])

  const fetchRecommendation = async () => {
    if (!fileData || !target) return

    setLoading(true)
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
      const response = await fetch(`${apiUrl}/recommend-model`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          target,
          file_data: fileData
        })
      })

      if (response.ok) {
        const data = await response.json()
        setRecommendation(data)
      }
    } catch (error) {
      console.error('Failed to fetch recommendation:', error)
    } finally {
      setLoading(false)
    }
  }

  if (!fileData || !recommendation) {
    return null
  }

  return (
    <div className="bg-gradient-to-br from-primary/5 to-primary/10 border border-primary/20 rounded-lg p-6 shadow-sm">
      <div 
        className="flex items-center justify-between cursor-pointer"
        onClick={() => setExpanded(!expanded)}
      >
        <div className="flex items-center gap-3">
          <Lightbulb className="w-5 h-5 text-primary" />
          <div>
            <h3 className="text-lg font-semibold text-primary">Model Recommendation</h3>
            <p className="text-sm text-muted-foreground">
              Based on your dataset analysis
            </p>
          </div>
        </div>
        {expanded ? (
          <ChevronUp className="w-5 h-5 text-muted-foreground" />
        ) : (
          <ChevronDown className="w-5 h-5 text-muted-foreground" />
        )}
      </div>

      {expanded && (
        <div className="mt-4 space-y-4">
          {loading ? (
            <div className="text-sm text-muted-foreground">Analyzing dataset...</div>
          ) : (
            <>
              <div className="bg-background rounded-lg p-4 border">
                <div className="flex items-start justify-between mb-2">
                  <div>
                    <p className="text-sm font-medium text-muted-foreground">Recommended Model</p>
                    <p className="text-xl font-bold text-primary capitalize">
                      {recommendation.recommended_model.replace('_', ' ')}
                    </p>
                  </div>
                  {currentModel !== recommendation.recommended_model && (
                    <button
                      onClick={() => onModelSelect?.(recommendation.recommended_model)}
                      className="px-3 py-1 bg-primary text-primary-foreground text-sm rounded-md hover:bg-primary/90 transition-colors"
                    >
                      Use This Model
                    </button>
                  )}
                </div>
                <p className="text-sm text-muted-foreground mt-2">
                  {recommendation.reason}
                </p>
              </div>

              <div>
                <p className="text-sm font-medium mb-2">Dataset Information</p>
                <div className="flex gap-4 text-sm">
                  <div className="bg-background rounded px-3 py-2 border">
                    <span className="text-muted-foreground">Rows:</span>{' '}
                    <span className="font-medium">{recommendation.dataset_info.num_rows}</span>
                  </div>
                  <div className="bg-background rounded px-3 py-2 border">
                    <span className="text-muted-foreground">Features:</span>{' '}
                    <span className="font-medium">{recommendation.dataset_info.num_features}</span>
                  </div>
                </div>
              </div>

              <div>
                <p className="text-sm font-medium mb-2">Alternative Models</p>
                <div className="space-y-2">
                  {recommendation.alternatives.map((alt) => (
                    <div
                      key={alt.model}
                      className={cn(
                        "bg-background rounded-lg p-3 border cursor-pointer transition-colors",
                        currentModel === alt.model && "border-primary bg-primary/5"
                      )}
                      onClick={() => onModelSelect?.(alt.model)}
                    >
                      <div className="flex items-center justify-between">
                        <div>
                          <p className="text-sm font-medium capitalize">
                            {alt.model.replace('_', ' ')}
                          </p>
                          <p className="text-xs text-muted-foreground mt-1">
                            {alt.reason}
                          </p>
                        </div>
                        {currentModel === alt.model && (
                          <span className="text-xs px-2 py-1 bg-primary text-primary-foreground rounded">
                            Selected
                          </span>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </>
          )}
        </div>
      )}
    </div>
  )
}
