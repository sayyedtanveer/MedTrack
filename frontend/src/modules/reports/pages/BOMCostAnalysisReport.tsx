import { toast } from "sonner"
import { useMemo, useState } from "react"
import { useQuery } from "@tanstack/react-query"
import type { ColumnDef } from "@tanstack/react-table"
import { Link } from "react-router-dom"
import { apiClient } from "@/services/api-client"
import { bomService } from "@/services/bom.service"
import { productService } from "@/services/product.service"
import { usePermissions } from "@/hooks/usePermissions"
import { DataTable } from "@/components/shared/DataTable"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"

interface OperationRow {
  operation_id: string
  name: string
  code: string | null
  cost: string | null
}
interface CostNode {
  id: string
  bom_id?: string
  name: string
  type: string
  version?: string
  quantity: string
  unit?: string | null
  unit_cost?: string | null
  cost: string | null
  cost_basis?: string
  stored_standard_cost?: string | null
  making_cost?: string
  children: CostNode[]
  operations?: OperationRow[]
}

interface CostAnalysis {
  bom_id: string
  version: string
  is_active: boolean
  target_name: string | null
  output_quantity: number
  output_uom: string | null
  generated_at: string
  currency_code: string | null
  total_cost: string | null
  direct_material_cost: string | null
  nested_cost: string | null
  own_operation_cost: string
  own_outside_processing_cost: string
  is_complete: boolean
  composition: { material: string; operations: string; outside_processing: string } | null
  missing_costs: { component_id: string; code?: string; name?: string; message: string }[]
  tree: CostNode
}

function costLabel(value: string | null | undefined, currency?: string | null) {
  return value == null ? "—" : [currency, value.replace(/(\.\d*?[1-9])0+$|\.0+$/, "$1")].filter(Boolean).join(" ")
}

function CostBranch({ node, currency }: { node: CostNode; currency?: string | null }) {
  const label = <>{node.name}{node.version ? ` · BOM ${node.version}` : ""} · {node.quantity} {node.unit} · {costLabel(node.cost, currency)}</>
  if (!node.children.length && !node.operations?.length) return <li className="py-1">{label}</li>
  return <li className="py-1">
    <details>
      <summary className="cursor-pointer font-medium">{label}</summary>
      <div className="ml-3 space-y-1 border-l pl-3">
        {node.stored_standard_cost != null && <p>Stored material Standard Cost per unit {costLabel(node.stored_standard_cost, currency)}</p>}
        {Number(node.making_cost) > 0 && <p>Estimated BOM outside processing {costLabel(node.making_cost, currency)}</p>}
        {node.operations?.map((op, index) => <p key={`${op.operation_id}-${index}`}>Operation · {op.name} · {costLabel(op.cost, currency)}</p>)}
        <ul>{node.children.map((child, index) => <CostBranch key={`${child.id}-${index}`} node={child} currency={currency} />)}</ul>
      </div>
    </details>
  </li>
}

function flattenNodes(node: CostNode): CostNode[] {
  return node.children.flatMap((child) => [child, ...flattenNodes(child)])
}

