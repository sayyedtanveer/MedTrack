import { useState, useEffect } from "react"
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
import { TagInput } from "@/components/ui/tag-input"
import { toast } from "sonner"
import { VariantManager } from "../components/VariantManager"
import { BusinessAssistantPanel, BusinessAssistantConfig } from "@/components/shared/BusinessAssistantPanel"

const panelConfig: BusinessAssistantConfig = {
  pageTitle: "Product Template & Variants",
  about: "This page allows you to define a Master Product (Template) and auto-generate or manually create specific sellable versions (Variants).",
  businessPurpose: "Centralize product data. Sales orders only sell Variants (e.g., Size L, Red) but defining a Template ensures consistent attributes and easier management.",
  erpFlow: [
    { label: "Item Master", active: true },
    { label: "BOM Creation" },
    { label: "Sales Order" },
  ],
  canDo: [
    "Define base details for a product",
    "Specify Variant Attributes (e.g., Color, Size)",
    "Generate combinations of variants automatically",
    "Map variants to Finished Good inventory materials",
  ],
  screenWalkthrough: [
    { section: "Basic Information", purpose: "Set name, category, and base unit", impact: "Used across all variants" },
    { section: "Product Variants", purpose: "Define variant attributes like Color and Size", impact: "Enables automatic generation of variant combinations" },
    { section: "Variants Tab (Edit Mode)", purpose: "Create, activate, and set prices for variants", impact: "Makes items available for Sales Orders" },
  ],
  fieldGuide: [
    { field: "Variant Attribute Name", purpose: "What the user sees in the UI", meaning: "Friendly name", example: "Color" },
    { field: "Variant Attribute Key", purpose: "Internal database key", meaning: "Used by API", example: "color", bestPractice: "Lowercase, underscores only" },
    { field: "Variant Options", purpose: "Available choices", meaning: "Values like Black, White", example: "Black, White" },
  ],
  buttonGuide: [
    { button: "Generate Variants", what: "Creates variant combinations from attributes", continues: "Adds to Variant grid", reversible: true },
    { button: "Save Template", what: "Saves basic information", continues: "Navigates to edit mode if new", reversible: true },
  ],
  beforeYouStart: ["Product Categories must exist", "Units of Measure must exist"],
  afterSave: [
    { label: "Add Variants" },
    { label: "Set Selling Price" },
    { label: "Link to BOM" },
  ],
  bestPractices: [
    "Keep Variant Attributes simple (2-3 max) to avoid generating hundreds of variants",
    "Always set a selling price for variants before using them in Sales Orders"
  ],
  commonMistakes: [
    "Creating a template but forgetting to generate variants",
    "Putting spaces or special characters in the Attribute Key"
  ],
  relatedScreens: [
    { label: "Sales Orders", href: "/sales/orders" },
    { label: "Inventory Materials", href: "/inventory/materials" },
  ],
  faqs: [
    { question: "Why is the variant grid missing?", answer: "You must save the Template first. Variants can only be added to an existing template." },
    { question: "Can I sell a template?", answer: "No, Sales Orders only accept Variants." },
  ],
  tips: ["Use 'Generate Variants' in edit mode to instantly create all possible combinations of your attributes."],
  warnings: ["Changing variant attributes after generating variants will not automatically delete old variants."],
  successResult: ["Template is created", "Variants can be added in the bottom section"],
}


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
  const [attributes, setAttributes] = useState<{ key: string; label: string; values?: string[]; _isNew?: boolean }[]>([])

  // Load existing data if edit mode
  const { data: templateData, isSuccess } = useQuery({
    queryKey: ["products", "template", id],
    queryFn: () => productService.getTemplate(id!),
    enabled: !isNew,
  })

  // Initialize form state when data loads
  useEffect(() => {
    if (isSuccess && templateData) {
      setCode(templateData.item_code || templateData.code || "")
      setName(templateData.name || "")
      setDescription(templateData.description || "")
      setCategoryId(templateData.category_id || "")
      setBaseUnitId(templateData.base_unit_id || "")
      setIsActive(templateData.is_active ?? true)
      setAttributes(templateData.attributes || [])
    }
  }, [isSuccess, templateData])

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

    // Attribute Validation
    const seenNames = new Set<string>()
    for (const attr of attributes) {
      const trimmedLabel = attr.label.trim()
      if (!trimmedLabel) {
        return toast.error("Variant attribute name is required.")
      }

      const lowerLabel = trimmedLabel.toLowerCase()
      if (seenNames.has(lowerLabel)) {
        return toast.error(`Duplicate attribute name found: "${trimmedLabel}"`)
      }
      seenNames.add(lowerLabel)

      const rawOptions = attr.values ?? []
      const validOptions = rawOptions.map(v => v.trim()).filter(Boolean)
      
      if (validOptions.length === 0) {
        return toast.error("Add at least one option to this variant attribute.")
      }

      const seenOptions = new Set<string>()
      for (const opt of validOptions) {
        const lowerOpt = opt.toLowerCase()
        if (seenOptions.has(lowerOpt)) {
          return toast.error(`Duplicate option "${opt}" found in attribute "${trimmedLabel}"`)
        }
        seenOptions.add(lowerOpt)
      }
    }

    const payload: any = {
      item_code: code.trim() || null,
      name,
      description,
      attributes: attributes.map((attr) => {
        // We preserve casing for display, but remove duplicates case-insensitively
        const uniqueValues: string[] = []
        const seen = new Set<string>()
        for (const val of (attr.values ?? [])) {
          const trimmed = val.trim()
          if (trimmed && !seen.has(trimmed.toLowerCase())) {
            seen.add(trimmed.toLowerCase())
            uniqueValues.push(trimmed)
          }
        }
        return {
          key: attr.key.trim(),
          label: attr.label.trim(),
          values: uniqueValues,
        }
      }),
    }
    payload.category_id = categoryId
    if (baseUnitId) payload.base_unit_id = baseUnitId
    if (!isNew && templateData) {
      const originalIsActive = templateData.is_active ?? true
      if (isActive !== originalIsActive) {
        payload.is_active = isActive
      }
    }
    mutation.mutate(payload)
  }

  const addAttr = () => setAttributes([...attributes, { key: "", label: "", values: [], _isNew: true }])
  const updateAttr = (i: number, field: "key"|"label", val: string) => {
    const arr = [...attributes]
    arr[i][field] = val
    if (field === "label" && arr[i]._isNew) {
      arr[i].key = val.toLowerCase().replace(/[^a-z0-9]/g, "_")
    }
    setAttributes(arr)
  }
  const updateAttrValues = (i: number, val: string[]) => {
    const arr = [...attributes]
    arr[i].values = val
    setAttributes(arr)
  }
  const removeAttr = (i: number) => setAttributes(attributes.filter((_, idx) => idx !== i))

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div className="flex items-center gap-3">
        <Button variant="ghost" size="icon" onClick={() => navigate("/products")} aria-label="Back to products"><ArrowLeft className="w-4 h-4" /></Button>
        <h1 className="text-xl font-semibold flex-1">{isNew ? "New Product Template" : "Edit Template"}</h1>
        <BusinessAssistantPanel config={panelConfig} triggerLabel="Help" />
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
            <h2 className="text-base font-medium">Product Variants</h2>
            {canEdit && <Button variant="ghost" size="sm" className="h-7 text-xs" onClick={addAttr}><Plus className="w-3.5 h-3.5 mr-1" /> Add Attribute</Button>}
          </div>
          <div className="text-sm text-muted-foreground space-y-1">
            <p>Define variant attributes such as Size, Color, or Voltage and their available options.</p>
            <p className="text-xs">Example: Color → Black, White</p>
          </div>
          <div className="space-y-4 flex-1 overflow-y-auto pt-2">
            {attributes.length > 0 && (
              <div className="grid grid-cols-1 md:grid-cols-[1fr_2fr_auto] gap-3 mb-1 px-1 text-xs font-medium text-muted-foreground">
                <div>Attribute Name</div>
                <div>Options</div>
                <div></div>
              </div>
            )}
            {attributes.map((attr, i) => (
              <div key={i} className="grid grid-cols-1 md:grid-cols-[1fr_2fr_auto] gap-3 items-start p-3 border rounded-lg bg-muted/10">
                <div className="flex-1 space-y-1">
                  <Input value={attr.label} onChange={e => updateAttr(i, "label", e.target.value)} disabled={!canEdit} placeholder="e.g. Color" className="text-sm font-medium" />
                </div>
                <div className="flex-1 space-y-1">
                  <TagInput
                    value={attr.values ?? []}
                    onChange={(newValues) => updateAttrValues(i, newValues)}
                    disabled={!canEdit}
                    placeholder="Type an option and press Enter..."
                  />
                </div>
                {canEdit && (
                  <Button variant="ghost" size="icon" className="h-9 w-9 text-muted-foreground hover:text-destructive" onClick={() => removeAttr(i)} aria-label="Remove attribute">
                    <Trash2 className="w-4 h-4" />
                  </Button>
                )}
              </div>
            ))}
            {attributes.length === 0 && <div className="text-center py-8 text-sm text-muted-foreground border border-dashed rounded-lg">No attributes defined. The product will exist as a single standard item.</div>}
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
