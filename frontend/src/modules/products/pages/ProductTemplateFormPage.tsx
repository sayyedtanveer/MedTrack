import { useState } from "react"
import { useParams, useNavigate } from "react-router-dom"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { ArrowLeft, Save, Plus, Trash2 } from "lucide-react"
import { productService, CreateTemplateInput, UpdateTemplateInput } from "@/services/product.service"
import { materialService } from "@/services/material.service"
import { usePermissions } from "@/hooks/usePermissions"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { Checkbox } from "@/components/ui/checkbox"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { toast } from "sonner"
import { VariantManager } from "../components/VariantManager"

export default function ProductTemplateFormPage() {
  const { id } = useParams()
  const isNew = !id || id === "new"
  const navigate = useNavigate()
  const qc = useQueryClient()
  const { hasRole } = usePermissions()
  const canEdit = hasRole(["ADMIN", "MANAGER"])

  // Form state
  const [code, setCode] = useState("")
  const [name, setName] = useState("")
  const [description, setDescription] = useState("")
  const [categoryId, setCategoryId] = useState("")
  const [baseUnitId, setBaseUnitId] = useState("")
  const [isActive, setIsActive] = useState(true)
  const [attributes, setAttributes] = useState<{ key: string; label: string; values?: string[] }[]>([])

  // Load existing data if edit mode
  const { data: templateData } = useQuery({
    queryKey: ["products", "template", id],
    queryFn: async () => {
      const tpl = await productService.getTemplate(id!)
      setCode(tpl.item_code || tpl.code)
      setName(tpl.name)
      setDescription(tpl.description || "")
      setCategoryId(tpl.category_id || "")
      setBaseUnitId(tpl.base_unit_id || "")
      setIsActive(tpl.is_active)
      setAttributes(tpl.attributes || [])
      return tpl
    },
    enabled: !isNew,
  })

  // Load categories and units (assuming shared from materialService for now)
  const { data: units } = useQuery({ queryKey: ["units"], queryFn: materialService.getUnits, staleTime: 60_000 })
  const { data: categories } = useQuery({ queryKey: ["categories"], queryFn: materialService.getCategories, staleTime: 60_000 })

  const mutation = useMutation({
    mutationFn: (payload: any) => isNew ? productService.createTemplate(payload as CreateTemplateInput) : productService.updateTemplate(id!, payload as UpdateTemplateInput),
    onSuccess: (data) => {
      qc.invalidateQueries({ queryKey: ["products", "templates"] })
      toast.success(isNew ? "Template created" : "Template updated")
      mutation.reset()
      navigate(`/products/${data.id}`, { replace: true })
    },
    onError: (err: any) => {
      toast.error(err?.response?.data?.detail || "Failed to save template")
      mutation.reset()
    }
  })

  const save = () => {
    if (!name.trim()) return toast.error("Name is required")
    if (!categoryId) return toast.error("Category is required")
    const payload: any = {
      item_code: code.trim() || null,
      name,
      description,
      attributes: attributes.map((attr) => ({
        key: attr.key.trim(),
        label: attr.label.trim(),
        values: (attr.values ?? []).map((value) => value.trim()).filter(Boolean),
      })),
    }
    payload.category_id = categoryId
    if (baseUnitId) payload.base_unit_id = baseUnitId
    if (!isNew) payload.is_active = isActive
    mutation.mutate(payload)
  }

  const addAttr = () => setAttributes([...attributes, { key: "", label: "", values: [] }])
  const updateAttr = (i: number, field: "key"|"label", val: string) => {
    const arr = [...attributes]
    arr[i][field] = val
    if (field === "label" && !arr[i].key) {
      arr[i].key = val.toLowerCase().replace(/[^a-z0-9]/g, "_")
    }
    setAttributes(arr)
  }
  const updateAttrValues = (i: number, val: string) => {
    const arr = [...attributes]
    arr[i].values = val.split(",").map((value) => value.trim()).filter(Boolean)
    setAttributes(arr)
  }
  const removeAttr = (i: number) => setAttributes(attributes.filter((_, idx) => idx !== i))

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div className="flex items-center gap-3">
        <Button variant="ghost" size="icon" onClick={() => navigate("/products")} aria-label="Back to products"><ArrowLeft className="w-4 h-4" /></Button>
        <h1 className="text-xl font-semibold flex-1">{isNew ? "New Product Template" : "Edit Template"}</h1>
        {canEdit && (
          <Button onClick={save} disabled={mutation.isPending}>
            <Save className="w-4 h-4 mr-2" />
            {mutation.isPending ? "Saving..." : "Save"}
          </Button>
        )}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="space-y-4 rounded-xl border bg-card p-5">
          <h2 className="text-base font-medium border-b pb-2">Basic Information</h2>
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label>Item Code</Label>
              <Input value={code} onChange={e => setCode(e.target.value)} disabled={!canEdit || !isNew} placeholder="Auto-generate if blank" />
            </div>
            <div className="space-y-2">
              <Label>Name</Label>
              <Input value={name} onChange={e => setName(e.target.value)} disabled={!canEdit} placeholder="Widget V1" />
            </div>
            <div className="col-span-2 space-y-2">
              <Label>Description</Label>
              <Textarea value={description} onChange={e => setDescription(e.target.value)} disabled={!canEdit} rows={2} />
            </div>
            <div className="space-y-2">
              <Label>Category</Label>
              <Select value={categoryId} onValueChange={setCategoryId} disabled={!canEdit}>
                <SelectTrigger><SelectValue placeholder="Select..." /></SelectTrigger>
                <SelectContent>
                  {categories?.map(c => <SelectItem key={c.id} value={c.id}>{c.name}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>Base Unit</Label>
              <Select value={baseUnitId} onValueChange={setBaseUnitId} disabled={!canEdit}>
                <SelectTrigger><SelectValue placeholder="Select..." /></SelectTrigger>
                <SelectContent>
                  {units?.map(u => <SelectItem key={u.id} value={u.id}>{u.code}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
            {!isNew && (
              <div className="col-span-2 flex items-center justify-between pt-2">
                <div className="space-y-0.5">
                  <Label>Active Status</Label>
                  <p className="text-xs text-muted-foreground">Inactive templates cannot be used in new BOMs.</p>
                </div>
                <div className="flex items-center space-x-2">
                  <Checkbox id="is-active" checked={isActive} onCheckedChange={(val) => setIsActive(!!val)} disabled={!canEdit} />
                  <label htmlFor="is-active" className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70">
                    Active
                  </label>
                </div>
              </div>
            )}
          </div>
        </div>

        <div className="space-y-4 rounded-xl border bg-card p-5 flex flex-col">
          <div className="flex items-center justify-between border-b pb-2">
            <h2 className="text-base font-medium">Dynamic Attributes</h2>
            {canEdit && <Button variant="ghost" size="sm" className="h-7 text-xs" onClick={addAttr}><Plus className="w-3.5 h-3.5 mr-1" /> Add</Button>}
          </div>
          <p className="text-sm text-muted-foreground">
            Define variant attributes and allowed values, e.g. Size = S, M, L or Voltage = 110V, 220V.
          </p>
          <div className="space-y-3 flex-1 overflow-y-auto">
            {attributes.map((attr, i) => (
              <div key={i} className="grid grid-cols-1 md:grid-cols-[1fr_1fr_1.4fr_auto] gap-2 items-start">
                <div className="flex-1 space-y-1">
                  <Input value={attr.label} onChange={e => updateAttr(i, "label", e.target.value)} disabled={!canEdit} placeholder="Label (e.g. Storage Size)" className="h-8 text-sm" />
                </div>
                <div className="flex-1 space-y-1">
                  <Input value={attr.key} onChange={e => updateAttr(i, "key", e.target.value)} disabled={!canEdit} placeholder="key (e.g. storage_size)" className="h-8 text-sm font-mono text-xs" />
                </div>
                <div className="flex-1 space-y-1">
                  <Input
                    value={(attr.values ?? []).join(", ")}
                    onChange={e => updateAttrValues(i, e.target.value)}
                    disabled={!canEdit}
                    placeholder="Allowed values, comma separated"
                    className="h-8 text-sm"
                  />
                </div>
                {canEdit && (
                  <Button variant="ghost" size="icon" className="h-8 w-8 text-destructive" onClick={() => removeAttr(i)} aria-label="Remove attribute">
                    <Trash2 className="w-3.5 h-3.5" />
                  </Button>
                )}
              </div>
            ))}
            {attributes.length === 0 && <div className="text-center py-6 text-sm text-muted-foreground border border-dashed rounded-lg">No attributes defined. All variants will rely strictly on auto-generation or manual key entry.</div>}
          </div>
        </div>
      </div>
      
      {!isNew && templateData && (
        <div className="rounded-xl border bg-card p-5">
           <VariantManager template={templateData} canEdit={canEdit} />
        </div>
      )}
    </div>
  )
}
