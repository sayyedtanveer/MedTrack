// QC Dashboard Page
import { useState } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card"
import { Table, TableHeader, TableRow, TableHead, TableBody, TableCell } from "@/components/ui/table"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Textarea } from "@/components/ui/textarea"
import { Label } from "@/components/ui/label"
import { CheckCircle, XCircle, RefreshCw, ClipboardCheck, AlertTriangle, Loader2 } from "lucide-react"
import { toast } from "sonner"
import axios from "axios"

// ── API calls ─────────────────────────────────────────────────────────────────

async function approveQC(workOrderId: string, remarks?: string) {
  const { data } = await axios.post("/api/v1/quality-control/approve", {
    work_order_id: workOrderId,
    remarks: remarks || null,
  })
  return data
}

async function rejectQC(workOrderId: string, reason: string) {
  const { data } = await axios.post("/api/v1/quality-control/reject", {
    work_order_id: workOrderId,
    reason,
  })
  return data
}

async function sendToRework(workOrderId: string, reworkReason: string) {
  const { data } = await axios.post("/api/v1/quality-control/send-to-rework", {
    work_order_id: workOrderId,
    rework_reason: reworkReason,
  })
  return data
}

async function scrapBatch(workOrderId: string, scrapReason: string) {
  const { data } = await axios.post("/api/v1/quality-control/scrap", {
    work_order_id: workOrderId,
    scrap_reason: scrapReason,
  })
  return data
}

// ── Types ─────────────────────────────────────────────────────────────────────

type WOQueueItem = {
  work_order_id: string
  wo_number: string
  product_id: string
  produced_quantity: number
  scrap_quantity?: number
  due_date?: string
  priority?: string
  status: string
}

type DialogMode = "approve" | "reject" | "rework" | "scrap" | null

