import { useState, useRef } from "react"
import { Upload, Download, AlertCircle, CheckCircle, FileX, ArrowRight, ArrowLeft, RefreshCw } from "lucide-react"
import { apiClient } from "@/services/api-client"
import { Button } from "@/components/ui/button"

interface MasterDataImportWizardProps {
  moduleName: string
  apiPrefix: string
  onComplete?: () => void
  onCancel?: () => void
}

interface PreviewStats {
  session_id: string
  total_rows: number
  valid_rows: number
  error_rows: number
}

type Step = "upload" | "preview" | "complete"

export function MasterDataImportWizard({ moduleName, apiPrefix, onComplete, onCancel }: MasterDataImportWizardProps) {
  const [step, setStep] = useState<Step>("upload")
  const [file, setFile] = useState<File | null>(null)
  const [isUploading, setIsUploading] = useState(false)
  const [previewStats, setPreviewStats] = useState<PreviewStats | null>(null)
  const [duplicateStrategy, setDuplicateStrategy] = useState<"SKIP" | "UPDATE" | "FAIL_IMPORT">("SKIP")
  const [isConfirming, setIsConfirming] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const handleDownloadTemplate = async () => {
    try {
      const response = await apiClient.get(`${apiPrefix}/import/template`, {
        responseType: "blob",
      })
      
      const url = window.URL.createObjectURL(new Blob([response.data]))
      const link = document.createElement("a")
      link.href = url
      link.setAttribute("download", `${moduleName}_template.xlsx`)
      document.body.appendChild(link)
      link.click()
      link.remove()
    } catch (err: any) {
      setError(err.message || "Failed to download template")
    }
  }

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0])
      setError(null)
    }
  }

  const handleUpload = async () => {
    if (!file) return
    setIsUploading(true)
    setError(null)

    try {
      const formData = new FormData()
      formData.append("file", file)
      
      const response = await apiClient.post(`${apiPrefix}/import/preview`, formData)
      
      setPreviewStats(response.data)
      setStep("preview")
    } catch (err: any) {
      setError(err.message || "Failed to upload file")
    } finally {
      setIsUploading(false)
    }
  }

  const handleConfirm = async () => {
    if (!previewStats) return
    setIsConfirming(true)
    setError(null)

    try {
      const formData = new FormData()
      formData.append("session_id", previewStats.session_id)
      formData.append("duplicate_strategy", duplicateStrategy)

      await apiClient.post(`${apiPrefix}/import/confirm`, formData)
      
      setStep("complete")
    } catch (err: any) {
      setError(err.message || "Failed to import data")
    } finally {
      setIsConfirming(false)
    }
  }

  const handleDownloadErrors = async () => {
    if (!previewStats) return
    try {
      const response = await apiClient.get(`${apiPrefix}/import/${previewStats.session_id}/errors`, {
        responseType: "blob",
      })
      
      const url = window.URL.createObjectURL(new Blob([response.data]))
      const link = document.createElement("a")
      link.href = url
      link.setAttribute("download", `${moduleName}_errors.xlsx`)
      document.body.appendChild(link)
      link.click()
      link.remove()
    } catch (err: any) {
      setError(err.message || "Failed to download errors")
    }
  }

  return (
    <div className="bg-white p-6 rounded-lg border shadow-sm max-w-2xl w-full">
      <h2 className="text-xl font-bold mb-6 capitalize text-slate-800">
        Import {moduleName.replace("-", " ")}
      </h2>

      {error && (
        <div className="mb-6 p-4 bg-red-50 text-red-700 rounded-md flex items-start gap-3 border border-red-200">
          <AlertCircle className="w-5 h-5 flex-shrink-0 mt-0.5" />
          <p className="text-sm font-medium">{error}</p>
        </div>
      )}

      {/* Step 1: Upload */}
      {step === "upload" && (
        <div className="space-y-6">
          <div className="p-4 bg-slate-50 rounded-md border border-slate-200">
            <h3 className="font-semibold text-slate-700 mb-2">Step 1: Download Template</h3>
            <p className="text-sm text-slate-600 mb-4">
              Download the Excel template. Do not change the column headers.
            </p>
            <Button variant="outline" onClick={handleDownloadTemplate} className="gap-2">
              <Download className="w-4 h-4" />
              Download Template
            </Button>
          </div>

          <div className="p-4 bg-slate-50 rounded-md border border-slate-200">
            <h3 className="font-semibold text-slate-700 mb-2">Step 2: Upload Data</h3>
            <p className="text-sm text-slate-600 mb-4">
              Upload your completed Excel file to preview the import.
            </p>
            
            <input
              type="file"
              accept=".xlsx,.xls"
              className="hidden"
              ref={fileInputRef}
              onChange={handleFileChange}
            />
            
            <div className="flex items-center gap-4">
              <Button 
                variant="outline" 
                onClick={() => fileInputRef.current?.click()}
                className="gap-2"
              >
                <Upload className="w-4 h-4" />
                Select File
              </Button>
              <span className="text-sm text-slate-600 truncate max-w-[200px]">
                {file ? file.name : "No file selected"}
              </span>
            </div>
          </div>

          <div className="flex justify-end gap-3 pt-4">
            <Button variant="ghost" onClick={onCancel}>Cancel</Button>
            <Button 
              onClick={handleUpload} 
              disabled={!file || isUploading}
              className="gap-2"
            >
              {isUploading ? <RefreshCw className="w-4 h-4 animate-spin" /> : <ArrowRight className="w-4 h-4" />}
              Preview Import
            </Button>
          </div>
        </div>
      )}

      {/* Step 2: Preview */}
      {step === "preview" && previewStats && (
        <div className="space-y-6">
          <div className="grid grid-cols-3 gap-4">
            <div className="p-4 bg-blue-50 border border-blue-200 rounded-md text-center">
              <div className="text-2xl font-bold text-blue-700">{previewStats.total_rows}</div>
              <div className="text-xs font-medium text-blue-600 uppercase tracking-wider">Total Rows</div>
            </div>
            <div className="p-4 bg-emerald-50 border border-emerald-200 rounded-md text-center">
              <div className="text-2xl font-bold text-emerald-700">{previewStats.valid_rows}</div>
              <div className="text-xs font-medium text-emerald-600 uppercase tracking-wider">Valid Rows</div>
            </div>
            <div className="p-4 bg-red-50 border border-red-200 rounded-md text-center">
              <div className="text-2xl font-bold text-red-700">{previewStats.error_rows}</div>
              <div className="text-xs font-medium text-red-600 uppercase tracking-wider">Errors</div>
            </div>
          </div>

          {previewStats.error_rows > 0 && (
            <div className="p-4 bg-amber-50 border border-amber-200 rounded-md flex items-start gap-4">
              <AlertCircle className="w-5 h-5 text-amber-600 flex-shrink-0 mt-0.5" />
              <div>
                <h4 className="font-semibold text-amber-800">Fix Errors Before Importing</h4>
                <p className="text-sm text-amber-700 mt-1 mb-3">
                  {previewStats.error_rows} rows have validation errors and will be skipped. Download the error report to see what went wrong.
                </p>
                <Button variant="outline" size="sm" onClick={handleDownloadErrors} className="gap-2 bg-white">
                  <FileX className="w-4 h-4" />
                  Download Error Report
                </Button>
              </div>
            </div>
          )}

          <div className="space-y-3">
            <label className="block text-sm font-semibold text-slate-700">Duplicate Handling Strategy</label>
            <div className="space-y-2">
              <label className="flex items-center gap-3 p-3 border rounded-md cursor-pointer hover:bg-slate-50">
                <input 
                  type="radio" 
                  name="strategy" 
                  value="SKIP" 
                  checked={duplicateStrategy === "SKIP"} 
                  onChange={() => setDuplicateStrategy("SKIP")} 
                  className="w-4 h-4 text-blue-600"
                />
                <div>
                  <div className="font-medium text-slate-800">Skip Duplicates (Recommended)</div>
                  <div className="text-sm text-slate-500">Ignore rows where code already exists.</div>
                </div>
              </label>
              
              <label className="flex items-center gap-3 p-3 border rounded-md cursor-pointer hover:bg-slate-50">
                <input 
                  type="radio" 
                  name="strategy" 
                  value="UPDATE" 
                  checked={duplicateStrategy === "UPDATE"} 
                  onChange={() => setDuplicateStrategy("UPDATE")} 
                  className="w-4 h-4 text-blue-600"
                />
                <div>
                  <div className="font-medium text-slate-800">Update Existing</div>
                  <div className="text-sm text-slate-500">Overwrite existing records with new data.</div>
                </div>
              </label>
              
              <label className="flex items-center gap-3 p-3 border rounded-md cursor-pointer hover:bg-slate-50">
                <input 
                  type="radio" 
                  name="strategy" 
                  value="FAIL_IMPORT" 
                  checked={duplicateStrategy === "FAIL_IMPORT"} 
                  onChange={() => setDuplicateStrategy("FAIL_IMPORT")} 
                  className="w-4 h-4 text-blue-600"
                />
                <div>
                  <div className="font-medium text-slate-800">Fail Entire Import</div>
                  <div className="text-sm text-slate-500">Stop import if any duplicates are found.</div>
                </div>
              </label>
            </div>
          </div>

          <div className="flex justify-between pt-4 border-t">
            <Button variant="ghost" onClick={() => setStep("upload")} className="gap-2">
              <ArrowLeft className="w-4 h-4" />
              Back
            </Button>
            <Button 
              onClick={handleConfirm} 
              disabled={isConfirming || previewStats.valid_rows === 0}
              className="gap-2 bg-blue-600 hover:bg-blue-700"
            >
              {isConfirming ? <RefreshCw className="w-4 h-4 animate-spin" /> : <CheckCircle className="w-4 h-4" />}
              Confirm & Import
            </Button>
          </div>
        </div>
      )}

      {/* Step 3: Complete */}
      {step === "complete" && (
        <div className="text-center py-8 space-y-6">
          <div className="mx-auto w-16 h-16 bg-emerald-100 rounded-full flex items-center justify-center">
            <CheckCircle className="w-8 h-8 text-emerald-600" />
          </div>
          <div>
            <h3 className="text-2xl font-bold text-slate-800">Import Successful</h3>
            <p className="text-slate-600 mt-2">
              The data has been successfully imported into the system.
            </p>
          </div>
          <Button onClick={onComplete} className="mt-4">
            Finish
          </Button>
        </div>
      )}
    </div>
  )
}
