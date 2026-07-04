import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"

interface ConfirmationDialogProps {
  /** Whether the dialog is open */
  open: boolean
  /** Callback when dialog open state changes */
  onOpenChange: (open: boolean) => void
  /** The confirmation message to display */
  message: string
  /** Optional dialog title (defaults to "Confirm Action") */
  title?: string
  /** Callback when the user confirms the action */
  onConfirm: () => void
  /** Optional label for the confirm button (defaults to "Confirm") */
  confirmLabel?: string
  /** Optional label for the cancel button (defaults to "Cancel") */
  cancelLabel?: string
  /** Whether the confirm action is destructive (changes button to red) */
  destructive?: boolean
  /** Whether the confirm button is in a loading state */
  loading?: boolean
}

export function ConfirmationDialog({
  open,
  onOpenChange,
  message,
  title = "Confirm Action",
  onConfirm,
  confirmLabel = "Confirm",
  cancelLabel = "Cancel",
  destructive = false,
  loading = false,
}: ConfirmationDialogProps) {
  const handleConfirm = () => {
    onConfirm()
  }

  const handleCancel = () => {
    onOpenChange(false)
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[425px]">
        <DialogHeader>
          <DialogTitle>{title}</DialogTitle>
          <DialogDescription>{message}</DialogDescription>
        </DialogHeader>
        <DialogFooter className="gap-2 sm:gap-0">
          <Button
            variant="outline"
            onClick={handleCancel}
            disabled={loading}
          >
            {cancelLabel}
          </Button>
          <Button
            variant={destructive ? "destructive" : "default"}
            onClick={handleConfirm}
            disabled={loading}
          >
            {loading ? "Processing..." : confirmLabel}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
