import { Outlet } from "react-router-dom"
import { useUIStore } from "@/app/store/uiStore"
import { PlatformSidebar } from "./PlatformSidebar"
import { TopBar } from "@/components/layout/TopBar"
import { Toaster } from "@/components/ui/toaster"
import { cn } from "@/lib/utils"

export function PlatformLayout() {
  const { isSidebarOpen } = useUIStore()

  return (
    <>
      <div className="flex min-h-screen w-full flex-col bg-background">
        <PlatformSidebar />

        <div
          className={cn(
            "flex min-h-screen flex-col transition-all duration-300",
            isSidebarOpen ? "md:pl-72" : "md:pl-20"
          )}
        >
          <TopBar />
          
          <main className="flex-1 px-3 pb-28 pt-4 sm:px-4 md:px-6 md:pb-10 md:pt-5 lg:px-8">
            <div className="mx-auto flex w-full max-w-[1600px] flex-col gap-4 md:gap-6">
              <Outlet />
            </div>
          </main>
        </div>
      </div>
      <Toaster />
    </>
  )
}
