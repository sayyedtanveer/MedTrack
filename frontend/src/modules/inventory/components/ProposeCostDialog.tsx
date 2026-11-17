import React, { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Material } from "@/types/material.types";
import { standardCostRevisionApi } from "@/modules/procurement/services/standardCostRevisionApi";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import ErrorBanner from "@/components/shared/ErrorBanner";

// Zod schema for form validation
const proposeCostSchema = z.object({
  requested_cost: z
    .string()
    .transform((v) => parseFloat(v))
    .refine((v) => !isNaN(v) && v > 0, {
      message: "Cost must be a valid number greater than 0",
    }),
  reason: z
    .string()
    .min(1, "Reason is required")
    .min(10, "Reason must be at least 10 characters"),
  notes: z.string().optional(),
});

type ProposeCostFormInput = z.input<typeof proposeCostSchema>;
type ProposeCostFormData = z.output<typeof proposeCostSchema>;

interface ProposeCostDialogProps {
  material: Material | null;
  isOpen: boolean;
  onClose: () => void;
  onSuccess?: () => void | Promise<void>;
}

/**
 * Dialog for proposing a new standard cost for a material
 * Uses react-hook-form + zod for validation
 */
export const ProposeCostDialog: React.FC<ProposeCostDialogProps> = ({
  material,
  isOpen,
  onClose,
  onSuccess,
}) => {
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<ProposeCostFormInput, unknown, ProposeCostFormData>({
    resolver: zodResolver(proposeCostSchema),
    defaultValues: {
      requested_cost: "",
      reason: "",
      notes: "",
    },
  });

  const handleDialogOpenChange = (open: boolean) => {
    if (!open) {
      reset();
      setError(null);
      onClose();
    }
  };

  const onSubmit = async (data: ProposeCostFormData) => {
    if (!material) {
      setError("Material not selected");
      return;
    }

    setLoading(true);
    setError(null);

    try {
      await standardCostRevisionApi.proposeCost(material.id, {
        requested_cost: data.requested_cost,
        reason: data.reason,
        notes: data.notes || undefined,
      });

      reset();
      setError(null);
      setTimeout(() => {
        handleDialogOpenChange(false);
        onSuccess?.();
      }, 500);
    } catch (err) {
      const errorMessage =
        err instanceof Error ? err.message : "Failed to propose cost";
      setError(errorMessage);
      console.error("Error proposing cost:", err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Dialog open={isOpen} onOpenChange={handleDialogOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Propose Material Cost</DialogTitle>
          <DialogDescription>
            {material ? (
              <>
                {material.code} — {material.name}
              </>
            ) : (
              "Enter cost proposal details"
            )}
          </DialogDescription>
        </DialogHeader>

        {material && (
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
            {/* Current Cost (Read-only) */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Current Cost
              </label>
              <div className="px-3 py-2 bg-gray-50 border border-gray-300 rounded text-gray-600 text-sm">
                {material.current_cost?.toFixed(2) || "0.00"}{" "}
                {material.base_unit_id ? "(per unit)" : ""}
              </div>
            </div>

            {/* Proposed Cost */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Proposed Cost <span className="text-red-500">*</span>
              </label>
              <input
                type="number"
                step="0.01"
                min="0"
                placeholder="Enter proposed cost"
                {...register("requested_cost")}
                className="w-full px-3 py-2 border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
              {errors.requested_cost && (
                <p className="text-red-600 text-xs mt-1">
                  {errors.requested_cost.message}
                </p>
              )}
            </div>

            {/* Reason */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Reason <span className="text-red-500">*</span>
              </label>
              <textarea
                rows={2}
                placeholder="Why are you proposing this cost?"
                {...register("reason")}
                className="w-full px-3 py-2 border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
              {errors.reason && (
                <p className="text-red-600 text-xs mt-1">
                  {errors.reason.message}
                </p>
              )}
            </div>

            {/* Notes */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Notes (Optional)
              </label>
              <textarea
                rows={2}
                placeholder="Any additional details..."
                {...register("notes")}
                className="w-full px-3 py-2 border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            {/* Error Message */}
            {error && <ErrorBanner message={error} />}

            {/* Actions */}
            <div className="flex gap-3 justify-end mt-6">
              <Button
                type="button"
                variant="outline"
                onClick={() => handleDialogOpenChange(false)}
                disabled={loading}
              >
                Cancel
              </Button>
              <Button type="submit" disabled={loading}>
                {loading ? "Submitting..." : "Propose Cost"}
              </Button>
            </div>
          </form>
        )}
      </DialogContent>
    </Dialog>
  );
};