export default function QCDashboardPage() {
  const qc = useQueryClient()
  const [activeWO, setActiveWO] = useState<WOQueueItem | null>(null)
  const [dialogMode, setDialogMode] = useState<DialogMode>(null)
  const [remarks, setRemarks] = useState("")

  // ── Queries ──────────────────────────────────────────────────────────────────

  const { data: inspectionQueue, isLoading: inspectionLoading } = useQuery<WOQueueItem[]>({
    queryKey: ["qc-inspection-queue"],
    queryFn: async () => {
      const response = await axios.get("/api/v1/work-orders/qc/inspection-queue")
      return response.data
    },
  })

  const { data: rejectedQueue, isLoading: rejectedLoading } = useQuery<WOQueueItem[]>({
    queryKey: ["qc-rejected-queue"],
    queryFn: async () => {
      const response = await axios.get("/api/v1/work-orders/qc/rejected-queue")
      return response.data
    },
  })

  const { data: reworkQueue, isLoading: reworkLoading } = useQuery<WOQueueItem[]>({
    queryKey: ["qc-rework-queue"],
    queryFn: async () => {
      const response = await axios.get("/api/v1/work-orders/qc/rework-queue")
      return response.data
    },
  })

  // ── Mutations ─────────────────────────────────────────────────────────────────

  const invalidateQueues = () => {
    qc.invalidateQueries({ queryKey: ["qc-inspection-queue"] })
    qc.invalidateQueries({ queryKey: ["qc-rejected-queue"] })
    qc.invalidateQueries({ queryKey: ["qc-rework-queue"] })
  }

  const approveMutation = useMutation({
    mutationFn: () => approveQC(activeWO!.work_order_id, remarks || undefined),
    onSuccess: () => {
      toast.success(`WO ${activeWO?.wo_number} approved — FG receipt triggered`)
      invalidateQueues()
      closeDialog()
    },
    onError: (err: any) => {
      toast.error(err?.response?.data?.detail || "Failed to approve QC")
    },
  })

  const rejectMutation = useMutation({
    mutationFn: () => rejectQC(activeWO!.work_order_id, remarks),
    onSuccess: () => {
      toast.success(`WO ${activeWO?.wo_number} rejected`)
      invalidateQueues()
      closeDialog()
    },
    onError: (err: any) => {
      toast.error(err?.response?.data?.detail || "Failed to reject QC")
    },
  })

  const reworkMutation = useMutation({
    mutationFn: () => sendToRework(activeWO!.work_order_id, remarks),
    onSuccess: () => {
      toast.success(`WO ${activeWO?.wo_number} sent to rework`)
      invalidateQueues()
      closeDialog()
    },
    onError: (err: any) => {
      toast.error(err?.response?.data?.detail || "Failed to send to rework")
    },
  })

  const scrapMutation = useMutation({
    mutationFn: () => scrapBatch(activeWO!.work_order_id, remarks),
    onSuccess: () => {
      toast.success(`WO ${activeWO?.wo_number} scrapped`)
      invalidateQueues()
      closeDialog()
    },
    onError: (err: any) => {
      toast.error(err?.response?.data?.detail || "Failed to scrap batch")
    },
  })

  // ── Dialog helpers ────────────────────────────────────────────────────────────

  const openDialog = (wo: WOQueueItem, mode: DialogMode) => {
    setActiveWO(wo)
    setDialogMode(mode)
    setRemarks("")
  }

  const closeDialog = () => {
    setActiveWO(null)
    setDialogMode(null)
    setRemarks("")
  }

  const handleConfirm = () => {
    if (!activeWO) return
    if (dialogMode === "approve") approveMutation.mutate()
    else if (dialogMode === "reject") rejectMutation.mutate()
    else if (dialogMode === "rework") reworkMutation.mutate()
    else if (dialogMode === "scrap") scrapMutation.mutate()
  }

  const isMutating =
    approveMutation.isPending ||
    rejectMutation.isPending ||
    reworkMutation.isPending ||
    scrapMutation.isPending

  const requiresReason = dialogMode === "reject" || dialogMode === "rework" || dialogMode === "scrap"
  const canConfirm = !requiresReason || remarks.trim().length > 0

  // ── Dialog config ─────────────────────────────────────────────────────────────

  const dialogConfig = {
    approve: {
      title: "Approve QC Inspection",
      description: "This will approve the batch, increase FG inventory, and update the linked sales order allocation.",
      label: "Remarks (optional)",
      placeholder: "Any notes about the inspection...",
      confirmLabel: "Approve",
      confirmClass: "bg-green-600 hover:bg-green-700",
    },
    reject: {
      title: "Reject QC Inspection",
      description: "This will reject the batch. You can then choose to send it to rework or scrap.",
      label: "Rejection reason (required)",
      placeholder: "Describe the defects found...",
      confirmLabel: "Reject",
      confirmClass: "bg-red-600 hover:bg-red-700",
    },
    rework: {
      title: "Send to Rework",
      description: "The work order will be sent back to the production queue for rework.",
      label: "Rework reason (required)",
      placeholder: "Describe what needs to be reworked...",
      confirmLabel: "Send to Rework",
      confirmClass: "bg-orange-600 hover:bg-orange-700",
    },
    scrap: {
      title: "Scrap Batch",
      description: "This will permanently close the work order and deduct the scrap from inventory. This cannot be undone.",
      label: "Scrap reason (required)",
      placeholder: "Describe why the batch is being scrapped...",
      confirmLabel: "Scrap Batch",
      confirmClass: "bg-red-700 hover:bg-red-800",
    },
  }

  const activeConfig = dialogMode ? dialogConfig[dialogMode] : null

  if (inspectionLoading || rejectedLoading || reworkLoading) {
    return <div className="p-8">Loading QC Dashboard...</div>
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-end">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">QC Dashboard</h1>
          <p className="text-muted-foreground mt-2">
            Inspection queue, rejected batches, and rework operations.
          </p>
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Card className="border-l-4 border-l-cyan-500">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground uppercase tracking-wider flex items-center">
              <ClipboardCheck className="w-4 h-4 mr-2 text-cyan-500" />
              Pending Inspections
            </CardTitle>
          </CardHeader>
          <CardContent>
            <span className="text-3xl font-bold">{inspectionQueue?.length || 0}</span>
          </CardContent>
        </Card>

        <Card className="border-l-4 border-l-red-500">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground uppercase tracking-wider flex items-center">
              <XCircle className="w-4 h-4 mr-2 text-red-500" />
              Rejected Batches
            </CardTitle>
          </CardHeader>
          <CardContent>
            <span className="text-3xl font-bold">{rejectedQueue?.length || 0}</span>
          </CardContent>
        </Card>

        <Card className="border-l-4 border-l-orange-500">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground uppercase tracking-wider flex items-center">
              <RefreshCw className="w-4 h-4 mr-2 text-orange-500" />
              Rework Queue
            </CardTitle>
          </CardHeader>
          <CardContent>
            <span className="text-3xl font-bold">{reworkQueue?.length || 0}</span>
          </CardContent>
        </Card>
      </div>

      {/* Inspection Queue Table */}
      <Card>
        <CardHeader>
          <CardTitle>Pending Inspections</CardTitle>
        </CardHeader>
        <CardContent>
          {inspectionQueue && inspectionQueue.length > 0 ? (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>WO Number</TableHead>
                  <TableHead>Product ID</TableHead>
                  <TableHead>Produced Qty</TableHead>
                  <TableHead>Scrap Qty</TableHead>
                  <TableHead>Due Date</TableHead>
                  <TableHead>Priority</TableHead>
                  <TableHead>Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {inspectionQueue.map((wo) => (
                  <TableRow key={wo.work_order_id}>
                    <TableCell className="font-mono">{wo.wo_number}</TableCell>
                    <TableCell className="font-mono text-xs">{wo.product_id}</TableCell>
                    <TableCell>{wo.produced_quantity}</TableCell>
                    <TableCell>{wo.scrap_quantity ?? 0}</TableCell>
                    <TableCell>{wo.due_date || "—"}</TableCell>
                    <TableCell>
                      <Badge variant="outline">{wo.priority || "NORMAL"}</Badge>
                    </TableCell>
                    <TableCell>
                      <div className="flex gap-2">
                        <Button
                          size="sm"
                          className="bg-green-600 hover:bg-green-700"
                          onClick={() => openDialog(wo, "approve")}
                        >
                          <CheckCircle className="w-3 h-3 mr-1" />
                          Approve
                        </Button>
                        <Button
                          size="sm"
                          variant="destructive"
                          onClick={() => openDialog(wo, "reject")}
                        >
                          <XCircle className="w-3 h-3 mr-1" />
                          Reject
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          ) : (
            <p className="text-muted-foreground text-center py-4">No pending inspections</p>
          )}
        </CardContent>
      </Card>

      {/* Rejected Queue Table */}
      <Card>
        <CardHeader>
          <CardTitle>Rejected Batches</CardTitle>
        </CardHeader>
        <CardContent>
          {rejectedQueue && rejectedQueue.length > 0 ? (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>WO Number</TableHead>
                  <TableHead>Product ID</TableHead>
                  <TableHead>Produced Qty</TableHead>
                  <TableHead>Due Date</TableHead>
                  <TableHead>Priority</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {rejectedQueue.map((wo) => (
                  <TableRow key={wo.work_order_id}>
                    <TableCell className="font-mono">{wo.wo_number}</TableCell>
                    <TableCell className="font-mono text-xs">{wo.product_id}</TableCell>
                    <TableCell>{wo.produced_quantity}</TableCell>
                    <TableCell>{wo.due_date || "—"}</TableCell>
                    <TableCell>
                      <Badge variant="outline">{wo.priority || "NORMAL"}</Badge>
                    </TableCell>
                    <TableCell>
                      <Badge variant="destructive">{wo.status}</Badge>
                    </TableCell>
                    <TableCell>
                      <div className="flex gap-2">
                        <Button
                          size="sm"
                          variant="outline"
                          className="border-orange-300 text-orange-700 hover:bg-orange-50"
                          onClick={() => openDialog(wo, "rework")}
                        >
                          <RefreshCw className="w-3 h-3 mr-1" />
                          Rework
                        </Button>
                        <Button
                          size="sm"
                          variant="destructive"
                          onClick={() => openDialog(wo, "scrap")}
                        >
                          <AlertTriangle className="w-3 h-3 mr-1" />
                          Scrap
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          ) : (
            <p className="text-muted-foreground text-center py-4">No rejected batches</p>
          )}
        </CardContent>
      </Card>

      {/* Rework Queue Table */}
      <Card>
        <CardHeader>
          <CardTitle>Rework Queue</CardTitle>
        </CardHeader>
        <CardContent>
          {reworkQueue && reworkQueue.length > 0 ? (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>WO Number</TableHead>
                  <TableHead>Product ID</TableHead>
                  <TableHead>Produced Qty</TableHead>
                  <TableHead>Due Date</TableHead>
                  <TableHead>Priority</TableHead>
                  <TableHead>Status</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {reworkQueue.map((wo) => (
                  <TableRow key={wo.work_order_id}>
                    <TableCell className="font-mono">{wo.wo_number}</TableCell>
                    <TableCell className="font-mono text-xs">{wo.product_id}</TableCell>
                    <TableCell>{wo.produced_quantity}</TableCell>
                    <TableCell>{wo.due_date || "—"}</TableCell>
                    <TableCell>
                      <Badge variant="outline">{wo.priority || "NORMAL"}</Badge>
                    </TableCell>
                    <TableCell>
                      <Badge variant="secondary">{wo.status}</Badge>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          ) : (
            <p className="text-muted-foreground text-center py-4">No rework items</p>
          )}
        </CardContent>
      </Card>

      {/* Action Confirmation Dialog */}
      {activeConfig && (
        <Dialog open={dialogMode !== null} onOpenChange={(open) => { if (!open && !isMutating) closeDialog() }}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>{activeConfig.title}</DialogTitle>
              <DialogDescription>
                {activeWO && (
                  <span className="font-mono text-sm">WO {activeWO.wo_number} — Produced: {activeWO.produced_quantity}</span>
                )}
                <br />
                {activeConfig.description}
              </DialogDescription>
            </DialogHeader>

            <div className="space-y-2">
              <Label>{activeConfig.label}</Label>
              <Textarea
                placeholder={activeConfig.placeholder}
                value={remarks}
                onChange={(e) => setRemarks(e.target.value)}
                rows={3}
                disabled={isMutating}
              />
              {requiresReason && remarks.trim().length === 0 && (
                <p className="text-xs text-red-500">A reason is required.</p>
              )}
            </div>

            <DialogFooter>
              <Button variant="outline" onClick={closeDialog} disabled={isMutating}>
                Cancel
              </Button>
              <Button
                className={activeConfig.confirmClass}
                onClick={handleConfirm}
                disabled={isMutating || !canConfirm}
              >
                {isMutating && <Loader2 className="w-3.5 h-3.5 mr-1 animate-spin" />}
                {activeConfig.confirmLabel}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      )}
    </div>
  )
}
