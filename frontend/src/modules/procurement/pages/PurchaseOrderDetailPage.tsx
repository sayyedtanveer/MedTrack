import { useEffect, useState } from "react"
import { Link, useParams } from "react-router-dom"
import { supplyChainApi, type PurchaseOrder } from "@/services/supply-chain.service"
import { materialService } from "@/services/material.service"
import { documentService } from "@/services/document.service"
import type { Material } from "@/types/material.types"
import { Button } from "@/components/ui/button"
import { AssistantButton } from "@/components/shared/assistant/AssistantButton"
import { AssistantEngine } from "@/lib/assistant/AssistantEngine"
import { MedTrackAssistant } from "@/components/shared/assistant/MedTrackAssistant"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { useToast } from "@/hooks/use-toast"

export default function PurchaseOrderDetailPage() {
  const { poId } = useParams<{ poId: string }>()
  const { toast } = useToast()
  const [po, setPo] = useState<PurchaseOrder | null>(null)
  const [matMap, setMatMap] = useState<Record<string, string>>({})
  const [documentLoading, setDocumentLoading] = useState(false)

  const load = async () => {
    if (!poId) return
    const { data } = await supplyChainApi.getPurchaseOrder(poId)
    setPo(data)
    const mats = await materialService.getMaterials({ page: 1, page_size: 500 })
    const map: Record<string, string> = {}
    mats.items.forEach((m: Material) => {
      map[m.id] = `${m.code} (${m.name})`
    })
    setMatMap(map)
  }

  useEffect(() => {
    load().catch(() => toast({ title: "Failed to load PO", variant: "destructive" }))
  }, [poId, toast])

  const send = async () => {
    if (!poId) return
    try {
      await supplyChainApi.sendPO(poId)
      toast({ title: "PO sent to supplier" })
      await load()
    } catch {
      toast({ title: "Send failed", variant: "destructive" })
    }
  }

  const acknowledge = async () => {
    if (!poId) return
    try {
      await supplyChainApi.acknowledgePO(poId)
      toast({ title: "PO acknowledged" })
      await load()
    } catch {
      toast({ title: "Acknowledge failed", variant: "destructive" })
    }
  }

  const handleDownloadPDF = async () => {
    if (!poId || documentLoading) return
    setDocumentLoading(true)
    try {
      const document = await documentService.generateDocument('purchase_order', poId)
      await documentService.downloadDocumentByUrl(document.id, `PO-${po?.po_number}.pdf`)
    } catch (e: any) {
      toast({ title: "Failed to generate PDF", variant: "destructive" })
    } finally {
      setDocumentLoading(false)
    }
  }

  const handlePrintPDF = async () => {
    if (!poId || documentLoading) return
    setDocumentLoading(true)
    try {
      const document = await documentService.generateDocument('purchase_order', poId)
      const previewUrl = await documentService.previewDocument(document.id)
      const printWindow = window.open(previewUrl, '_blank')
      if (printWindow) {
        printWindow.onload = () => {
          printWindow.print()
        }
      }
    } catch (e: any) {
      toast({ title: "Failed to generate PDF for printing", variant: "destructive" })
    } finally {
      setDocumentLoading(false)
    }
  }

  if (!po) return <p className="text-muted-foreground">Loading…</p>

  const canSend = po.status === "draft"
  const canAck = ["sent", "partial"].includes(po.status)
  const canReceive = ["sent", "acknowledged", "partial"].includes(po.status)

  return (
    <div className="space-y-6 max-w-4xl">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <Button variant="ghost" size="sm" asChild className="mb-2 -ml-2">
            <Link to="/procurement/purchase-orders">← Back to list</Link>
          </Button>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold tracking-tight">Purchase Order {po.po_number}</h1>
            <span className="inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold bg-gray-100 text-gray-800 uppercase tracking-wide">
              {po.status}
            </span>
          </div>
        </div>
      </div>

      {(() => {
        const guidance = AssistantEngine.getGuidance(po);
        return guidance ? <MedTrackAssistant guidance={guidance} /> : null;
      })()}

      <div className="flex items-center justify-between bg-gray-50 p-4 rounded-lg border">
        <div>
          <h1 className="text-2xl font-semibold font-mono">{po.po_number}</h1>
          <p className="text-sm text-muted-foreground">
            Status: <strong>{po.status}</strong> · Ordered {po.order_date}
          </p>
          {po.notes && <p className="text-sm mt-1">{po.notes}</p>}
        </div>
        <div className="flex flex-wrap gap-2">
          <Button
            variant="outline"
            onClick={handlePrintPDF}
            disabled={documentLoading}
          >
            {documentLoading ? '…' : 'Print'}
          </Button>
          <Button
            variant="outline"
            onClick={handleDownloadPDF}
            disabled={documentLoading}
          >
            {documentLoading ? '…' : 'Download PDF'}
          </Button>
          {canSend && (
            <AssistantButton onClick={send} pulse={AssistantEngine.getGuidance(po)?.pulseActionId === 'send'}>
              Send to Supplier
            </AssistantButton>
          )}
          {canAck && (
            <AssistantButton variant="secondary" onClick={acknowledge} pulse={AssistantEngine.getGuidance(po)?.pulseActionId === 'acknowledge'}>
              Mark Acknowledged
            </AssistantButton>
          )}
          {canReceive && (
            <AssistantButton variant="outline" asChild id="receive_goods" pulse={AssistantEngine.getGuidance(po)?.pulseActionId === 'receive_goods'}>
              <Link to={`/procurement/grn?poId=${po.id}`}>Goods receipt (GRN)</Link>
            </AssistantButton>
          )}
        </div>
      </div>

      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Material</TableHead>
            <TableHead className="text-right">Ordered</TableHead>
            <TableHead className="text-right">Received</TableHead>
            <TableHead className="text-right">Unit price</TableHead>
            <TableHead className="text-right">Line total</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {po.lines.map((l) => (
            <TableRow key={l.id}>
              <TableCell>{matMap[l.material_id] || l.material_id}</TableCell>
              <TableCell className="text-right tabular-nums">{l.quantity}</TableCell>
              <TableCell className="text-right tabular-nums">{l.received_quantity}</TableCell>
              <TableCell className="text-right tabular-nums">
                {new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR' }).format(l.unit_price)}
              </TableCell>
              <TableCell className="text-right tabular-nums">
                {new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR' }).format(l.line_total ?? l.quantity * l.unit_price)}
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  )
}
