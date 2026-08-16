import { useState, useEffect } from "react"
import { useParams, useNavigate, useSearchParams } from "react-router-dom"
import { useQuery, useQueryClient, useMutation } from "@tanstack/react-query"
import {
  ArrowLeft, GitBranch, Package2, Zap, Lock, AlertCircle, Trash2
} from "lucide-react"
import { bomService } from "@/services/bom.service"
import { productService } from "@/services/product.service"
import { BOM, ItemTemplate, ItemVariant } from "@/types/bom.types"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Skeleton } from "@/components/ui/skeleton"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { Separator } from "@/components/ui/separator"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"
import { usePermissions } from "@/hooks/usePermissions"
import { BOMTreeView } from "../components/BOMTreeView"
import { BOMLineList } from "../components/BOMLineList"
import { BOMVersionPanel } from "../components/BOMVersionPanel"
import { BOMCostBreakdown } from "../components/BOMCostBreakdown"
import { BOMOperationList } from "../components/BOMOperationList"
import { BOMActivateDialog } from "../components/BOMActivateDialog"
import { BOMCopyDialog } from "../components/BOMCopyDialog"
import { ProductSelectionModal } from "../components/ProductSelectionModal"
import { VersionSelectionPanel } from "../components/VersionSelectionPanel"
import { toast } from "sonner"

