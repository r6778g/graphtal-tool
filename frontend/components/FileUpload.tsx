'use client'

import { useState, useCallback } from 'react'
import { Upload, FileText, X, CheckCircle, AlertCircle } from 'lucide-react'
import { cn } from '@/lib/utils'
import Papa from 'papaparse'
import * as XLSX from 'xlsx'

interface FileUploadProps {
  onDataLoaded: (data: Record<string, number[]>) => void
  onParametersSelected?: (parameters: string[]) => void
  loading?: boolean
}

export default function FileUpload({ onDataLoaded, onParametersSelected, loading }: FileUploadProps) {
  const [file, setFile] = useState<File | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState(false)
  const [processing, setProcessing] = useState(false)
  const [detectedColumns, setDetectedColumns] = useState<string[]>([])
  const [selectedParameters, setSelectedParameters] = useState<Set<string>>(new Set())

  const processCSV = useCallback((file: File) => {
    return new Promise<Record<string, number[]>>((resolve, reject) => {
      Papa.parse(file, {
        header: true,
        dynamicTyping: true,
        skipEmptyLines: true,
        complete: (results) => {
          try {
            const data: Record<string, number[]> = {}
            const headers = results.meta.fields || []
            
            headers.forEach(header => {
              data[header] = results.data
                .map((row: any) => parseFloat(row[header]))
                .filter((val: number) => !isNaN(val))
            })
            
            resolve(data)
          } catch (err) {
            reject(err)
          }
        },
        error: (err) => reject(err)
      })
    })
  }, [])

  const processExcel = useCallback((file: File) => {
    return new Promise<Record<string, number[]>>((resolve, reject) => {
      const reader = new FileReader()
      
      reader.onload = (e) => {
        try {
          const data = e.target?.result
          const workbook = XLSX.read(data, { type: 'binary' })
          const sheetName = workbook.SheetNames[0]
          const worksheet = workbook.Sheets[sheetName]
          const jsonData = XLSX.utils.sheet_to_json(worksheet, { header: 1 })
          
          if (jsonData.length < 2) {
            reject(new Error('Excel file is empty or has no data'))
            return
          }
          
          const headers = jsonData[0] as string[]
          const rows = jsonData.slice(1) as any[][]
          
          const result: Record<string, number[]> = {}
          
          headers.forEach((header, index) => {
            result[header] = rows
              .map(row => parseFloat(row[index]))
              .filter(val => !isNaN(val))
          })
          
          resolve(result)
        } catch (err) {
          reject(err)
        }
      }
      
      reader.onerror = () => reject(new Error('Failed to read file'))
      reader.readAsBinaryString(file)
    })
  }, [])

  const handleFileSelect = useCallback(async (selectedFile: File) => {
    setError(null)
    setSuccess(false)
    setProcessing(true)
    
    const validTypes = [
      'text/csv',
      'application/vnd.ms-excel',
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
      'application/vnd.ms-excel.sheet.macroEnabled.12'
    ]
    
    const fileExtension = selectedFile.name.split('.').pop()?.toLowerCase()
    const validExtensions = ['csv', 'xls', 'xlsx']
    
    if (!validExtensions.includes(fileExtension || '')) {
      setError('Please upload a CSV or Excel file (.csv, .xls, .xlsx)')
      setProcessing(false)
      return
    }
    
    try {
      let parsedData: Record<string, number[]>
      
      if (fileExtension === 'csv') {
        parsedData = await processCSV(selectedFile)
      } else {
        parsedData = await processExcel(selectedFile)
      }
      
      if (Object.keys(parsedData).length === 0) {
        setError('No valid numeric data found in the file')
        setProcessing(false)
        return
      }
      
      setFile(selectedFile)
      setSuccess(true)
      const columns = Object.keys(parsedData)
      setDetectedColumns(columns)
      setSelectedParameters(new Set(columns))
      onDataLoaded(parsedData)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to process file')
    } finally {
      setProcessing(false)
    }
  }, [processCSV, processExcel, onDataLoaded])

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    const droppedFile = e.dataTransfer.files[0]
    if (droppedFile) {
      handleFileSelect(droppedFile)
    }
  }, [handleFileSelect])

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault()
  }, [])

  const handleFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0]
    if (selectedFile) {
      handleFileSelect(selectedFile)
    }
  }

  const clearFile = () => {
    setFile(null)
    setError(null)
    setSuccess(false)
    setDetectedColumns([])
    setSelectedParameters(new Set())
  }

  const toggleParameter = (parameter: string) => {
    setSelectedParameters(prev => {
      const newSet = new Set(prev)
      if (newSet.has(parameter)) {
        newSet.delete(parameter)
      } else {
        newSet.add(parameter)
      }
      onParametersSelected?.(Array.from(newSet))
      return newSet
    })
  }

  const selectAllParameters = () => {
    setSelectedParameters(new Set(detectedColumns))
    onParametersSelected?.(detectedColumns)
  }

  const deselectAllParameters = () => {
    setSelectedParameters(new Set())
    onParametersSelected?.([])
  }

  return (
    <div className="bg-card border rounded-lg p-6 shadow-sm">
      <div className="flex items-center gap-2 mb-4">
        <Upload className="w-5 h-5 text-primary" />
        <h2 className="text-lg font-semibold">Upload Data File</h2>
      </div>

      {!file ? (
        <div
          onDrop={handleDrop}
          onDragOver={handleDragOver}
          className={cn(
            "border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors",
            "hover:border-primary/50 hover:bg-primary/5",
            processing && "pointer-events-none opacity-50"
          )}
        >
          <input
            type="file"
            accept=".csv,.xls,.xlsx"
            onChange={handleFileInput}
            disabled={processing || loading}
            className="hidden"
            id="file-upload"
          />
          <label
            htmlFor="file-upload"
            className="flex flex-col items-center gap-3 cursor-pointer"
          >
            <FileText className="w-12 h-12 text-muted-foreground" />
            <div>
              <p className="text-sm font-medium">
                {processing ? 'Processing file...' : 'Click to upload or drag and drop'}
              </p>
              <p className="text-xs text-muted-foreground mt-1">
                CSV or Excel files (.csv, .xls, .xlsx)
              </p>
            </div>
          </label>
        </div>
      ) : (
        <div className="space-y-4">
          <div className="flex items-center justify-between p-4 bg-secondary rounded-lg">
            <div className="flex items-center gap-3">
              <FileText className="w-8 h-8 text-primary" />
              <div>
                <p className="text-sm font-medium">{file.name}</p>
                <p className="text-xs text-muted-foreground">
                  {(file.size / 1024).toFixed(2)} KB
                </p>
              </div>
            </div>
            <button
              onClick={clearFile}
              disabled={loading}
              className={cn(
                "p-2 rounded-md hover:bg-destructive/10 text-muted-foreground hover:text-destructive",
                "transition-colors",
                loading && "opacity-50 cursor-not-allowed"
              )}
            >
              <X className="w-4 h-4" />
            </button>
          </div>

          {success && (
            <div className="space-y-3">
              <div className="flex items-center gap-2 text-sm text-green-600 dark:text-green-400">
                <CheckCircle className="w-4 h-4" />
                <span>File processed successfully</span>
              </div>
              <div className="bg-secondary/50 rounded-lg p-4">
                <div className="flex items-center justify-between mb-3">
                  <p className="text-sm font-medium">Select Input Parameters ({selectedParameters.size}/{detectedColumns.length}):</p>
                  <div className="flex gap-2">
                    <button
                      onClick={selectAllParameters}
                      disabled={loading}
                      className="text-xs px-2 py-1 bg-primary/10 hover:bg-primary/20 text-primary rounded transition-colors disabled:opacity-50"
                    >
                      Select All
                    </button>
                    <button
                      onClick={deselectAllParameters}
                      disabled={loading}
                      className="text-xs px-2 py-1 bg-destructive/10 hover:bg-destructive/20 text-destructive rounded transition-colors disabled:opacity-50"
                    >
                      Deselect All
                    </button>
                  </div>
                </div>
                <div className="flex flex-wrap gap-2">
                  {detectedColumns.map((column) => (
                    <button
                      key={column}
                      onClick={() => toggleParameter(column)}
                      disabled={loading}
                      className={cn(
                        "px-3 py-1 text-xs rounded-full border transition-colors cursor-pointer",
                        selectedParameters.has(column)
                          ? "bg-primary text-primary-foreground border-primary"
                          : "bg-primary/10 text-primary border-primary/20 hover:bg-primary/20",
                        loading && "opacity-50 cursor-not-allowed"
                      )}
                    >
                      {column}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          )}

          {error && (
            <div className="flex items-center gap-2 text-sm text-destructive">
              <AlertCircle className="w-4 h-4" />
              <span>{error}</span>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
