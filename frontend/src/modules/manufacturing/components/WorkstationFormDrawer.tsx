/**
 * Workstation Form Drawer - Create/Edit Workstations.
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { useForm } from "react-hook-form"
import React from "react"
import { workstationsService, CreateWorkstationPayload, UpdateWorkstationPayload } from "@/services/workstations.service"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetFooter,
} from "@/components/ui/sheet"
import { Label } from "@/components/ui/label"
import { X, Loader2 } from "lucide-react"
import { toast } from "sonner"

interface Props {
  workstationId?: string
  isNew?: boolean
  open: boolean
  onClose: () => void
}

export function WorkstationFormDrawer({ workstationId, isNew = false, open, onClose }: Props) {
  const queryClient = useQueryClient()

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm({
    defaultValues: {
      code: "",
      name: "",
      capacity_hours_per_day: 8.0,
      hourly_rate: 0.0,
    },
  })

  // Fetch workstation if editing
  const { data: workstation, isLoading: isFetchingWorkstation } = useQuery({
    queryKey: ["workstation", workstationId],
    queryFn: () => workstationsService.getWorkstation(workstationId!),
    enabled: !!workstationId && !isNew,
  })

  // Reset form when workstation loads
  React.useEffect(() => {
    if (workstation && open) {
      reset({
        code: workstation.code,
        name: workstation.name,
        capacity_hours_per_day: workstation.capacity_hours_per_day,
        hourly_rate: workstation.hourly_rate,
      })
    } else if (isNew && open) {
      reset({
        code: "",
        name: "",
        capacity_hours_per_day: 8.0,
        hourly_rate: 0.0,
      })
    }
  }, [workstation, open, isNew, reset])

  // Create mutation
  const createMutation = useMutation({
    mutationFn: (payload: CreateWorkstationPayload) => workstationsService.createWorkstation(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["workstations"] })
      toast.success("Workstation created successfully")
      onClose()
    },
    onError: (error: any) => {
      toast.error(error?.response?.data?.detail || "Failed to create workstation")
    },
  })

  // Update mutation
  const updateMutation = useMutation({
    mutationFn: (payload: UpdateWorkstationPayload) =>
      workstationsService.updateWorkstation(workstationId!, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["workstations"] })
      toast.success("Workstation updated successfully")
      onClose()
    },
    onError: (error: any) => {
      toast.error(error?.response?.data?.detail || "Failed to update workstation")
    },
  })

  const onSubmit = handleSubmit(async (data) => {
    try {
      if (isNew) {
        await createMutation.mutateAsync(data)
      } else {
        await updateMutation.mutateAsync(data)
      }
    } catch (error) {
      console.error("Form submission error:", error)
    }
  })

  const isLoading = createMutation.isPending || updateMutation.isPending || isFetchingWorkstation

  return (
    <Sheet open={open} onOpenChange={onClose}>
      <SheetContent className="w-full sm:max-w-xl overflow-y-auto">
        <SheetHeader className="flex flex-row items-center justify-between space-y-0 pb-4">
          <SheetTitle>
            {isNew ? "New Workstation" : "Edit Workstation"}
          </SheetTitle>
          <Button
            variant="ghost"
            size="icon"
            onClick={onClose}
            className="h-8 w-8"
            disabled={isLoading}
            aria-label="Close drawer"
          >
            <X className="h-4 w-4" />
          </Button>
        </SheetHeader>

        <form onSubmit={onSubmit} className="space-y-6">
          {/* Workstation Code - Read-only when editing */}
          <div className="space-y-2">
            <Label htmlFor="code">Workstation Code *</Label>
            <Input
              id="code"
              placeholder="e.g., WS-001, ASM-1, CNC-1"
              disabled={!isNew}
              {...register("code", {
                required: "Code is required",
                maxLength: { value: 50, message: "Max 50 characters" },
              })}
            />
            {errors.code && (
              <p className="text-sm text-destructive">{errors.code.message}</p>
            )}
            <p className="text-xs text-muted-foreground">
              Unique identifier for this workstation
            </p>
          </div>

          {/* Name */}
          <div className="space-y-2">
            <Label htmlFor="name">Workstation Name *</Label>
            <Input
              id="name"
              placeholder="e.g., Assembly Line 1, CNC Machine A, Soldering Station"
              {...register("name", {
                required: "Name is required",
                maxLength: { value: 255, message: "Max 255 characters" },
              })}
            />
            {errors.name && (
              <p className="text-sm text-destructive">{errors.name.message}</p>
            )}
          </div>

          {/* Capacity (hours per day) */}
          <div className="space-y-2">
            <Label htmlFor="capacity">Capacity (hours/day) *</Label>
            <Input
              id="capacity"
              type="number"
              min="0"
              step="0.5"
              placeholder="8.0"
              {...register("capacity_hours_per_day", {
                required: "Capacity is required",
                valueAsNumber: true,
                min: { value: 0, message: "Must be positive" },
              })}
            />
            {errors.capacity_hours_per_day && (
              <p className="text-sm text-destructive">{errors.capacity_hours_per_day.message}</p>
            )}
            <p className="text-xs text-muted-foreground">
              Available working hours per day for this workstation
            </p>
          </div>

          {/* Hourly Rate */}
          <div className="space-y-2">
            <Label htmlFor="rate">Hourly Rate (₹)</Label>
            <Input
              id="rate"
              type="number"
              min="0"
              step="0.01"
              placeholder="0.00"
              {...register("hourly_rate", {
                valueAsNumber: true,
                min: { value: 0, message: "Must be positive" },
              })}
            />
            {errors.hourly_rate && (
              <p className="text-sm text-destructive">{errors.hourly_rate.message}</p>
            )}
            <p className="text-xs text-muted-foreground">
              Used for cost calculation in work orders
            </p>
          </div>

          {/* Footer */}
          <SheetFooter className="mt-8 gap-2">
            <Button
              type="button"
              variant="outline"
              onClick={onClose}
              disabled={isLoading}
            >
              Cancel
            </Button>
            <Button
              type="submit"
              disabled={isLoading}
            >
              {isLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              {isNew ? "Create Workstation" : "Save Changes"}
            </Button>
          </SheetFooter>
        </form>
      </SheetContent>
    </Sheet>
  )
}
