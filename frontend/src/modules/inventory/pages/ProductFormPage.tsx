import { useNavigate, useParams } from "react-router-dom"
import { useForm, type SubmitHandler } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import * as z from "zod"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { inventoryService } from "@/services/inventory.service"
import { materialService } from "@/services/material.service"
import { PageHeader } from "@/components/layout/PageHeader"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { FormSkeleton } from "@/components/shared/LoadingSkeleton"
import { ArrowLeft, Save } from "lucide-react"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"

const productSchema = z.object({
  // legacy/required field for existing create/update flows
  sku: z.string().min(3, "SKU must be at least 3 characters"),

  // Phase 2: item code system (optional override)
  item_code: z.string().min(1).max(50).optional(),
  item_type: z.enum(["raw", "finished", "semi_finished"]).optional(),
  code_locked: z.boolean(),

  // core
  name: z.string().min(2, "Name is required"),
  description: z.string().optional(),
  category_id: z.string().uuid("Please select a valid category").nullable().optional(),
  reorder_point: z.coerce.number().min(0),
})

type ProductFormValues = z.infer<typeof productSchema>

export default function ProductFormPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const isEditing = Boolean(id && id !== "new")

  const { data: product, isLoading: isFetching } = useQuery({
    queryKey: ["product", id],
    queryFn: () => inventoryService.getProduct(id!),
    enabled: isEditing,
  })

  const { data: categories } = useQuery({
    queryKey: ["categories"],
    queryFn: () => materialService.getCategories(),
  })

  const { register, handleSubmit, formState: { errors }, setValue, watch } = useForm<ProductFormValues>({
    resolver: zodResolver(productSchema),
    values: product
      ? {
          sku: product.sku,
          name: product.name,
          description: product.description || "",
          category_id: product.category === "Uncategorized" ? null : product.category,
          reorder_point: product.reorder_point,
          // Phase 2 defaults (legacy API may not send these yet)
          code_locked: true,
          item_code: (product as any).item_code ?? undefined,
          item_type: ((product as any).item_type as any) ?? undefined,
        }
      : {
          sku: "",
          name: "",
          description: "",
          category_id: null,
          reorder_point: 10,
          code_locked: true,
          item_code: undefined,
          item_type: undefined,
        },
  })

  const saveMutation = useMutation({
    mutationFn: async (data: ProductFormValues) => {
      if (isEditing) {
        return inventoryService.updateProduct(id!, data)
      }
      return inventoryService.createProduct(data)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["products"] })
      queryClient.invalidateQueries({ queryKey: ["materials"] })
      navigate("/inventory/products")
    }
  })

  const onSubmit: SubmitHandler<ProductFormValues> = (data) => {
    saveMutation.mutate(data)
  }

  if (isEditing && isFetching) {
    return (
      <div className="space-y-6">
        <PageHeader title="Edit Product" />
        <FormSkeleton fields={5} />
      </div>
    )
  }

  return (
    <div className="max-w-3xl space-y-6">
      <div className="flex items-center gap-4">
        <Button variant="ghost" size="icon" onClick={() => navigate("/inventory/products")} aria-label="Back to products">
          <ArrowLeft className="h-5 w-5" />
        </Button>
        <PageHeader 
          title={isEditing ? "Edit Product" : "New Product"} 
          description={isEditing ? `Update details for ${product?.name}` : "Add a new item to your inventory catalog."}
          action={
            <Button onClick={handleSubmit(onSubmit)} disabled={saveMutation.isPending}>
              <Save className="mr-2 h-4 w-4" />
              {saveMutation.isPending ? "Saving..." : "Save Product"}
            </Button>
          }
        />
      </div>

      <div className="grid gap-6 p-6 border rounded-xl bg-card">
        <div className="grid sm:grid-cols-2 gap-4 border-b pb-6">
          <div className="space-y-2">
            <Label htmlFor="sku">SKU / Barcode</Label>
            <Input id="sku" placeholder="E.g. RW-001" {...register("sku")} />
            {errors.sku && <p className="text-xs text-destructive">{errors.sku.message}</p>}
          </div>

          <div className="space-y-2">
            <Label htmlFor="item_code">Item Code (override)</Label>
            <Input id="item_code" placeholder="Auto-generated if empty" {...register("item_code")} />
            {errors.item_code && <p className="text-xs text-destructive">{errors.item_code.message}</p>}
          </div>

          <div className="space-y-2">
            <Label htmlFor="item_type">Item Type</Label>
            <Select value={watch("item_type") || "finished"} onValueChange={(val) => setValue("item_type", val as any, { shouldValidate: true })}>
              <SelectTrigger>
                <SelectValue placeholder="Select item type" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="raw">RAW (RM)</SelectItem>
                <SelectItem value="finished">FG (FG)</SelectItem>
                <SelectItem value="semi_finished">SF (SF)</SelectItem>
              </SelectContent>
            </Select>
            {errors.item_type && <p className="text-xs text-destructive">{errors.item_type.message}</p>}
          </div>

          <div className="space-y-2">
            <Label htmlFor="code_locked">Code Lock</Label>
            <Select value={watch("code_locked") ? "true" : "false"} onValueChange={(val) => setValue("code_locked", val === "true", { shouldValidate: true })}>
              <SelectTrigger>
                <SelectValue placeholder="Lock after creation" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="true">Locked</SelectItem>
                <SelectItem value="false">Unlocked</SelectItem>
              </SelectContent>
            </Select>
            {errors.code_locked && <p className="text-xs text-destructive">{errors.code_locked.message}</p>}
          </div>

          <div className="space-y-2 sm:col-span-2">
            <Label htmlFor="name">Product Name</Label>
            <Input id="name" placeholder="E.g. Raw Material A" {...register("name")} />
            {errors.name && <p className="text-xs text-destructive">{errors.name.message}</p>}
          </div>
        </div>

        <div className="space-y-2 border-b pb-6">
          <Label htmlFor="description">Description (Optional)</Label>
          <Textarea id="description" rows={3} {...register("description")} />
        </div>

        <div className="grid sm:grid-cols-2 gap-4">
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
                    {category.name} ({category.code_prefix})
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            {errors.category_id && <p className="text-xs text-destructive">{errors.category_id.message}</p>}
          </div>
          <div className="space-y-2">
            <Label htmlFor="reorder_point">Reorder Point</Label>
            <Input id="reorder_point" type="number" min="0" {...register("reorder_point")} />
            {errors.reorder_point && <p className="text-xs text-destructive">{errors.reorder_point.message}</p>}
          </div>
        </div>
      </div>
    </div>
  )
}
