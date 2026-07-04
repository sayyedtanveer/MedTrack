// Operation Form Drawer - Create/Edit Operations.

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { useForm } from "react-hook-form"
import React from "react"
import { operationService, CreateOperationPayload, UpdateOperationPayload } from "@/services/operation.service"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetFooter,
} from "@/components/ui/sheet"
import { Label } from "@/components/ui/label"
import { Checkbox } from "@/components/ui/checkbox"
import { X, Loader2 } from "lucide-react"

interface Props {
  operationId?: string
  isNew?: boolean
  open: boolean
  onClose: () => void
}

const OPERATION_TYPES = [
  { value: "cutting", label: "Cutting" },
  { value: "machining", label: "Machining" },
  { value: "assembly", label: "Assembly" },
  { value: "calibration", label: "Calibration" },
  { value: "testing", label: "Testing" },
  { value: "inspection", label: "Inspection" },
  { value: "packaging", label: "Packaging" },
  { value: "finishing", label: "Finishing" },
  { value: "other", label: "Other" },
]

export function OperationFormDrawer({ operationId, isNew = false, open, onClose }: Props) {
  const queryClient = useQueryClient()
  const {
    register,
    handleSubmit,
    reset,
    watch,
    setValue,
    formState: { errors, isSubmitting },
  } = useForm({
    defaultValues: {
      operation_code: "",
      name: "",
      operation_type: "other",
      description: "",
      default_sequence: 10,
      estimated_time_minutes: undefined,
      qc_required: false,
      color: undefined,
      icon_code: undefined,
    },
  })

  const operationType = watch("operation_type")
  const qcRequired = watch("qc_required")

  // Fetch operation if editing
  const { data: operation, isLoading: isFetchingOperation } = useQuery({
    queryKey: ["operation", operationId],
    queryFn: () => operationService.getOperation(operationId!),
    enabled: !!operationId && !isNew,
  })

  // Reset form when operation loads
  React.useEffect(() => {
    if (operation && open) {
      const resetData: any = {
        operation_code: operation.operation_code,
        name: operation.name,
        operation_type: operation.operation_type,
        description: operation.description || "",
        default_sequence: operation.default_sequence,
        qc_required: operation.qc_required,
      }
      if (operation.estimated_time_minutes !== undefined) {
        resetData.estimated_time_minutes = operation.estimated_time_minutes
      }
      if (operation.color !== undefined) {
        resetData.color = operation.color
      }
      if (operation.icon_code !== undefined) {
        resetData.icon_code = operation.icon_code
      }
      reset(resetData)
    } else if (isNew && open) {
      reset({
        operation_code: "",
        name: "",
        operation_type: "other",
        description: "",
        default_sequence: 10,
        estimated_time_minutes: undefined,
        qc_required: false,
      })
    }
  }, [operation, open, isNew, reset])

  // Create mutation
  const createMutation = useMutation({
    mutationFn: (payload: CreateOperationPayload) => operationService.createOperation(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["operations"] })
      onClose()
    },
  })

  // Update mutation
  const updateMutation = useMutation({
    mutationFn: (payload: UpdateOperationPayload) =>
      operationService.updateOperation(operationId!, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["operations"] })
      queryClient.invalidateQueries({ queryKey: ["operation", operationId] })
      onClose()
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

  return (
    <Sheet open={open} onOpenChange={onClose}>
      <SheetContent className="w-full sm:max-w-xl overflow-y-auto">
        <SheetHeader className="flex flex-row items-center justify-between space-y-0 pb-4">
          <SheetTitle>
            {isNew ? "New Operation" : "Edit Operation"}
          </SheetTitle>
          <Button
            variant="ghost"
            size="icon"
            onClick={onClose}
            className="h-8 w-8"
            aria-label="Close drawer"
          >
            <X className="h-4 w-4" />
          </Button>
        </SheetHeader>

        {isFetchingOperation ? (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
          </div>
        ) : (
          <form onSubmit={onSubmit} className="space-y-6">
            {/* Operation Code - Read-only when editing */}
            <div className="space-y-2">
              <Label htmlFor="code">Operation Code *</Label>
              <Input
                id="code"
                placeholder="10, 20, 30..."
                disabled={!isNew}
                {...register("operation_code", {
                  required: "Code is required",
                  maxLength: { value: 10, message: "Max 10 characters" },
                })}
              />
              {errors.operation_code && (
                <p className="text-sm text-destructive">{errors.operation_code.message}</p>
              )}
            </div>

            {/* Name */}
            <div className="space-y-2">
              <Label htmlFor="name">Operation Name *</Label>
              <Input
                id="name"
                placeholder="e.g., Cutting, Assembly, QC Inspection..."
                {...register("name", {
                  required: "Name is required",
                  maxLength: { value: 100, message: "Max 100 characters" },
                })}
              />
              {errors.name && (
                <p className="text-sm text-destructive">{errors.name.message}</p>
              )}
            </div>

            {/* Operation Type */}
            <div className="space-y-2">
              <Label htmlFor="type">Operation Type</Label>
              <Select value={operationType} onValueChange={(value) => setValue("operation_type", value)}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {OPERATION_TYPES.map((type) => (
                    <SelectItem key={type.value} value={type.value}>
                      {type.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {/* Description */}
            <div className="space-y-2">
              <Label htmlFor="desc">Description</Label>
              <Textarea
                id="desc"
                placeholder="What does this operation involve?"
                rows={3}
                {...register("description")}
              />
            </div>

            {/* Sequence */}
            <div className="space-y-2">
              <Label htmlFor="seq">Sequence #</Label>
              <Input
                id="seq"
                type="number"
                placeholder="10"
                {...register("default_sequence", {
                  valueAsNumber: true,
                  min: { value: 10, message: "Must be >= 10" },
                })}
              />
              {errors.default_sequence && (
                <p className="text-sm text-destructive">{errors.default_sequence.message}</p>
              )}
            </div>

            {/* Estimated Time */}
            <div className="space-y-2">
              <Label htmlFor="time">Estimated Time (minutes)</Label>
              <Input
                id="time"
                type="number"
                placeholder="e.g., 15"
                step={0.5}
                {...register("estimated_time_minutes", {
                  valueAsNumber: true,
                })}
              />
            </div>

            {/* QC Required */}
            <div className="flex items-center gap-2">
              <Checkbox
                id="qc"
                checked={qcRequired}
                onCheckedChange={(checked) => setValue("qc_required", !!checked)}
              />
              <Label htmlFor="qc" className="font-normal cursor-pointer">
                Quality Control Required
              </Label>
            </div>

            {/* UI Metadata */}
            <div className="pt-4 border-t">
              <h4 className="text-sm font-semibold mb-3">Optional UI Styling</h4>

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="color">Color (hex)</Label>
                  <Input
                    id="color"
                    type="color"
                    {...register("color")}
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="icon">Icon Code</Label>
                  <Input
                    id="icon"
                    placeholder="e.g., cut, hammer..."
                    {...register("icon_code")}
                  />
                </div>
              </div>
            </div>

            {/* Buttons */}
            <SheetFooter className="flex gap-2 justify-end pt-6">
              <Button variant="outline" onClick={onClose}>
                Cancel
              </Button>
              <Button type="submit" disabled={isSubmitting}>
                {isSubmitting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                {isNew ? "Create" : "Update"} Operation
              </Button>
            </SheetFooter>
          </form>
        )}
      </SheetContent>
    </Sheet>
  )
}
