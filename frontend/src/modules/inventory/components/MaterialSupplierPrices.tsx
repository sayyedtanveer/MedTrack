import { useQuery } from "@tanstack/react-query"
import { materialService } from "@/services/material.service"
import { supplyChainApi } from "@/services/supply-chain.service"
import { supplierPriceAgreementApi } from "@/modules/procurement/services/supplierPriceAgreementApi"

export function MaterialSupplierPrices({ materialId }: { materialId: string }) {
  const prices = useQuery({
    queryKey: ["material-supplier-prices", materialId],
    queryFn: async () => {
      const first = await supplierPriceAgreementApi.list({ material_id: materialId, page_size: 100 })
      const items = [...first.items]
      for (let page = 2; page <= Math.ceil(first.total / first.page_size); page += 1) {
        const next = await supplierPriceAgreementApi.list({ material_id: materialId, page, page_size: 100 })
        items.push(...next.items)
      }
      return items
    },
    enabled: Boolean(materialId),
  })
  const suppliers = useQuery({
    queryKey: ["suppliers"],
    queryFn: async () => (await supplyChainApi.listSuppliers()).data,
  })
  const units = useQuery({ queryKey: ["units"], queryFn: materialService.getUnits })
  const date = (value: string | null) => value ? new Date(value).toLocaleDateString("en-IN") : "Ongoing"
  const number = (value: number | string) => {
    const parsed = Number(value)
    return Number.isFinite(parsed)
      ? parsed.toLocaleString("en-IN", { maximumFractionDigits: 6 }) : "Unavailable"
  }

  return (
    <section aria-label="Supplier Prices" className="space-y-2">
      <p className="text-sm font-medium">Supplier Prices</p>
      <p className="text-xs text-muted-foreground">Supplier quotes are separate from standard cost and actual purchases. DRAFT quotes are not active purchasing agreements.</p>
      {prices.isLoading || suppliers.isLoading || units.isLoading ? (
        <p className="text-sm text-muted-foreground">Loading supplier prices…</p>
      ) : prices.isError ? (
        <p role="alert" className="text-sm text-destructive">Unable to load supplier prices or supplier/UOM details. Check your pricing access and try again.</p>
      ) : !prices.data?.length ? (
        <p className="text-sm text-muted-foreground">No supplier prices yet.</p>
      ) : (
        <div className="overflow-x-auto rounded-md border">
          {(suppliers.isError || units.isError) && <p className="p-2 text-xs text-amber-700">Some supplier or UOM details could not be loaded. Prices below retain their original identifiers.</p>}
          <table className="w-full text-sm">
            <thead><tr className="border-b bg-muted/30">
              {["Supplier", "Price", "UOM", "MOQ", "Effective dates", "Status"].map(label => (
                <th key={label} className="p-2 text-left font-medium">{label}</th>
              ))}
            </tr></thead>
            <tbody>{prices.data.map(agreement => {
              const supplier = suppliers.data?.find(item => item.id === agreement.supplier_id)
              const unit = units.data?.find(item => item.id === agreement.purchase_uom_id)
              return <tr key={agreement.id} className="border-b last:border-0 align-top">
                <td className="p-2">{supplier?.name ?? "Supplier unavailable"}<span className="block text-xs text-muted-foreground">{supplier?.code ?? agreement.supplier_id}</span></td>
                <td className="p-2 whitespace-nowrap">{agreement.currency_code} {number(agreement.base_price)}</td>
                <td className="p-2">{unit?.code ?? agreement.purchase_uom_id ?? "Unspecified"}</td>
                <td className="p-2">{agreement.minimum_order_quantity == null ? "—" : number(agreement.minimum_order_quantity)}</td>
                <td className="p-2 text-xs">{date(agreement.effective_from)} – {date(agreement.effective_to)}</td>
                <td className="p-2"><span className="rounded border px-1.5 py-0.5 text-xs font-medium">{agreement.status}</span></td>
              </tr>
            })}</tbody>
          </table>
        </div>
      )}
    </section>
  )
}
