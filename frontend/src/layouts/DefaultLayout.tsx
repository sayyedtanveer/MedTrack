import { useState } from "react"
import { Outlet } from "react-router-dom"
import { Barcode } from "lucide-react"
import { useUIStore } from "@/app/store/uiStore"
import { Sidebar } from "@/components/layout/Sidebar"
import { TopBar } from "@/components/layout/TopBar"
import { Breadcrumb } from "@/components/layout/Breadcrumb"
import { BottomNavigation } from "@/components/navigation/BottomNavigation"
import { FloatingActionButton } from "@/components/mobile/FloatingActionButton"
import { BarcodeScannerModal } from "@/components/barcode/BarcodeScannerModal"
import { Toaster } from "@/components/ui/toaster"
import { OfflineIndicator } from "@/components/offline/OfflineIndicator"
import { InstallPrompt } from "@/components/pwa/InstallPrompt"
import { cn } from "@/lib/utils"

export default function DefaultLayout() {
  const { isSidebarOpen } = useUIStore()
  const [scannerOpen, setScannerOpen] = useState(false)

  const handleBarcodeScan = (barcode: string) => {
    console.log("Scanned barcode:", barcode)
  }

  return (
    <>
      <div className="flex min-h-screen w-full flex-col bg-background">
        <Sidebar />

        <div
          className={cn(
            "flex min-h-screen flex-col transition-all duration-300",
            isSidebarOpen ? "md:pl-72" : "md:pl-20"
          )}
        >
          <TopBar />
          
          <main className="flex-1 px-3 pb-28 pt-4 sm:px-4 md:px-6 md:pb-10 md:pt-5 lg:px-8">
            <div className="mx-auto flex w-full max-w-[1600px] flex-col gap-4 md:gap-6">
              <Breadcrumb />
              <Outlet />
            </div>
          </main>
        </div>
      </div>

      {/* Global UI Components */}
      <Toaster />
      <OfflineIndicator />
      <BottomNavigation />
      <InstallPrompt />
      
      {/* Floating Action Button - Barcode Scanner */}
      <FloatingActionButton
        icon={Barcode}
        label="Scan"
        onClick={() => setScannerOpen(true)}
      />
      
      {/* Barcode Scanner Modal */}
      <BarcodeScannerModal
        isOpen={scannerOpen}
        onClose={() => setScannerOpen(false)}
        onScan={handleBarcodeScan}
        title="Scan Work Order or Material"
        description="Point camera at barcode"
      />
    </>
  )
}
