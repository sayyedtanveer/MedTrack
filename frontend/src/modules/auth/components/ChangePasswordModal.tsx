import { useState } from "react"
import { useMutation } from "@tanstack/react-query"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { useAuthStore } from "@/app/store/authStore"

interface ChangePasswordModalProps {
  isOpen: boolean
  onClose: () => void
}

const readErrorMessage = async (response: Response, fallback: string) => {
  try {
    const data = await response.json()
    const message = data?.detail || data?.message
    return typeof message === "string" ? message : message ? JSON.stringify(message) : fallback
  } catch {
    return fallback
  }
}

export default function ChangePasswordModal({ isOpen, onClose }: ChangePasswordModalProps) {
  const [currentPassword, setCurrentPassword] = useState("")
  const [newPassword, setNewPassword] = useState("")
  const [confirmPassword, setConfirmPassword] = useState("")
  const [error, setError] = useState("")
  const [message, setMessage] = useState("")
  const token = useAuthStore((s) => s.token)

  const changePasswordMutation = useMutation({
    mutationFn: async () => {
      if (newPassword !== confirmPassword) {
        throw new Error("Passwords do not match")
      }
      if (newPassword.length < 8) {
        throw new Error("New password must be at least 8 characters")
      }

      const response = await fetch("/api/v1/auth/change-password", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          current_password: currentPassword,
          new_password: newPassword,
        }),
      })
      if (!response.ok) {
        throw new Error(await readErrorMessage(response, "Failed to change password"))
      }
      return response.json()
    },
    onSuccess: () => {
      setMessage("Password changed successfully!")
      setTimeout(() => {
        handleClose()
      }, 2000)
    },
    onError: (err: any) => {
      setError(err.message || "Failed to change password")
    },
  })

  const handleClose = () => {
    setCurrentPassword("")
    setNewPassword("")
    setConfirmPassword("")
    setError("")
    setMessage("")
    onClose()
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    setError("")
    setMessage("")
    changePasswordMutation.mutate()
  }

  return (
    <Dialog open={isOpen} onOpenChange={handleClose}>
      <DialogContent className="sm:max-w-[400px]">
        <DialogHeader>
          <DialogTitle>Change Password</DialogTitle>
          <DialogDescription>
            Enter your current password and a new password to update your credentials.
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="current-password">Current Password</Label>
            <Input
              id="current-password"
              type="password"
              placeholder="Enter your current password"
              value={currentPassword}
              onChange={(e) => setCurrentPassword(e.target.value)}
              disabled={changePasswordMutation.isPending}
              autoFocus
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="new-password">New Password</Label>
            <Input
              id="new-password"
              type="password"
              placeholder="At least 8 characters"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              disabled={changePasswordMutation.isPending}
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="confirm-password">Confirm New Password</Label>
            <Input
              id="confirm-password"
              type="password"
              placeholder="Confirm your new password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              disabled={changePasswordMutation.isPending}
            />
          </div>

          {error && <div className="rounded bg-red-50 p-3 text-sm text-red-600">{error}</div>}
          {message && <div className="rounded bg-green-50 p-3 text-sm text-green-600">{message}</div>}

          <div className="flex gap-2">
            <Button type="button" variant="outline" onClick={handleClose} className="flex-1">
              Cancel
            </Button>
            <Button
              type="submit"
              className="flex-1"
              disabled={changePasswordMutation.isPending || !currentPassword || !newPassword || !confirmPassword}
            >
              {changePasswordMutation.isPending ? "Changing..." : "Change Password"}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  )
}
