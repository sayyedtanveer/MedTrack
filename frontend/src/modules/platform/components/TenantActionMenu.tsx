import { useState } from "react"
import { MoreHorizontal, CheckCircle, XCircle, Ban, RefreshCw, AlertCircle } from "lucide-react"
import { Button } from "@/components/ui/button"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { SystemTenant } from "../types/platform"
import {
  useApproveTenant,
  useRejectTenant,
  useSuspendTenant,
  useReactivateTenant,
} from "../hooks/usePlatformTenants"

interface TenantActionMenuProps {
  tenant: SystemTenant
  variant?: "dropdown" | "buttons"
}

export function TenantActionMenu({ tenant, variant = "dropdown" }: TenantActionMenuProps) {
  const [isRejectOpen, setIsRejectOpen] = useState(false)
  const [isSuspendOpen, setIsSuspendOpen] = useState(false)
  const [reason, setReason] = useState("")

  const approve = useApproveTenant()
  const reject = useRejectTenant()
  const suspend = useSuspendTenant()
  const reactivate = useReactivateTenant()

  const handleApprove = () => {
    approve.mutate(tenant.id)
  }

  const handleReject = () => {
    if (!reason.trim()) return
    reject.mutate({ tenantId: tenant.id, data: { reason } }, {
      onSuccess: () => {
        setIsRejectOpen(false)
        setReason("")
      }
    })
  }

  const handleSuspend = () => {
    if (!reason.trim()) return
    suspend.mutate({ tenantId: tenant.id, data: { reason } }, {
      onSuccess: () => {
        setIsSuspendOpen(false)
        setReason("")
      }
    })
  }

  const handleReactivate = () => {
    reactivate.mutate(tenant.id)
  }

  // Allow approval if pending
  const canApprove = tenant.status === "pending"
  // Allow reject if pending
  const canReject = tenant.status === "pending"
  // Allow suspend if active
  const canSuspend = tenant.status === "active"
  // Allow reactivate if suspended
  const canReactivate = tenant.status === "suspended"

  if (variant === "buttons") {
    return (
      <div className="flex items-center gap-2">
        {canApprove && (
          <Button onClick={handleApprove} disabled={approve.isPending} size="sm" className="bg-emerald-600 hover:bg-emerald-700 text-white">
            <CheckCircle className="mr-2 h-4 w-4" />
            Approve
          </Button>
        )}
        {canReactivate && (
          <Button onClick={handleReactivate} disabled={reactivate.isPending} size="sm" variant="outline">
            <RefreshCw className="mr-2 h-4 w-4" />
            Reactivate
          </Button>
        )}
        {canSuspend && (
          <Button onClick={() => setIsSuspendOpen(true)} size="sm" variant="destructive">
            <Ban className="mr-2 h-4 w-4" />
            Suspend
          </Button>
        )}
        {canReject && (
          <Button onClick={() => setIsRejectOpen(true)} size="sm" variant="destructive">
            <XCircle className="mr-2 h-4 w-4" />
            Reject
          </Button>
        )}

        <ReasonDialog 
          isOpen={isRejectOpen} 
          setIsOpen={setIsRejectOpen} 
          title="Reject Tenant" 
          description={`Are you sure you want to reject ${tenant.name}? This action cannot be undone.`}
          reason={reason}
          setReason={setReason}
          onConfirm={handleReject}
          isLoading={reject.isPending}
          confirmText="Reject Tenant"
        />

        <ReasonDialog 
          isOpen={isSuspendOpen} 
          setIsOpen={setIsSuspendOpen} 
          title="Suspend Tenant" 
          description={`Suspending ${tenant.name} will prevent all users of this tenant from logging in.`}
          reason={reason}
          setReason={setReason}
          onConfirm={handleSuspend}
          isLoading={suspend.isPending}
          confirmText="Suspend Tenant"
        />
      </div>
    )
  }

  return (
    <>
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button variant="ghost" className="h-8 w-8 p-0">
            <span className="sr-only">Open menu</span>
            <MoreHorizontal className="h-4 w-4" />
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end">
          {canApprove && (
            <DropdownMenuItem onClick={handleApprove} disabled={approve.isPending} className="text-emerald-600 focus:bg-emerald-50 focus:text-emerald-700 dark:focus:bg-emerald-950/50">
              <CheckCircle className="mr-2 h-4 w-4" />
              Approve
            </DropdownMenuItem>
          )}
          
          {canReactivate && (
            <DropdownMenuItem onClick={handleReactivate} disabled={reactivate.isPending}>
              <RefreshCw className="mr-2 h-4 w-4" />
              Reactivate
            </DropdownMenuItem>
          )}
          
          {(canApprove || canReactivate) && (canSuspend || canReject) && <DropdownMenuSeparator />}
          
          {canSuspend && (
            <DropdownMenuItem onClick={() => setIsSuspendOpen(true)} className="text-destructive focus:bg-destructive/10 focus:text-destructive">
              <Ban className="mr-2 h-4 w-4" />
              Suspend
            </DropdownMenuItem>
          )}
          
          {canReject && (
            <DropdownMenuItem onClick={() => setIsRejectOpen(true)} className="text-destructive focus:bg-destructive/10 focus:text-destructive">
              <XCircle className="mr-2 h-4 w-4" />
              Reject
            </DropdownMenuItem>
          )}
        </DropdownMenuContent>
      </DropdownMenu>

      <ReasonDialog 
        isOpen={isRejectOpen} 
        setIsOpen={setIsRejectOpen} 
        title="Reject Tenant" 
        description={`Are you sure you want to reject ${tenant.name}? This action cannot be undone.`}
        reason={reason}
        setReason={setReason}
        onConfirm={handleReject}
        isLoading={reject.isPending}
        confirmText="Reject Tenant"
      />

      <ReasonDialog 
        isOpen={isSuspendOpen} 
        setIsOpen={setIsSuspendOpen} 
        title="Suspend Tenant" 
        description={`Suspending ${tenant.name} will prevent all users of this tenant from logging in.`}
        reason={reason}
        setReason={setReason}
        onConfirm={handleSuspend}
        isLoading={suspend.isPending}
        confirmText="Suspend Tenant"
      />
    </>
  )
}

function ReasonDialog({ 
  isOpen, setIsOpen, title, description, reason, setReason, onConfirm, isLoading, confirmText 
}: any) {
  return (
    <Dialog open={isOpen} onOpenChange={(open) => {
      setIsOpen(open)
      if (!open) setReason("")
    }}>
      <DialogContent className="sm:max-w-[425px]">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <AlertCircle className="h-5 w-5 text-destructive" />
            {title}
          </DialogTitle>
          <DialogDescription>
            {description}
          </DialogDescription>
        </DialogHeader>
        <div className="grid gap-4 py-4">
          <div className="grid gap-2">
            <Label htmlFor="reason">Reason (Required)</Label>
            <Input
              id="reason"
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              placeholder="Please provide a reason..."
            />
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => setIsOpen(false)} disabled={isLoading}>
            Cancel
          </Button>
          <Button variant="destructive" onClick={onConfirm} disabled={isLoading || !reason.trim()}>
            {isLoading ? "Processing..." : confirmText}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
