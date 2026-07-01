import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import * as z from "zod"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { materialService } from "@/services/material.service"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { FormSkeleton } from "@/components/shared/LoadingSkeleton"
import { ArrowDownToLine, ArrowUpToLine, ArrowLeftRight, Replace, Save } from "lucide-react"
import { Drawer } from "@/components/shared/Drawer"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { useEffect, useState } from "react"
import { TransactionType } from "@/types/material.types"

const operationSchema = z.object({
  quantity: z.coerce.number().min(0.0001, "Quantity must be greater than 0"),
  unit_id: z.string().uuid("Please select a valid unit").nullable().optional(),
  from_location_id: z.string().uuid("Please select a valid location").nullable().optional(),
  to_location_id: z.string().uuid("Please select a valid location").nullable().optional(),
  remarks: z.string().max(500).optional().nullable(),
})

type OperationFormValues = z.infer<typeof operationSchema>

interface Props {
  materialId: string | null
  open: boolean
  onClose: () => void
}

export function StockOperationDrawer({ materialId, open, onClose }: Props) {
  const queryClient = useQueryClient()
  const [activeTab, setActiveTab] = useState<TransactionType>("in")

  const { data: material, isLoading: isFetchingMaterial } = useQuery({
    queryKey: ["material", materialId],
    queryFn: () => materialService.getMaterial(materialId!),
    enabled: Boolean(materialId) && open,
  })

  const { data: units, isLoading: isFetchingUnits } = useQuery({
    queryKey: ["units"],
    queryFn: () => materialService.getUnits(),
  })

  const { data: locations, isLoading: isFetchingLocations } = useQuery({
    queryKey: ["locations"],
    queryFn: () => materialService.getLocations(),
  })

  const isFetching = isFetchingMaterial || isFetchingUnits || isFetchingLocations;

  const { register, handleSubmit, formState: { errors }, reset, watch, setValue } = useForm<OperationFormValues>({
    resolver: zodResolver(operationSchema),
    defaultValues: {
      quantity: 0,
      unit_id: null,
      from_location_id: null,
      to_location_id: null,
      remarks: "",
    }
  })

  const qty = watch("quantity");

  useEffect(() => {
    if (open) {
      reset({
        quantity: 0,
        unit_id: material?.base_unit_id || null, // fallback to base_unit_id on open
        from_location_id: null,
        to_location_id: null,
        remarks: "",
      });
      setActiveTab("in");
    }
  }, [open, reset, material]);

  const saveMutation = useMutation({
    mutationFn: async (data: OperationFormValues) => {
      return await materialService.createTransaction({
        material_id: materialId!,
        transaction_type: activeTab,
        quantity: data.quantity,
        new_quantity: activeTab === "adjustment" ? data.quantity : undefined,
        unit_id: data.unit_id,
        from_location_id: activeTab === "out" ? data.from_location_id : activeTab === "transfer" ? data.from_location_id : undefined,
        to_location_id: activeTab === "in" ? data.to_location_id : activeTab === "transfer" ? data.to_location_id : undefined,
        remarks: data.remarks,
      })
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["materials"] })
      queryClient.invalidateQueries({ queryKey: ["material", materialId] })
      queryClient.invalidateQueries({ queryKey: ["transactions"] })
      onClose()
    }
  })

  if (!materialId) return null;

  const onSubmit = (data: OperationFormValues) => {
    // Transfer-specific validation
    if (activeTab === "transfer") {
      if (!data.from_location_id) return;
      if (!data.to_location_id) return;
      if (data.from_location_id === data.to_location_id) return;
    }
    saveMutation.mutate(data)
  }

  return (
    <Drawer 
      open={open} 
      onOpenChange={(v) => !v && onClose()} 
      title="Stock Operation"
      description={`Update stock levels for ${material?.name || "material"}`}
    >
      {isFetching ? (
         <FormSkeleton fields={4} />
      ) : (
        <div className="space-y-6 flex flex-col h-full pb-8">
          
          <div className="bg-muted p-4 rounded-lg flex justify-between items-center mb-4">
            <div>
              <p className="text-sm font-medium text-muted-foreground uppercase tracking-wider">{material?.code}</p>
              <h4 className="text-lg font-semibold">{material?.name}</h4>
            </div>
            <div className="text-right">
              <p className="text-sm text-muted-foreground mb-1">Current Stock</p>
              <p className="text-2xl font-bold font-mono">{material?.current_stock} <span className="text-sm font-normal">{units?.find(u => u.id === material?.base_unit_id)?.code}</span></p>
            </div>
          </div>

          <div className="grid grid-cols-4 gap-2 p-1 bg-muted/50 rounded-lg">
            <Button 
              type="button" 
              variant={activeTab === "in" ? "default" : "ghost"} 
              className={`w-full ${activeTab === "in" ? "bg-green-600 hover:bg-green-700 text-white" : ""}`}
              onClick={() => setActiveTab("in")}
            >
              <ArrowDownToLine className="w-4 h-4 mr-2"/>
              In
            </Button>
            <Button 
              type="button" 
              variant={activeTab === "out" ? "default" : "ghost"} 
              className={`w-full ${activeTab === "out" ? "bg-red-600 hover:bg-red-700 text-white" : ""}`}
              onClick={() => setActiveTab("out")}
            >
              <ArrowUpToLine className="w-4 h-4 mr-2"/>
              Out
            </Button>
            <Button 
              type="button" 
              variant={activeTab === "adjustment" ? "default" : "ghost"} 
              className="w-full"
              onClick={() => setActiveTab("adjustment")}
            >
              <Replace className="w-4 h-4 mr-2"/>
              Adjust
            </Button>
            <Button 
              type="button" 
              variant={activeTab === "transfer" ? "default" : "ghost"} 
              className={`w-full ${activeTab === "transfer" ? "bg-blue-600 hover:bg-blue-700 text-white" : ""}`}
              onClick={() => setActiveTab("transfer")}
            >
              <ArrowLeftRight className="w-4 h-4 mr-2"/>
              Transfer
            </Button>
          </div>

          <form onSubmit={handleSubmit(onSubmit)} className="space-y-6 flex-1">
            <div className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="quantity">
                  {activeTab === "adjustment" ? "New Absolute Stock Quantity" : "Quantity to Transfer"}
                </Label>
                <div className="relative">
                  <Input 
                    id="quantity" 
                    type="number" 
                    step="0.0001" 
                    className="text-lg font-mono pl-4 pr-16 py-6"
                    placeholder="0.00" 
                    {...register("quantity")} 
                    autoFocus 
                  />
                  <div className="absolute right-4 top-1/2 -translate-y-1/2 text-muted-foreground font-medium">
                    {units?.find(u => u.id === material?.base_unit_id)?.code}
                  </div>
                </div>
                {errors.quantity && <p className="text-xs text-destructive">{errors.quantity.message}</p>}
                
                {activeTab === "out" && material && Number(qty) > material.current_stock && (
                  <p className="text-xs text-destructive">Warning: This exceeds the current stock of {material.current_stock}</p>
                )}
              </div>

              <div className="space-y-2">
                <Label htmlFor="unit_id">Unit of Measure (Optional)</Label>
                <Select 
                  value={watch("unit_id") || ""} 
                  onValueChange={(val) => setValue("unit_id", val, { shouldValidate: true })}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Select UOM" />
                  </SelectTrigger>
                  <SelectContent>
                    {units?.map((u) => (
                      <SelectItem key={u.id} value={u.id}>
                        {u.name} ({u.code})
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                {errors.unit_id && <p className="text-xs text-destructive">{errors.unit_id.message}</p>}
              </div>

              {activeTab === "in" && (
                <div className="space-y-2">
                  <Label htmlFor="to_location_id">Destination Location (Optional)</Label>
                  <Select 
                    value={watch("to_location_id") || ""} 
                    onValueChange={(val) => setValue("to_location_id", val, { shouldValidate: true })}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Select Location" />
                    </SelectTrigger>
                    <SelectContent>
                      {locations?.map((l) => (
                        <SelectItem key={l.id} value={l.id}>
                          {l.name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  {errors.to_location_id && <p className="text-xs text-destructive">{errors.to_location_id.message}</p>}
                </div>
              )}

              {activeTab === "out" && (
                <div className="space-y-2">
                  <Label htmlFor="from_location_id">Source Location (Optional)</Label>
                  <Select 
                    value={watch("from_location_id") || ""} 
                    onValueChange={(val) => setValue("from_location_id", val, { shouldValidate: true })}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Select Location" />
                    </SelectTrigger>
                    <SelectContent>
                      {locations?.map((l) => (
                        <SelectItem key={l.id} value={l.id}>
                          {l.name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  {errors.from_location_id && <p className="text-xs text-destructive">{errors.from_location_id.message}</p>}
                </div>
              )}

              {activeTab === "transfer" && (
                <>
                  <div className="space-y-2">
                    <Label htmlFor="from_location_id">From Location <span className="text-destructive">*</span></Label>
                    <Select 
                      value={watch("from_location_id") || ""} 
                      onValueChange={(val) => setValue("from_location_id", val, { shouldValidate: true })}
                    >
                      <SelectTrigger>
                        <SelectValue placeholder="Select source location" />
                      </SelectTrigger>
                      <SelectContent>
                        {locations?.map((l) => (
                          <SelectItem key={l.id} value={l.id}>
                            {l.name}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    {errors.from_location_id && <p className="text-xs text-destructive">{errors.from_location_id.message}</p>}
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="to_location_id">To Location <span className="text-destructive">*</span></Label>
                    <Select 
                      value={watch("to_location_id") || ""} 
                      onValueChange={(val) => setValue("to_location_id", val, { shouldValidate: true })}
                    >
                      <SelectTrigger>
                        <SelectValue placeholder="Select destination location" />
                      </SelectTrigger>
                      <SelectContent>
                        {locations?.map((l) => (
                          <SelectItem key={l.id} value={l.id}>
                            {l.name}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    {errors.to_location_id && <p className="text-xs text-destructive">{errors.to_location_id.message}</p>}
                  </div>
                  {watch("from_location_id") && watch("to_location_id") && watch("from_location_id") === watch("to_location_id") && (
                    <p className="text-xs text-destructive">Source and destination locations must be different</p>
                  )}
                </>
              )}

              <div className="space-y-2">
                <Label htmlFor="remarks">Remarks / Reason</Label>
                <Textarea 
                  id="remarks" 
                  rows={2} 
                  placeholder={activeTab === "adjustment" ? "E.g. Cycle count discrepancy" : "Optional comments"} 
                  {...register("remarks")} 
                />
              </div>

            </div>
            
            <div className="pt-6 flex gap-3 w-full sm:justify-end">
              <Button type="button" variant="outline" onClick={onClose} className="w-full sm:w-auto">Cancel</Button>
              <Button 
                type="submit" 
                disabled={
                  saveMutation.isPending || 
                  (activeTab === "out" && material && Number(qty) > material.current_stock) ||
                  (activeTab === "transfer" && (!watch("from_location_id") || !watch("to_location_id") || watch("from_location_id") === watch("to_location_id")))
                } 
                className={`w-full sm:w-auto ${
                  activeTab === "in" ? "bg-green-600 hover:bg-green-700 text-white" : 
                  activeTab === "out" ? "bg-red-600 hover:bg-red-700 text-white" : 
                  activeTab === "transfer" ? "bg-blue-600 hover:bg-blue-700 text-white" : ""
                }`}
              >
                <Save className="mr-2 h-4 w-4" />
                {saveMutation.isPending ? "Processing..." : `Confirm ${activeTab === "transfer" ? "Transfer" : activeTab}`}
              </Button>
            </div>
          </form>
        </div>
      )}
    </Drawer>
  )
}
