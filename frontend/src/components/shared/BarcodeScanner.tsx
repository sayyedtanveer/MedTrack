import { useState, useRef, useEffect } from "react"
import { BrowserMultiFormatReader, NotFoundException } from "@zxing/library"
import { Button } from "@/components/ui/button"
import { Camera, X } from "lucide-react"

interface BarcodeScannerProps {
  onScan: (data: string) => void
  onClose: () => void
}

export function BarcodeScanner({ onScan, onClose }: BarcodeScannerProps) {
  const [error, setError] = useState<string | null>(null)
  const videoRef = useRef<HTMLVideoElement>(null)
  const codeReaderRef = useRef<BrowserMultiFormatReader | null>(null)

  useEffect(() => {
    codeReaderRef.current = new BrowserMultiFormatReader()
    const reader = codeReaderRef.current

    let isMounted = true

    reader.listVideoInputDevices()
      .then((videoInputDevices) => {
        if (!isMounted) return

        if (videoInputDevices.length > 0) {
          // Use the first available camera (usually rear camera on mobile if we select properly, 
          // but library default is usually okay for first pass)
          const firstDeviceId = videoInputDevices[0].deviceId
          
          if (videoRef.current) {
            reader.decodeFromVideoDevice(firstDeviceId, videoRef.current, (result, err) => {
              if (result && isMounted) {
                // Play a beep sound here if desired
                onScan(result.getText())
              }
              if (err && !(err instanceof NotFoundException)) {
                // Real error
                console.error(err)
              }
            })
          }
        } else {
          setError("No cameras found on this device.")
        }
      })
      .catch((err) => {
        if (isMounted) {
          console.error(err)
          setError("Camera permission denied or camera not available.")
        }
      })

    return () => {
      isMounted = false
      if (reader) {
        reader.reset()
      }
    }
  }, [onScan])

  return (
    <div className="relative flex flex-col items-center justify-center bg-black rounded-lg overflow-hidden h-[300px] sm:h-[400px]">
      {error ? (
        <div className="text-destructive text-center p-4">
          <Camera className="h-10 w-10 mx-auto mb-2 opacity-50" />
          <p>{error}</p>
        </div>
      ) : (
        <video 
          ref={videoRef} 
          className="w-full h-full object-cover"
          playsInline
        />
      )}
      
      {/* Target overlay */}
      <div className="absolute inset-0 pointer-events-none flex items-center justify-center">
        <div className="w-64 h-32 border-2 border-primary/50 relative">
          {/* Scanning animation line */}
          <div className="absolute left-0 right-0 h-0.5 bg-primary animate-[scan_2s_ease-in-out_infinite]" />
        </div>
      </div>

      <Button
        variant="destructive"
        size="icon"
        className="absolute top-2 right-2 rounded-full"
        onClick={onClose}
        aria-label="Close scanner"
      >
        <X className="h-4 w-4" />
      </Button>

      {/* Tailwind scan animation added to tailwind config would be better, adding inline keyframes here for simplicity if needed, but assuming a generic animate pulse for now if not defined */}
      <style>{`
        @keyframes scan {
          0% { top: 0%; opacity: 0; }
          10% { opacity: 1; }
          90% { opacity: 1; }
          100% { top: 100%; opacity: 0; }
        }
      `}</style>
    </div>
  )
}
