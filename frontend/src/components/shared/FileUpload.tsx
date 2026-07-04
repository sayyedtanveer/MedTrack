import { useState, useRef } from "react"
import { Button } from "@/components/ui/button"
import { UploadCloud, X, File as FileIcon } from "lucide-react"

interface FileUploadProps {
  onFileSelect: (file: File) => void
  accept?: string
  maxSizeMB?: number
  currentFile?: File | null
  onClear?: () => void
}

export function FileUpload({
  onFileSelect,
  accept = "image/*,.pdf",
  maxSizeMB = 5,
  currentFile,
  onClear
}: FileUploadProps) {
  const [dragActive, setDragActive] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true)
    } else if (e.type === "dragleave") {
      setDragActive(false)
    }
  }

  const validateAndProcessFile = (file: File) => {
    setError(null)
    const validTypes = accept.split(",").map(t => t.trim())
    
    // Check type if accept is specific
    if (accept && accept !== "*") {
      const fileExt = `.${file.name.split('.').pop()?.toLowerCase()}`
      const isTypeMatch = validTypes.some(type => {
        if (type.startsWith(".")) return fileExt === type
        if (type.endsWith("/*")) return file.type.startsWith(type.replace("/*", ""))
        return file.type === type
      })
      
      if (!isTypeMatch) {
        setError("Invalid file type.")
        return
      }
    }

    // Check size
    if (file.size > maxSizeMB * 1024 * 1024) {
      setError(`File must be smaller than ${maxSizeMB}MB.`)
      return
    }

    onFileSelect(file)
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setDragActive(false)
    
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      validateAndProcessFile(e.dataTransfer.files[0])
    }
  }

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    e.preventDefault()
    if (e.target.files && e.target.files[0]) {
      validateAndProcessFile(e.target.files[0])
    }
  }

  return (
    <div className="w-full">
      {currentFile ? (
        <div className="flex items-center justify-between p-4 border rounded-md bg-muted/20">
          <div className="flex items-center space-x-3 overflow-hidden">
            <FileIcon className="h-8 w-8 text-primary flex-shrink-0" />
            <div className="truncate">
              <p className="text-sm font-medium truncate">{currentFile.name}</p>
              <p className="text-xs text-muted-foreground">{(currentFile.size / 1024 / 1024).toFixed(2)} MB</p>
            </div>
          </div>
          {onClear && (
            <Button variant="ghost" size="icon" onClick={onClear} aria-label="Clear file">
              <X className="h-4 w-4" />
            </Button>
          )}
        </div>
      ) : (
        <div
          className={`relative flex flex-col items-center justify-center p-8 border-2 border-dashed rounded-lg transition-colors ${
            dragActive ? "border-primary bg-primary/5" : "border-border hover:border-primary/50"
          }`}
          onDragEnter={handleDrag}
          onDragLeave={handleDrag}
          onDragOver={handleDrag}
          onDrop={handleDrop}
        >
          <input
            ref={inputRef}
            type="file"
            className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
            accept={accept}
            onChange={handleChange}
          />
          <UploadCloud className="h-10 w-10 text-muted-foreground mb-4" />
          <p className="text-sm font-medium mb-1">Click or drag file to this area to upload</p>
          <p className="text-xs text-muted-foreground text-center">
            Support for a single upload. Maximum file size {maxSizeMB}MB. <br />
            Formats: {accept}
          </p>
          {error && <p className="text-sm text-destructive mt-4 font-medium">{error}</p>}
        </div>
      )}
    </div>
  )
}
