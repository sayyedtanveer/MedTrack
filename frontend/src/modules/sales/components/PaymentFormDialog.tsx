/**
 * Payment Form Dialog Component
 * Allows recording payment for an invoice from the Sales Order Detail page.
 * 
 * Requirements validated: 3.1–3.7
 */

import { useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import * as z from 'zod';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Textarea } from '@/components/ui/textarea';
import { useToast } from '@/hooks/use-toast';
import { financeService, type Invoice } from '@/services/finance.service';
import { formatCurrency } from '@/utils/currency';
import { Loader2 } from 'lucide-react';

// Validation schema with zod
const paymentSchema = z.object({
  amount: z
    .number()
    .min(0.01, 'Amount must be at least 0.01')
    .positive('Amount must be positive'),
  payment_method: z.enum(['Cash', 'Bank Transfer', 'Credit Card', 'Check'], {
    required_error: 'Payment method is required',
  }),
  payment_date: z.string().min(1, 'Payment date is required'),
  notes: z.string().optional(),
});

type PaymentFormData = z.infer<typeof paymentSchema>;

interface PaymentFormDialogProps {
  open: boolean;
  onClose: () => void;
  invoice: Invoice | null;
  onSuccess?: () => void;
}

export default function PaymentFormDialog({
  open,
  onClose,
  invoice,
  onSuccess,
}: PaymentFormDialogProps) {
  const { toast } = useToast();
  const queryClient = useQueryClient();

  const outstandingBalance = invoice ? invoice.balance_due : 0;

  const {
    register,
    handleSubmit,
    formState: { errors },
    setValue,
    watch,
    reset,
  } = useForm<PaymentFormData>({
    resolver: zodResolver(paymentSchema),
    defaultValues: {
      amount: outstandingBalance,
      payment_method: 'Bank Transfer',
      payment_date: new Date().toISOString().split('T')[0], // Today's date in YYYY-MM-DD
      notes: '',
    },
  });

  const paymentMethod = watch('payment_method');

  // Reset form when invoice changes or dialog opens
  useEffect(() => {
    if (open && invoice) {
      reset({
        amount: invoice.balance_due,
        payment_method: 'Bank Transfer',
        payment_date: new Date().toISOString().split('T')[0],
        notes: '',
      });
    }
  }, [open, invoice, reset]);

  const recordPaymentMutation = useMutation({
    mutationFn: async (data: PaymentFormData) => {
      if (!invoice) throw new Error('No invoice selected');
      
      // Validate amount against outstanding balance
      if (data.amount > outstandingBalance) {
        throw new Error(`Amount cannot exceed outstanding balance of ${formatCurrency(outstandingBalance)}`);
      }

      return financeService.recordPayment({
        invoice_id: invoice.id,
        amount: data.amount,
        payment_date: data.payment_date,
        payment_method: data.payment_method,
        notes: data.notes,
      });
    },
    onSuccess: () => {
      toast({
        title: 'Payment recorded',
        description: 'Payment has been successfully recorded',
      });
      
      // Invalidate relevant queries
      queryClient.invalidateQueries({ queryKey: ['sales-order'] });
      queryClient.invalidateQueries({ queryKey: ['invoice'] });
      queryClient.invalidateQueries({ queryKey: ['invoices'] });
      
      onSuccess?.();
      onClose();
    },
    onError: (error: Error) => {
      // Preserve form inputs on error
      toast({
        title: 'Payment recording failed',
        description: error.message,
        variant: 'destructive',
      });
    },
  });

  const onSubmit = (data: PaymentFormData) => {
    recordPaymentMutation.mutate(data);
  };

  if (!invoice) {
    return null;
  }

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="sm:max-w-[500px]">
        <DialogHeader>
          <DialogTitle>Record Payment</DialogTitle>
          <DialogDescription>
            Record a payment for Invoice {invoice.invoice_number}
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          {/* Read-only Invoice Information */}
          <div className="space-y-2 pb-4 border-b">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label className="text-xs text-gray-500">Invoice Number</Label>
                <p className="text-sm font-medium">{invoice.invoice_number}</p>
              </div>
              <div>
                <Label className="text-xs text-gray-500">Outstanding Balance</Label>
                <p className="text-sm font-semibold text-red-600">
                  {formatCurrency(outstandingBalance)}
                </p>
              </div>
            </div>
            <div>
              <Label className="text-xs text-gray-500">Client</Label>
              <p className="text-sm font-medium">{invoice.client_name}</p>
            </div>
          </div>

          {/* Payment Amount */}
          <div className="space-y-2">
            <Label htmlFor="amount">
              Payment Amount <span className="text-red-500">*</span>
            </Label>
            <Input
              id="amount"
              type="number"
              step="0.01"
              min="0.01"
              max={outstandingBalance}
              aria-required="true"
              {...register('amount', { valueAsNumber: true })}
              placeholder="Enter amount"
            />
            {errors.amount && (
              <p className="text-sm text-red-600">{errors.amount.message}</p>
            )}
            <p className="text-xs text-gray-500">
              Maximum: {formatCurrency(outstandingBalance)}
            </p>
          </div>

          {/* Payment Method */}
          <div className="space-y-2">
            <Label htmlFor="payment_method">
              Payment Method <span className="text-red-500">*</span>
            </Label>
            <Select
              value={paymentMethod}
              onValueChange={(value) =>
                setValue('payment_method', value as any, { shouldValidate: true })
              }
            >
              <SelectTrigger id="payment_method" aria-required="true">
                <SelectValue placeholder="Select payment method" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="Cash">Cash</SelectItem>
                <SelectItem value="Bank Transfer">Bank Transfer</SelectItem>
                <SelectItem value="Credit Card">Credit Card</SelectItem>
                <SelectItem value="Check">Check</SelectItem>
              </SelectContent>
            </Select>
            {errors.payment_method && (
              <p className="text-sm text-red-600">{errors.payment_method.message}</p>
            )}
          </div>

          {/* Payment Date */}
          <div className="space-y-2">
            <Label htmlFor="payment_date">
              Payment Date <span className="text-red-500">*</span>
            </Label>
            <Input
              id="payment_date"
              type="date"
              aria-required="true"
              {...register('payment_date')}
            />
            {errors.payment_date && (
              <p className="text-sm text-red-600">{errors.payment_date.message}</p>
            )}
          </div>

          {/* Notes (Optional) */}
          <div className="space-y-2">
            <Label htmlFor="notes">Notes (Optional)</Label>
            <Textarea
              id="notes"
              {...register('notes')}
              placeholder="Add any additional notes about this payment"
              rows={3}
            />
            {errors.notes && (
              <p className="text-sm text-red-600">{errors.notes.message}</p>
            )}
          </div>

          {/* Error Display */}
          {recordPaymentMutation.isError && (
            <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded text-sm">
              {recordPaymentMutation.error?.message || 'Failed to record payment'}
            </div>
          )}

          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={onClose}
              disabled={recordPaymentMutation.isPending}
            >
              Cancel
            </Button>
            <Button type="submit" disabled={recordPaymentMutation.isPending}>
              {recordPaymentMutation.isPending && (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              )}
              Record Payment
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