export function BOMCostAnalysisReport() {
  const [search, setSearch] = useState("")
  const [productId, setProductId] = useState("")
  const [variantId, setVariantId] = useState("")
  const [bomId, setBomId] = useState("")
  const [productPage, setProductPage] = useState(1)
  const [variantPage, setVariantPage] = useState(1)
  const [bomPage, setBomPage] = useState(1)
  const [exporting, setExporting] = useState(false)
  const { hasPermission } = usePermissions()
  const canViewMaterials = hasPermission("inventory:read")
  const products = useQuery({
    queryKey: ["bom-report-products", search, productPage],
    queryFn: () => productService.getTemplates({ query: search || undefined, page: productPage, page_size: 50 }),
  })
  const variants = useQuery({
    queryKey: ["bom-report-variants", productId, variantPage],
    queryFn: () => productService.getVariants(productId, { page: variantPage, page_size: 50 }),
    enabled: Boolean(productId),
  })
  const versions = useQuery({
    queryKey: ["bom-report-versions", productId, variantId, bomPage],
    queryFn: () => bomService.getBOMsForProduct(variantId || productId, !variantId, { page: bomPage, page_size: 50 }),
    enabled: Boolean(productId),
  })
  const report = useQuery({
    queryKey: ["bom-report", bomId],
    queryFn: async () => (await apiClient.get<CostAnalysis>(`/reports/bom-cost/${bomId}`)).data,
    enabled: Boolean(bomId),
  })
  const data = report.data
  const currency = data?.currency_code
  const rows = useMemo(() => data ? flattenNodes(data.tree) : [], [data])
  const columns: ColumnDef<CostNode>[] = [
    { accessorKey: "name", header: ({ column }) => <Button variant="ghost" onClick={() => column.toggleSorting()}>Component ↕</Button>, cell: ({ row }) => {
      const item = row.original
      const href = item.bom_id ? `/bom/${item.bom_id}` : item.type === "material" && canViewMaterials ? `/inventory/materials?materialId=${item.id}` : null
      return href ? <Link className="text-primary underline" to={href}>{item.name}</Link> : item.name
    } },
    { accessorKey: "quantity", header: "Quantity" },
    { accessorKey: "unit", header: "UOM" },
    { accessorKey: "unit_cost", header: "Unit Cost", cell: ({ row }) => costLabel(row.original.unit_cost, currency) },
    { accessorKey: "cost", header: "Extended Cost", cell: ({ row }) => costLabel(row.original.cost, currency) },
  ]
  async function download() {
    setExporting(true)
    try {
      const { data: workbook } = await apiClient.get<Blob>(`/reports/bom-cost/${bomId}/export/xlsx`, { responseType: "blob" })
      const url = URL.createObjectURL(workbook)
      const anchor = document.createElement("a")
      anchor.href = url
      anchor.download = `bom-cost-${bomId}.xlsx`
      document.body.append(anchor)
      anchor.click()
      anchor.remove()
      setTimeout(() => URL.revokeObjectURL(url), 0)
    } catch {
      toast.error("Could not export this BOM. Check your access and the report size.")
    } finally {
      setExporting(false)
    }
  }
  const total = Number(data?.total_cost)
  return <section className="space-y-5">
    <header>
      <h2 className="text-xl font-semibold">BOM Cost Analysis</h2>
      <p className="text-sm text-muted-foreground">Current calculated cost per output unit, by BOM version.</p>
    </header>
    <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
      <label className="space-y-1 text-sm">Search products<Input value={search} onChange={(event) => { setSearch(event.target.value); setProductPage(1) }} /></label>
      <label className="space-y-1 text-sm">Product
        <select className="block w-full rounded-md border bg-background p-2" value={productId} onChange={(event) => { setProductId(event.target.value); setVariantId(""); setBomId(""); setVariantPage(1); setBomPage(1) }}>
          <option value="">Select product</option>
          {products.data?.items.map((item) => <option key={item.id} value={item.id}>{item.code} · {item.name}</option>)}
        </select>
        <PageControls page={productPage} total={products.data?.total} setPage={setProductPage} />
      </label>
      <label className="space-y-1 text-sm">Variant
        <select className="block w-full rounded-md border bg-background p-2" value={variantId} disabled={!productId} onChange={(event) => { setVariantId(event.target.value); setBomId(""); setBomPage(1) }}>
          <option value="">Product template</option>
          {variants.data?.items.map((item) => <option key={item.id} value={item.id}>{item.code} · {item.name}</option>)}
        </select>
        <PageControls page={variantPage} total={variants.data?.total} setPage={setVariantPage} />
      </label>
      <label className="space-y-1 text-sm">BOM version
        <select className="block w-full rounded-md border bg-background p-2" value={bomId} disabled={!productId} onChange={(event) => setBomId(event.target.value)}>
          <option value="">Select version</option>
          {versions.data?.items.map((item) => <option key={item.id} value={item.id}>{item.version} · {item.is_active ? "Active" : "Draft / inactive"}</option>)}
        </select>
        <PageControls page={bomPage} total={versions.data?.total} setPage={setBomPage} />
      </label>
    </div>
    {(products.isLoading || variants.isLoading || versions.isLoading || report.isLoading) && <p role="status">Loading report data…</p>}
    {(products.isError || variants.isError || versions.isError || report.isError) && <p role="alert" className="text-destructive">The report data could not be loaded. Check access and retry.</p>}
    {productId && versions.data?.total === 0 && <p>No BOM versions exist for this selection.</p>}
    {data && <>
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="text-sm">{data.target_name} · {data.version} · {data.is_active ? "Active" : "Draft / inactive"} · {data.output_quantity} {data.output_uom ?? "UOM missing"} · Calculated {new Date(data.generated_at).toLocaleString()}</p>
        <div className="flex flex-wrap items-center gap-3">
          <Link className="text-primary underline" to={`/bom/${data.bom_id}`}>Open BOM</Link>
          <Button variant="outline" disabled={exporting} onClick={download}>{exporting ? "Exporting…" : "Export Excel"}</Button>
        </div>
      </div>
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-5">
        {[
          ["Calculated BOM Cost", data.total_cost],
          ["Direct Materials", data.direct_material_cost],
          ["Nested BOM Contribution", data.nested_cost],
          ["Own Operations", data.own_operation_cost],
          ["Own Outside Processing (estimate)", data.own_outside_processing_cost],
        ].map(([label, value]) => <Card key={label}><CardHeader className="p-4 pb-2"><CardTitle className="text-sm">{label}</CardTitle></CardHeader><CardContent className="p-4 pt-0 text-lg font-semibold">{value == null ? "Incomplete" : costLabel(value, currency)}</CardContent></Card>)}
      </div>
      {!data.is_complete && <div role="alert" className="rounded-lg border border-amber-500 p-4">
        <h3 className="font-semibold">Incomplete cost</h3>
        <ul className="list-disc pl-5">{data.missing_costs.map((issue, index) => <li key={`${issue.component_id}-${index}`}>{issue.code ?? issue.name ?? "BOM"} · {issue.message}</li>)}</ul>
      </div>}
      {data.composition && <Card><CardHeader><CardTitle className="text-base">Reconciled Cost Composition</CardTitle></CardHeader><CardContent className="space-y-3">
        {([
          ["Raw materials", data.composition.material, "bg-primary"],
          ["Operations", data.composition.operations, "bg-teal-600"],
          ["Outside processing (estimated BOM cost)", data.composition.outside_processing, "bg-amber-600"],
        ] as const).map(([label, value, color]) => <div key={label}>
          <div className="flex justify-between gap-3 text-sm"><span>{label}</span><span>{costLabel(value, currency)}</span></div>
          {total > 0 && <div aria-hidden="true" className="h-2 rounded bg-muted"><div className={`h-full rounded ${color}`} style={{ width: `${Math.min(100, Math.max(0, Number(value) / total * 100))}%` }} /></div>}
        </div>)}
      </CardContent></Card>}
      <Card><CardHeader><CardTitle className="text-base">BOM Hierarchy</CardTitle></CardHeader><CardContent className="text-sm"><ul><CostBranch node={data.tree} currency={currency} /></ul></CardContent></Card>
      {rows.length > 0 && <Card><CardHeader><CardTitle className="text-base">Component Details</CardTitle></CardHeader><CardContent className="overflow-x-auto"><DataTable columns={columns} data={rows} searchKey="name" /></CardContent></Card>}
    </>}
  </section>
}

function PageControls({ page, total, setPage }: { page: number; total?: number; setPage: (page: number) => void }) {
  if (!total || total <= 50) return null
  return <span className="flex items-center gap-2">
    <Button type="button" size="sm" variant="ghost" disabled={page === 1} onClick={() => setPage(page - 1)}>Previous</Button>
    <span>{page}</span>
    <Button type="button" size="sm" variant="ghost" disabled={page * 50 >= total} onClick={() => setPage(page + 1)}>Next</Button>
  </span>
}
