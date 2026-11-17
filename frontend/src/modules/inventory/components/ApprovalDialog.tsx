import React, { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
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

// Zod schema for rejection reason
const approvalSchema = z.object({
  rejection_reason: z
    .string()
    .min(1, "Reason is required")
    .min(5, "Reason must be at least 5 characters"),
});

type ApprovalFormData = z.infer<typeof approvalSchema>;

interface ApprovalDialogProps {
  isOpen: boolean;
  onClose: () => void;
  materialCode: string | null;
  revisionId: string | null;
  isReject: boolean;
  onSuccess?: () => void | Promise<void>;
}

/**
 * Dialog for approving or rejecting a cost revision
 * For rejection, collects rejection reason with validation
 */
export const ApprovalDialog: React.FC<ApprovalDialogProps> = ({
  isOpen,
  onClose,
  materialCode,
  revisionId,
  isReject,
  onSuccess,
}) => {
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<ApprovalFormData>({
    resolver: isReject ? zodResolver(approvalSchema) : undefined,
    defaultValues: {
      rejection_reason: "",
    },
  });

  const handleDialogOpenChange = (open: boolean) => {
    if (!open) {
      reset();
      setError(null);
      onClose();
    }
  };

  const onSubmit = async (data?: ApprovalFormData) => {
    if (!revisionId) {
      setError("Revision ID missing");
      return;
    }

    setLoading(true);
    setError(null);

    try {
      if (isReject) {
        if (!data?.rejection_reason) {
          setError("Rejection reason is required");
          setLoading(false);
          return;
        }
        await standardCostRevisionApi.reject({
          revision_id: revisionId,
          rejection_reason: data.rejection_reason,
        });
      } else {
        await standardCostRevisionApi.approve(revisionId);
      }

      reset();
      setError(null);
      setTimeout(() => {
        handleDialogOpenChange(false);
        onSuccess?.();
      }, 500);
    } catch (err) {
      const errorMessage =
        err instanceof Error ? err.message : "Failed to process approval";
      setError(errorMessage);
      console.error("Error processing approval:", err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Dialog open={isOpen} onOpenChange={handleDialogOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>
            {isReject ? "Reject Cost Revision" : "Approve Cost Revision"}
          </DialogTitle>
          <DialogDescription>
            {materialCode ? `Material: ${materialCode}` : "Cost revision"}
          </DialogDescription>
        </DialogHeader>

        {isReject ? (
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
            {/* Rejection Reason */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Rejection Reason <span className="text-red-500">*</span>
              </label>
              <textarea
                rows={3}
                placeholder="Explain why this cost revision is being rejected"
                {...register("rejection_reason")}
                className="w-full px-3 py-2 border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-red-500"
              />
              {errors.rejection_reason && (
                <p className="text-red-600 text-xs mt-1">
                  {errors.rejection_reason.message}
                </p>
              )}
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
              <Button
                type="submit"
                variant="destructive"
                disabled={loading}
              >
                {loading ? "Rejecting..." : "Reject"}
              </Button>
            </div>
          </form>
        ) : (
          <div className="space-y-4">
            <p className="text-gray-600">
              Are you sure you want to approve this cost revision?
            </p>

            {error && <ErrorBanner message={error} />}

            {/* Actions */}
            <div className="flex gap-3 justify-end mt-6">
              <Button
                variant="outline"
                onClick={() => handleDialogOpenChange(false)}
                disabled={loading}
              >
                Cancel
              </Button>
              <Button
                onClick={() => onSubmit()}
                disabled={loading}
              >
                {loading ? "Approving..." : "Approve"}
              </Button>
            </div>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
};