export default function BOMDetailPage() {
  const { bomId } = useParams<{ bomId: string }>()
  const navigate = useNavigate()
  const qc = useQueryClient()
  const { canEditBOM } = usePermissions()

  const [activateOpen, setActivateOpen] = useState(false)
  const [copyOpen, setCopyOpen] = useState(false)
  const [activeTab, setActiveTab] = useState("builder")
  const [searchParams] = useSearchParams()
  const templateIdParam = searchParams.get("template_id")
  const variantIdParam = searchParams.get("variant_id")
  
  // For NEW BOM creation flow
  const [creationStep, setCreationStep] = useState<"select-product" | "select-version">("select-product")
  const [selectedProduct, setSelectedProduct] = useState<{
    product: ItemTemplate | ItemVariant
    isTemplate: boolean
  } | null>(null)

  const isNewBOM = bomId === "new"

  // Reset creation state when navigating to /bom/new without params
  useEffect(() => {
    if (isNewBOM && !templateIdParam && !variantIdParam) {
      setCreationStep("select-product")
      setSelectedProduct(null)
    }
  }, [bomId, templateIdParam, variantIdParam])

  // Automatically fetch product if query params are present
  useEffect(() => {
    async function fetchProduct() {
      if (isNewBOM && (templateIdParam || variantIdParam) && !selectedProduct) {
        try {
          if (templateIdParam) {
            const product = await bomService.getTemplate(templateIdParam)
            setSelectedProduct({ product, isTemplate: true })
            setCreationStep("select-version")
          } else if (variantIdParam) {
            // productService.getVariant returns an ItemVariant which has the same base shape
            const product = await productService.getVariant(variantIdParam) as unknown as ItemVariant
            setSelectedProduct({ product, isTemplate: false })
            setCreationStep("select-version")
          }
        } catch (error) {
          toast.error("Failed to load product from URL parameters")
        }
      }
    }
    fetchProduct()
  }, [isNewBOM, templateIdParam, variantIdParam, selectedProduct])

  // For existing BOMs: fetch the BOM data
  const { data: bom, isLoading, isError, error, refetch } = useQuery({
    queryKey: ["bom", bomId],
    queryFn: () => bomService.getBOM(bomId!),
    enabled: !!bomId && !isNewBOM,
    staleTime: 30_000,
  })

  // Mutation for creating new BOM
  const createBOMMutation = useMutation({
    mutationFn: async () => {
      if (!selectedProduct) throw new Error("No product selected")
      const isTemplate = selectedProduct.isTemplate
      const productId = selectedProduct.product.id
      
      // Calculate next version
      const versionsRes = await bomService.getBOMsForProduct(productId, isTemplate)
      const versions = versionsRes.items.map(b => b.version).sort()
      const nextVersion = versions.length > 0 
        ? `v${parseInt(versions[versions.length - 1].substring(1)) + 1}.0`
        : "v1.0"

      const payload: any = {
        version: nextVersion,
        valid_from: new Date().toISOString(),
        lines: [],
      }
      
      if (isTemplate) {
        payload.template_id = productId
      } else {
        payload.variant_id = productId
      }
      
      return bomService.createBOM(productId, payload)
    },
    onSuccess: (newBom) => {
      toast.success("BOM created successfully")
      qc.invalidateQueries({ queryKey: ["product-boms"] })
      navigate(`/bom/${newBom.id}`)
    },
    onError: (err: any) => {
      const message = err.response?.data?.detail || err.message || "Failed to create BOM"
      toast.error(typeof message === "string" ? message : JSON.stringify(message))
    },
  })

  // Fetch product context for version panel
  const productId = bom?.variant_id ?? bom?.template_id
  const isTemplateType = !bom?.variant_id

  const targetQuery = useQuery({
    queryKey: ["bom-target", bom?.template_id, bom?.variant_id],
    queryFn: async () => {
      if (bom?.template_id) {
        const t = await bomService.getTemplate(bom.template_id)
        return { isTemplate: true, product: t, template: t, variant: null }
      }
      if (bom?.variant_id) {
        // productService.getVariant returns ItemVariant
        const v = await productService.getVariant(bom.variant_id) as unknown as ItemVariant
        // We need the template to get the product name
        // The variant has template_id
        const t = await bomService.getTemplate(v.template_id)
        return { isTemplate: false, product: v, template: t, variant: v }
      }
      return null
    },
    enabled: !!bom,
    staleTime: 60_000,
  })

  // ─── NEW BOM CREATION FLOW ────────────────────────────────────────────────────

  if (isNewBOM) {
    // Step 1: Select Product
    if (creationStep === "select-product") {
      return (
        <div className="w-full max-w-2xl">
          <div className="mb-6">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => navigate("/bom/list")}
              className="-ml-2 mb-4"
            >
              <ArrowLeft className="w-4 h-4 mr-1" />
              Back
            </Button>
          </div>
          <div className="border rounded-lg p-6 space-y-6 bg-card">
            <h2 className="text-2xl font-bold mb-4">Create New Bill of Materials</h2>
            <ProductSelectionModal
              onSelect={(product, isTemplate) => {
                setSelectedProduct({ product, isTemplate })
                setCreationStep("select-version")
              }}
              onCancel={() => navigate("/bom/list")}
            />
          </div>
        </div>
      )
    }

    // Step 2: Select Version (create new or open existing)
    if (creationStep === "select-version" && selectedProduct) {
      return (
        <div className="w-full max-w-2xl space-y-6">
          {/* Header */}
          <div className="flex items-center gap-3">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setCreationStep("select-product")}
              className="-ml-2"
            >
              <ArrowLeft className="w-4 h-4 mr-1" />
              Back
            </Button>
            <h1 className="text-2xl font-bold">Bill of Materials for</h1>
          </div>

          {/* Selected Product Info */}
          <div className="border rounded-lg p-4 bg-muted/30">
            <div className="flex items-start justify-between gap-3">
              <div>
                <h3 className="font-semibold">{selectedProduct.product.name}</h3>
                <p className="text-sm text-muted-foreground font-mono">
                  {selectedProduct.product.code}
                </p>
              </div>
              <Badge variant={selectedProduct.isTemplate ? "default" : "secondary"}>
                {selectedProduct.isTemplate ? "Template" : "Variant"}
              </Badge>
            </div>
          </div>

          {/* Version Selection */}
          <div className="border rounded-lg p-6 space-y-6 bg-card">
            <VersionSelectionPanel
              productId={selectedProduct.product.id}
              isTemplate={selectedProduct.isTemplate}
              onCreateNew={() => createBOMMutation.mutate()}
              onOpenExisting={(selected) => navigate(`/bom/${selected.id}`)}
              isCreatingNew={createBOMMutation.isPending}
            />
          </div>
        </div>
      )
    }

    // Fallback: If none of the steps matched, go back to step 1
    return (
      <div className="w-full max-w-2xl">
        <div className="mb-6">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => navigate("/bom/list")}
            className="-ml-2 mb-4"
          >
            <ArrowLeft className="w-4 h-4 mr-1" />
            Back
          </Button>
        </div>
        <div className="border rounded-lg p-6 space-y-6 bg-card">
          <h2 className="text-2xl font-bold mb-4">Create New Bill of Materials</h2>
          <ProductSelectionModal
            onSelect={(product, isTemplate) => {
              setSelectedProduct({ product, isTemplate })
              setCreationStep("select-version")
            }}
            onCancel={() => navigate("/bom/list")}
          />
        </div>
      </div>
    )
  }

  // ─── EXISTING BOM DETAIL VIEW ────────────────────────────────────────────────

  if (isLoading) {
    return (
      <div className="w-full space-y-6">
        <div className="flex items-center gap-3">
          <Skeleton className="h-9 w-9 rounded-md" />
          <Skeleton className="h-8 w-48" />
          <Skeleton className="h-6 w-20" />
        </div>
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
          <Skeleton className="h-64 rounded-xl" />
          <Skeleton className="col-span-3 h-96 rounded-xl" />
        </div>
      </div>
    )
  }

  if ((isError || !bom) && !isNewBOM) {
    return (
      <div className="p-8 flex flex-col items-center gap-4">
        <Alert variant="destructive" className="max-w-md">
          <AlertCircle className="w-4 h-4" />
          <AlertDescription>
            {(error as any)?.response?.data?.detail || "BOM not found."}
          </AlertDescription>
        </Alert>
        <div className="flex gap-2">
          <Button variant="outline" onClick={() => refetch()}>
            Retry
          </Button>
          <Button variant="outline" onClick={() => navigate("/bom/list")}>
            <ArrowLeft className="w-4 h-4 mr-2" />
            Back to BOM List
          </Button>
        </div>
      </div>
    )
  }

  // Ensure bom is defined for existing BOM detail view
  if (!bom) {
    return null
  }

  const onActivated = (updated: BOM) => {
    qc.setQueryData(["bom", bomId], updated)
    qc.invalidateQueries({ queryKey: ["bom-versions"] })
    toast.success(`BOM v${updated.version} activated`)
  }

  const onCopied = (newBom: BOM) => {
    qc.invalidateQueries({ queryKey: ["bom-versions"] })
    navigate(`/bom/${newBom.id}`)
  }

  return (
    <div className="w-full space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-start gap-4">
        {targetQuery.data?.variant ? (
          <Button
            variant="ghost"
            size="sm"
            onClick={() => navigate(`/products/templates/${targetQuery.data!.template.id}?tab=variants`)}
            className="-ml-2 self-start"
          >
            <ArrowLeft className="w-4 h-4 mr-1" />
            Back to Variant
          </Button>
        ) : (
          <Button
            variant="ghost"
            size="sm"
            onClick={() => navigate("/bom/list")}
            className="-ml-2 self-start"
          >
            <ArrowLeft className="w-4 h-4 mr-1" />
            BOMs
          </Button>
        )}
        <Separator orientation="vertical" className="h-10 hidden sm:block" />
        <div className="flex flex-col flex-1 min-w-0">
          <div className="flex items-center gap-3 flex-wrap">
            <h1 className="text-xl font-semibold truncate">
              BOM v{bom.version}
            </h1>
            <Badge
              className={
                bom.is_active
                  ? "bg-green-50 text-green-700 border-green-200"
                  : "text-muted-foreground border"
              }
            >
              {bom.is_active ? (
                <>
                  <Zap className="w-3 h-3 mr-1" />
                  Active
                </>
              ) : (
                "Draft"
              )}
            </Badge>
            {!canEditBOM() && (
              <Badge variant="outline" className="text-muted-foreground text-xs">
                <Lock className="w-3 h-3 mr-1" />
                Read-only
              </Badge>
            )}
          </div>
          {targetQuery.data && (
            <div className="text-sm mt-1.5 flex flex-wrap gap-x-4 gap-y-1">
              <span>
                Finished Product: <strong className="text-foreground">
                  {targetQuery.data.isTemplate 
                    ? targetQuery.data.template.name 
                    : `${targetQuery.data.template.name} - ${targetQuery.data.variant?.name}`}
                </strong>
              </span>
              {!targetQuery.data.isTemplate && (
                <>
                  <span className="text-muted-foreground hidden sm:inline">|</span>
                  <span className="text-muted-foreground">
                    Product: <strong className="text-foreground font-medium">{targetQuery.data.template.name}</strong>
                  </span>
                  <span className="text-muted-foreground hidden sm:inline">|</span>
                  <span className="text-muted-foreground">
                    Variant: <strong className="text-foreground font-medium">{targetQuery.data.variant?.name}</strong>
                  </span>
                </>
              )}
            </div>
          )}
        </div>

        {/* Action buttons */}
        {canEditBOM() && (
          <div className="flex gap-2 flex-shrink-0">
            {!bom.is_active && (
              <>
                <Button
                  size="sm"
                  onClick={() => setActivateOpen(true)}
                  className="bg-green-600 hover:bg-green-700"
                >
                  <Zap className="w-3.5 h-3.5 mr-1.5" />
                  Activate
                </Button>
                <Dialog>
                  <DialogTrigger asChild>
                    <Button size="sm" variant="destructive" className="bg-red-600 hover:bg-red-700/90 text-white border-transparent">
                      <Trash2 className="w-3.5 h-3.5 mr-1.5" />
                      Delete
                    </Button>
                  </DialogTrigger>
                  <DialogContent>
                    <DialogHeader>
                      <DialogTitle>Are you sure you want to delete this draft BOM?</DialogTitle>
                      <DialogDescription>
                        This will permanently delete the draft BOM version {bom.version}. This action cannot be undone.
                      </DialogDescription>
                    </DialogHeader>
                    <DialogFooter>
                      <Button variant="outline" className="mt-2 sm:mt-0" onClick={() => document.dispatchEvent(new KeyboardEvent('keydown', {'key': 'Escape'}))}>Cancel</Button>
                      <Button
                        variant="destructive"
                        className="bg-red-600 hover:bg-red-700"
                        onClick={async () => {
                          try {
                            await bomService.deleteBOM(bom.id);
                            // Close dialog manually if needed, or redirect
                            toast.success(`Draft BOM v${bom.version} deleted`)
                            navigate("/bom/list")
                          } catch (err: any) {
                            toast.error(err?.response?.data?.detail || "Failed to delete BOM")
                          }
                        }}
                      >
                        Delete
                      </Button>
                    </DialogFooter>
                  </DialogContent>
                </Dialog>
              </>
            )}
            <Button
              size="sm"
              variant="outline"
              onClick={() => setCopyOpen(true)}
            >
              <GitBranch className="w-3.5 h-3.5 mr-1.5" />
              Copy
            </Button>
          </div>
        )}
      </div>

      {/* Meta info row */}
      <div className="flex flex-wrap gap-x-4 gap-y-1 text-sm text-muted-foreground">
        {bom.valid_from && (
          <span>
            Valid from: <strong className="text-foreground">
              {new Date(bom.valid_from).toLocaleDateString()}
            </strong>
          </span>
        )}
        {bom.valid_to && (
          <span>
            to <strong className="text-foreground">
              {new Date(bom.valid_to).toLocaleDateString()}
            </strong>
          </span>
        )}
        <span>
          Components: <strong className="text-foreground">{bom.lines.length}</strong>
        </span>
      </div>

      {/* Main two-column layout */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6 items-start">
        {/* Left: Version panel */}
        {productId && (
          <div className="lg:col-span-1">
            <div className="rounded-xl border bg-card p-4">
              <BOMVersionPanel
                productId={productId}
                isTemplate={isTemplateType}
                productName={targetQuery.data ? targetQuery.data.product.name : `Product ${productId.slice(0, 8)}`}
                productCode={targetQuery.data ? targetQuery.data.product.code : productId.slice(0, 8)}
                selectedBomId={bom.id}
                activeBomId={bom.is_active ? bom.id : undefined}
                onSelectBom={(b) => navigate(`/bom/${b.id}`)}
              />
            </div>
          </div>
        )}

        {/* Right: Tabs */}
        <div className={productId ? "lg:col-span-3" : "lg:col-span-4"}>
          <Tabs value={activeTab} onValueChange={setActiveTab}>
            <TabsList className="w-full sm:w-auto">
              <TabsTrigger value="builder">
                <Package2 className="w-3.5 h-3.5 mr-1.5" />
                Components Builder
              </TabsTrigger>
              <TabsTrigger value="tree">
                <GitBranch className="w-3.5 h-3.5 mr-1.5" />
                Multi-level Tree
              </TabsTrigger>
              <TabsTrigger value="operations">Operations</TabsTrigger>
              <TabsTrigger value="cost">Cost Breakdown</TabsTrigger>
            </TabsList>

            {/* Components Builder tab */}
            <TabsContent value="builder" className="mt-4">
              <div className="rounded-xl border bg-card p-4">
                <BOMLineList bom={bom} canEdit={canEditBOM() && !bom.is_active} />
              </div>
            </TabsContent>

            {/* BOM Tree tab */}
            <TabsContent value="tree" className="mt-4">
              <div className="rounded-xl border bg-card p-4">
                {bom.lines.length === 0 ? (
                  <div className="flex flex-col items-center justify-center py-12 gap-3 text-muted-foreground">
                    <Package2 className="w-10 h-10" />
                    <p className="text-sm">This BOM has no components yet.</p>
                  </div>
                ) : (
                  <BOMTreeView bomId={bom.id} />
                )}
              </div>
            </TabsContent>

            {/* Operations tab */}
            <TabsContent value="operations" className="mt-4">
              <div className="rounded-xl border bg-card p-4">
                <BOMOperationList bom={bom} canEdit={canEditBOM() && !bom.is_active} />
              </div>
            </TabsContent>

            {/* Cost tab */}
            <TabsContent value="cost" className="mt-4">
              <div className="rounded-xl border bg-card p-4">
                <BOMCostBreakdown bom={bom} />
              </div>
            </TabsContent>
          </Tabs>
        </div>
      </div>

      {/* Dialogs */}
      <BOMActivateDialog
        open={activateOpen}
        bom={bom}
        onClose={() => setActivateOpen(false)}
        onActivated={onActivated}
      />
      <BOMCopyDialog
        open={copyOpen}
        bom={bom}
        productId={productId ?? ""}
        onClose={() => setCopyOpen(false)}
        onCopied={onCopied}
      />
    </div>
  )
}
