import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import * as z from "zod"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { inventoryService } from "@/services/inventory.service"
import { materialService } from "@/services/material.service"
import { useMaterialCodeEntry } from "../hooks/useMaterialCodeEntry"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { FormSkeleton } from "@/components/shared/LoadingSkeleton"
import { Save } from "lucide-react"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Drawer } from "@/components/shared/Drawer"
import { useEffect } from "react"

const productSchema = z.object({
  item_code: z.string().trim().max(50).optional(),
  sku: z.string().min(3, "SKU must be at least 3 characters"),
  name: z.string().min(2, "Name is required"),
  description: z.string().optional(),
  category_id: z.string().uuid("Please select a valid category").nullable().optional(),
  base_unit_id: z.string().uuid("Please select a valid unit").nullable().optional(),
  reorder_point: z.coerce.number().min(0),
  code_locked: z.boolean().optional(),
})

type ProductFormValues = z.infer<typeof productSchema>

interface Props {
  productId: string | null
  open: boolean
  onClose: () => void
}

export function ProductFormDrawer({ productId, open, onClose }: Props) {
  const queryClient = useQueryClient()
  const isEditing = Boolean(productId && productId !== "new")
  const { canEnterCode, generationDisabled, isLoading: isLoadingCodePolicy } = useMaterialCodeEntry(open && !isEditing)

  const { data: product, isLoading: isFetching } = useQuery({
    queryKey: ["product", productId],
    queryFn: () => inventoryService.getProduct(productId!),
    enabled: isEditing && open,
  })

  const { data: categories } = useQuery({
    queryKey: ["categories"],
    queryFn: () => materialService.getCategories(),
    enabled: open,
  })

  const { data: units } = useQuery({
    queryKey: ["units"],
    queryFn: () => materialService.getUnits(),
    enabled: open,
  })

  // Using raw uncontrolled form approach with react-hook-form register for simplicity in Phase 1
  const { register, handleSubmit, formState: { errors }, setValue, watch, reset } = useForm<ProductFormValues>({
    resolver: zodResolver(productSchema),
    defaultValues: {
      item_code: "",
      sku: "",
      name: "",
      description: "",
      category_id: null,
      base_unit_id: null,
      reorder_point: 10,
      code_locked: false,
    }
  })

  // Reset form when product data loads or modal opens for "new"
  useEffect(() => {
    if (product) {
      reset({
        item_code: product.item_code || "",
        sku: product.sku,
        name: product.name,
        description: product.description || "",
        category_id: product.category === "Uncategorized" ? null : product.category,
        base_unit_id: null,
        reorder_point: product.reorder_point,
        code_locked: product.code_locked || false,
      })
    } else if (productId === "new") {
      reset({
        item_code: "",
        sku: "",
        name: "",
        description: "",
        category_id: null,
        base_unit_id: null,
        reorder_point: 10,
        code_locked: false,
      })
    }
  }, [product, productId, reset])

  const saveMutation = useMutation({
    mutationFn: async (data: ProductFormValues) => {
      if (isEditing) {
        return inventoryService.updateProduct(productId!, data)
      }
      return inventoryService.createProduct({ ...data, item_code: canEnterCode ? data.item_code : undefined })
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["products"] })
      queryClient.invalidateQueries({ queryKey: ["materials"] })
      onClose()
    }
  })

  const onSubmit = (data: ProductFormValues) => {
    saveMutation.mutate(data)
  }

  return (
    <Drawer 
      open={open} 
      onOpenChange={(v) => !v && onClose()} 
      title={isEditing ? "Edit Product" : "New Product"}
      description={isEditing ? `Update details for ${product?.name || "product"}` : "Add a new item to your inventory catalog."}
    >
      {isEditing && isFetching ? (
        <FormSkeleton fields={5} />
      ) : (
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-6 pb-8">
          <div className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="item_code">Item Code</Label>
              <Input 
                id="item_code" 
                placeholder={canEnterCode ? "Enter a custom code" : generationDisabled ? "Auto-generation disabled" : "Auto-generated on save"}
                {...register("item_code")} 
                readOnly={!canEnterCode}
              />
              <p className="text-xs text-muted-foreground">
                {canEnterCode
                  ? "Workspace settings allow a custom code."
                  : generationDisabled ? "Automatic code generation is disabled in ERP settings." : "Automatically generated from ERP settings."}
              </p>
              {errors.item_code && <p className="text-xs text-destructive">{errors.item_code.message}</p>}
            </div>
            <div className="space-y-2">
              <Label htmlFor="sku">SKU / Barcode</Label>
              <Input id="sku" placeholder="E.g. RW-001" {...register("sku")} />
              {errors.sku && <p className="text-xs text-destructive">{errors.sku.message}</p>}
            </div>
            <div className="space-y-2">
              <Label htmlFor="name">Product Name</Label>
              <Input id="name" placeholder="E.g. Raw Material A" {...register("name")} />
              {errors.name && <p className="text-xs text-destructive">{errors.name.message}</p>}
            </div>

            <div className="space-y-2">
              <Label htmlFor="description">Description (Optional)</Label>
              <Textarea id="description" rows={3} {...register("description")} />
            </div>

            <div className="space-y-2">
              <Label htmlFor="category_id">Category</Label>
              <Select 
                value={watch("category_id") || ""} 
                onValueChange={(val) => setValue("category_id", val, { shouldValidate: true })}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select Category" />
                </SelectTrigger>
                <SelectContent>
                  {categories?.map((category) => (
                    <SelectItem key={category.id} value={category.id}>
                      {category.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              {errors.category_id && <p className="text-xs text-destructive">{errors.category_id.message}</p>}
            </div>
            
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="reorder_point">Reorder Point</Label>
                <Input id="reorder_point" type="number" min="0" {...register("reorder_point")} />
                {errors.reorder_point && <p className="text-xs text-destructive">{errors.reorder_point.message}</p>}
              </div>
              <div className="space-y-2">
                <Label htmlFor="base_unit_id">Base Unit</Label>
                <Select
                  value={watch("base_unit_id") || ""}
                  onValueChange={(val) => setValue("base_unit_id", val, { shouldValidate: true })}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Select Unit" />
                  </SelectTrigger>
                  <SelectContent>
                    {units?.map((unit) => (
                      <SelectItem key={unit.id} value={unit.id}>
                        {unit.name} ({unit.code})
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                {errors.base_unit_id && <p className="text-xs text-destructive">{errors.base_unit_id.message}</p>}
              </div>
            </div>
          </div>
          
          <div className="pt-4 flex gap-3 w-full sm:justify-end">
            <Button type="button" variant="outline" onClick={onClose} className="w-full sm:w-auto">Cancel</Button>
            <Button type="submit" disabled={saveMutation.isPending || isLoadingCodePolicy} className="w-full sm:w-auto">
              <Save className="mr-2 h-4 w-4" />
              {saveMutation.isPending ? "Saving..." : "Save Product"}
            </Button>
          </div>
        </form>
      )}
    </Drawer>
  )
}
