import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { useState, type ChangeEvent } from "react"
import { useParams, useNavigate } from "react-router-dom"
import { ChevronLeft, Download, Upload, Loader2, Edit2 } from "lucide-react"
import { productService } from "@/services/product.service"
import { Button } from "@/components/ui/button"
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { toast } from "sonner"
import { formatCurrency } from "@/utils/currency"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { useSearchParams } from "react-router-dom"
import { bomService } from "@/services/bom.service"
import { Layers, Plus } from "lucide-react"

interface BulkImportError {
  row_number: number
  field: string
  message: string
}

export default function ProductDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const qc = useQueryClient()

  const [searchParams, setSearchParams] = useSearchParams()
  const currentTab = searchParams.get("tab") || "overview"
  const setTab = (tab: string) => setSearchParams({ tab })

  const [showImport, setShowImport] = useState(false)
  const [csvContent, setCsvContent] = useState("")
  const [showErrors, setShowErrors] = useState(false)
  const [importErrors, setImportErrors] = useState<BulkImportError[]>([])

  // Load product
  const { data: product, isLoading: loadingTemplate } = useQuery({
    queryKey: ["products", "template", id],
    queryFn: () => productService.getTemplate(id!),
  })

  // Load variants
  const { data: variants, isLoading: loadingVariants } = useQuery({
    queryKey: ["products", "template", id, "variants"],
    queryFn: () => productService.getVariants(id!, { page_size: 100 }),
    enabled: !!id,
  })

  // Load images
  const { data: images } = useQuery({
    queryKey: ["products", "template", id, "images"],
    queryFn: () => productService.getTemplateImages(id!),
    enabled: !!id,
  })

  // Load BOMs
  const { data: boms, isLoading: loadingBOMs } = useQuery({
    queryKey: ["boms", "template", id],
    queryFn: () => bomService.getBOMsForProduct(id!, true),
    enabled: !!id,
  })

  // Get import template
  const getTemplateMutation = useMutation({
    mutationFn: () => productService.getImportTemplate(id!),
    onSuccess: (data) => {
      const blob = new Blob([data.csv_content], { type: "text/csv" })
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement("a")
      a.href = url
      a.download = data.file_name
      a.click()
      window.URL.revokeObjectURL(url)
    },
  })

  // Import variants
  const importMutation = useMutation({
    mutationFn: (csv: string) => productService.bulkImportVariants(id!, { csv_data: csv }),
    onSuccess: (result) => {
      qc.invalidateQueries({ queryKey: ["products", "template", id, "variants"] })
      setShowImport(false)
      setCsvContent("")
      if (result.error_count > 0) {
        setImportErrors(result.errors)
        setShowErrors(true)
        toast.warning(`Imported ${result.success_count} variants with ${result.error_count} errors`)
      } else {
        toast.success(`Successfully imported ${result.success_count} variants`)
      }
    },
    onError: (err: any) => toast.error(err?.response?.data?.detail || "Import failed"),
  })

  // Bulk activate
  const activateMutation = useMutation({
    mutationFn: (variantIds: string[]) => productService.bulkActivateVariants(id!, variantIds),
    onSuccess: (result) => {
      qc.invalidateQueries({ queryKey: ["products", "template", id, "variants"] })
      toast.success(`Activated ${result.success_count} variants`)
    },
  })

  // Bulk deactivate
  const deactivateMutation = useMutation({
    mutationFn: (variantIds: string[]) => productService.bulkDeactivateVariants(id!, variantIds),
    onSuccess: (result) => {
      qc.invalidateQueries({ queryKey: ["products", "template", id, "variants"] })
      toast.success(`Deactivated ${result.success_count} variants`)
    },
  })

  const handleCsvUpload = async (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (!file) return
    setCsvContent(await file.text())
  }

  if (loadingTemplate) return <div className="p-8">Loading...</div>
  if (!product) return <div className="p-8">Product not found</div>

  const activeVariants = variants?.items.filter(v => v.is_active) || []
  const inactiveVariants = variants?.items.filter(v => !v.is_active) || []

  return (
    <div className="space-y-6 pb-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Button variant="ghost" size="icon" onClick={() => navigate("/products")} aria-label="Back to products">
            <ChevronLeft className="w-4 h-4" />
          </Button>
          <div>
            <h1 className="text-2xl font-bold">{product.name}</h1>
            <p className="text-sm text-muted-foreground">{product.code}</p>
          </div>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={() => navigate(`/products/${id}/edit`)} size="sm">
            <Edit2 className="w-4 h-4 mr-1" />
            Edit Product
          </Button>
          <Button variant="outline" onClick={() => navigate(`/products/${id}/edit`)} size="sm">
            <Plus className="w-4 h-4 mr-1" />
            Add Variant
          </Button>
          <Button onClick={() => navigate(`/bom/new?template_id=${id}`)} size="sm">
            <Layers className="w-4 h-4 mr-1" />
            Create BOM
          </Button>
        </div>
      </div>

      <Tabs value={currentTab} onValueChange={setTab} className="w-full">
        <TabsList className="mb-4">
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="variants">Variants ({variants?.total || 0})</TabsTrigger>
          <TabsTrigger value="bom">BOMs ({boms?.items.length || 0})</TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="space-y-6 mt-0">
          {/* Quick Stats */}
          <div className="grid grid-cols-4 gap-4">
            <div className="rounded-lg border bg-card p-4">
              <p className="text-sm text-muted-foreground">Total Variants</p>
              <p className="text-2xl font-bold">{variants?.total || 0}</p>
            </div>
            <div className="rounded-lg border bg-card p-4">
              <p className="text-sm text-muted-foreground">Active Variants</p>
              <p className="text-2xl font-bold text-green-600">{activeVariants.length}</p>
            </div>
            <div className="rounded-lg border bg-card p-4">
              <p className="text-sm text-muted-foreground">BOMs</p>
              <p className="text-2xl font-bold text-blue-600">{boms?.items.length || 0}</p>
            </div>
            <div className="rounded-lg border bg-card p-4">
              <p className="text-sm text-muted-foreground">Images</p>
              <p className="text-2xl font-bold">{images?.items.length || 0}</p>
            </div>
          </div>

          {/* Images Gallery */}
          {images && images.items.length > 0 && (
            <div className="rounded-lg border bg-card p-6">
              <h2 className="text-lg font-semibold mb-4">Product Images ({images.items.length})</h2>
              <div className="grid grid-cols-6 gap-4">
                {images.items.map((img: any) => (
                  <div key={img.id} className="relative group rounded-lg overflow-hidden bg-muted aspect-square flex items-center justify-center">
                    <img src={img.file_path} alt={img.file_name} className="w-full h-full object-cover" />
                    {img.is_primary && (
                      <div className="absolute top-1 right-1 bg-blue-600 text-white text-xs px-2 py-1 rounded">Primary</div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
        </TabsContent>

        <TabsContent value="variants" className="space-y-6 mt-0">
          <div className="rounded-lg border bg-card p-6">
            <div className="flex gap-2 mb-4">
              <h2 className="text-lg font-semibold flex-1">Variants ({variants?.total})</h2>
              <Button variant="outline" onClick={() => getTemplateMutation.mutate()} size="sm">
                <Download className="w-4 h-4 mr-1" />
                {getTemplateMutation.isPending ? "Downloading..." : "Download Template"}
              </Button>
              <Button onClick={() => setShowImport(true)} size="sm">
                <Upload className="w-4 h-4 mr-1" />
                Import Variants
              </Button>
              {activeVariants.length > 0 && (
                <Button variant="outline" size="sm" onClick={() => deactivateMutation.mutate(activeVariants.map(v => v.id))}>
                  Deactivate All Active
                </Button>
              )}
              {inactiveVariants.length > 0 && (
                <Button variant="outline" size="sm" onClick={() => activateMutation.mutate(inactiveVariants.map(v => v.id))}>
                  Activate All Inactive
                </Button>
              )}
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="border-b">
                  <tr>
                    <th className="h-10 px-4 text-left font-medium">Code</th>
                    <th className="h-10 px-4 text-left font-medium">Name</th>
                    <th className="h-10 px-4 text-left font-medium">Attributes</th>
                    <th className="h-10 px-4 text-right font-medium">Cost</th>
                    <th className="h-10 px-4 text-right font-medium">Price</th>
                    <th className="h-10 px-4 text-center font-medium">Status</th>
                    <th className="h-10 px-4 text-center font-medium">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y">
                  {loadingVariants ? (
                    <tr>
                      <td colSpan={7} className="py-10 text-center text-muted-foreground">
                        <Loader2 className="w-5 h-5 animate-spin mx-auto" />
                      </td>
                    </tr>
                  ) : variants?.items.length === 0 ? (
                    <tr>
                      <td colSpan={7} className="py-10 text-center text-muted-foreground">
                        <div className="space-y-3">
                          <p>No variants yet. Create one standard SKU or import variant rows before using this product in sales and production.</p>
                          <Button variant="outline" size="sm" onClick={() => navigate(`/products/${id}/edit`)}>
                            <Edit2 className="w-4 h-4 mr-1" />
                            Add Variant
                          </Button>
                        </div>
                      </td>
                    </tr>
                  ) : (
                    variants?.items.map(v => (
                      <tr key={v.id} className="hover:bg-muted/30">
                        <td className="px-4 py-3 font-mono text-xs">{v.code}</td>
                        <td className="px-4 py-3">{v.name}</td>
                        <td className="px-4 py-3 text-xs max-w-xs overflow-hidden text-ellipsis">
                          {Object.entries(v.attribute_values).map(([k, val]) => (
                            <span key={k} className="inline-block mr-2 bg-muted px-2 py-1 rounded">
                              {k}: {String(val)}
                            </span>
                          ))}
                        </td>
                        <td className="px-4 py-3 text-right">{formatCurrency(Number(v.standard_cost))}</td>
                        <td className="px-4 py-3 text-right">{v.selling_price ? formatCurrency(Number(v.selling_price)) : "-"}</td>
                        <td className="px-4 py-3 text-center">
                          <span className="inline-block px-2 py-1 rounded text-xs bg-opacity-20" 
                                style={{ backgroundColor: v.is_active ? "rgb(34 197 94 / 0.2)" : "rgb(239 68 68 / 0.2)" }}>
                            {v.is_active ? "Active" : "Inactive"}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-center">
                          <Button variant="ghost" size="sm" onClick={() => navigate(`/bom/new?variant_id=${v.id}`)}>
                            Create BOM
                          </Button>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </TabsContent>

        <TabsContent value="bom" className="space-y-6 mt-0">
          <div className="rounded-lg border bg-card p-6">
            <div className="flex gap-2 mb-4">
              <h2 className="text-lg font-semibold flex-1">Bills of Materials</h2>
              <Button onClick={() => navigate(`/bom/new?template_id=${id}`)} size="sm">
                <Layers className="w-4 h-4 mr-1" />
                Create BOM
              </Button>
            </div>
            
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="border-b">
                  <tr>
                    <th className="h-10 px-4 text-left font-medium">Version</th>
                    <th className="h-10 px-4 text-left font-medium">Target</th>
                    <th className="h-10 px-4 text-left font-medium">Status</th>
                    <th className="h-10 px-4 text-center font-medium">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y">
                  {loadingBOMs ? (
                    <tr>
                      <td colSpan={4} className="py-10 text-center text-muted-foreground">
                        <Loader2 className="w-5 h-5 animate-spin mx-auto" />
                      </td>
                    </tr>
                  ) : boms?.items.length === 0 ? (
                    <tr>
                      <td colSpan={4} className="py-10 text-center text-muted-foreground">
                        No BOMs found for this product.
                      </td>
                    </tr>
                  ) : (
                    boms?.items.map(bom => (
                      <tr key={bom.id} className="hover:bg-muted/30">
                        <td className="px-4 py-3 font-mono text-sm font-medium">{bom.version}</td>
                        <td className="px-4 py-3">
                          {bom.variant_id ? "Variant Specific" : "Template Wide"}
                        </td>
                        <td className="px-4 py-3">
                          <span className="inline-block px-2 py-1 rounded text-xs bg-opacity-20" 
                                style={{ backgroundColor: bom.is_active ? "rgb(34 197 94 / 0.2)" : "rgb(239 68 68 / 0.2)" }}>
                            {bom.is_active ? "Active" : "Inactive"}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-center">
                          <Button variant="ghost" size="sm" onClick={() => navigate(`/bom/list/${bom.id}`)}>
                            View Details
                          </Button>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </TabsContent>
      </Tabs>

      {/* Import Dialog */}
      <Dialog open={showImport} onOpenChange={setShowImport}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>Import Variants</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <div className="rounded-lg border bg-muted/30 p-3 text-sm text-muted-foreground">
              Download the template, fill one row per SKU/variant, then upload the CSV or paste it below.
              Attribute columns must match this product template; standard cost is required and selling price is optional.
            </div>
            <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
              <input
                type="file"
                accept=".csv,text/csv"
                onChange={handleCsvUpload}
                className="text-sm"
              />
              <Button variant="outline" size="sm" onClick={() => getTemplateMutation.mutate()}>
                <Download className="w-4 h-4 mr-1" />
                Download Template
              </Button>
            </div>
            <div>
              <label className="text-sm font-medium">CSV Content</label>
              <textarea
                value={csvContent}
                onChange={e => setCsvContent(e.target.value)}
                placeholder="Paste CSV here, e.g. SIZE,COLOR,standard_cost,selling_price"
                className="w-full h-64 p-3 border rounded font-mono text-sm"
              />
            </div>
            <div className="flex justify-end gap-2">
              <Button variant="outline" onClick={() => setShowImport(false)}>Cancel</Button>
              <Button onClick={() => importMutation.mutate(csvContent)} disabled={importMutation.isPending || !csvContent.trim()}>
                {importMutation.isPending ? "Importing..." : "Import"}
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>

      {/* Errors Dialog */}
      <Dialog open={showErrors} onOpenChange={setShowErrors}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>Import Errors ({importErrors.length})</DialogTitle>
          </DialogHeader>
          <div className="space-y-2 max-h-96 overflow-y-auto">
            {importErrors.map((err, i) => (
              <div key={i} className="p-3 rounded border border-red-200 bg-red-50">
                <p className="font-mono text-sm">Row {err.row_number}, {err.field}:</p>
                <p className="text-sm text-red-700">{err.message}</p>
              </div>
            ))}
          </div>
        </DialogContent>
      </Dialog>
    </div>
  )
}
