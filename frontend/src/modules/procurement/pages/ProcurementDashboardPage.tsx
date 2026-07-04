/**
 * Procurement Dashboard Page
 * Overview of procurement pipeline: purchase requisitions, pending PO approvals,
 * supplier deliveries, GRN pending, and material shortages blocking work orders.
 *
 * Requirements validated: 30.1–30.8
 */

import { useState } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { useNavigate } from "react-router-dom"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Table, TableHeader, TableRow, TableHead, TableBody, TableCell } from "@/components/ui/table"
import { Truck, FileText, AlertTriangle, PackageCheck, RefreshCw, Clock, ChevronDown, ChevronUp, CheckCircle } from "lucide-react"
import { useToast } from "@/hooks/use-toast"
import apiClient from "@/services/api-client"

interface ProcurementDashboardData {
  pending_requisitions: number
  pending_po_approvals: number
  upcoming_supplier_deliveries: number
  overdue_deliveries: number
  grn_pending: number
  material_shortages: number
}

interface PurchaseRequisition {
  id: string
  requisition_number: string
  material_name: string
  required_quantity: number
  shortage_quantity: number
  status: string
}

export default function ProcurementDashboardPage() {
  const navigate = useNavigate()
  const { toast } = useToast()
  const queryClient = useQueryClient()
  const [showRequisitions, setShowRequisitions] = useState(false)

  const { data, isLoading, isError, refetch, isFetching } = useQuery<ProcurementDashboardData>({
    queryKey: ["procurement-dashboard"],
    queryFn: async () => {
      const response = await apiClient.get("/procurement/dashboard")
      return response.data
    },
    refetchInterval: 60_000,
    retry: 1,
  })

  // Fetch recent purchase requisitions
  const { data: requisitions, isLoading: requisitionsLoading } = useQuery<PurchaseRequisition[]>({
    queryKey: ["purchase-requisitions-recent"],
    queryFn: async () => {
      const response = await apiClient.get("/procurement/requisitions", {
        params: { limit: 10, status: "PENDING_APPROVAL" }
      })
      return response.data
    },
    enabled: showRequisitions,
  })

  // Approve requisition mutation
  const approveMutation = useMutation({
    mutationFn: async (requisitionId: string) => {
      await apiClient.post(`/procurement/requisitions/${requisitionId}/approve`)
    },
    onSuccess: () => {
      toast({
        title: "Success",
        description: "Purchase requisition approved successfully",
      })
      queryClient.invalidateQueries({ queryKey: ["purchase-requisitions-recent"] })
      queryClient.invalidateQueries({ queryKey: ["procurement-dashboard"] })
    },
    onError: (error: any) => {
      toast({
        title: "Error",
        description: error.message || "Failed to approve requisition",
        variant: "destructive",
      })
    },
  })

  return (
    <div className="space-y-6 p-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-slate-900">Procurement Dashboard</h1>
          <p className="mt-1 text-sm text-slate-500">Procurement pipeline overview and pending actions</p>
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={() => refetch()}
          disabled={isFetching}
          className="gap-2"
        >
          <RefreshCw className={`h-4 w-4 ${isFetching ? "animate-spin" : ""}`} />
          Refresh
        </Button>
      </div>

      {isError && (
        <div className="rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm text-amber-800">
          Could not load dashboard data. Displaying last known values or empty state.
        </div>
      )}

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {/* Purchase Requisitions */}
        <Card
          className="cursor-pointer hover:shadow-md transition-shadow"
        >
          <CardHeader className="pb-2">
            <CardDescription className="flex items-center gap-2">
              <FileText className="h-4 w-4 text-blue-500" />
              Purchase Requisitions
            </CardDescription>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold text-slate-900">
              {isLoading ? "—" : (data?.pending_requisitions ?? 0)}
            </p>
            <div className="mt-2 flex items-center gap-2">
              <p className="text-xs text-slate-500">Awaiting approval</p>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setShowRequisitions(!showRequisitions)}
                className="ml-auto h-6 px-2"
              >
                {showRequisitions ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
              </Button>
            </div>
          </CardContent>
        </Card>

        {/* Pending PO Approvals */}
        <Card
          className="cursor-pointer hover:shadow-md transition-shadow"
          onClick={() => navigate("/procurement/purchase-orders")}
        >
          <CardHeader className="pb-2">
            <CardDescription className="flex items-center gap-2">
              <FileText className="h-4 w-4 text-indigo-500" />
              Pending PO Approvals
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex items-center gap-2">
              <p className="text-3xl font-bold text-slate-900">
                {isLoading ? "—" : (data?.pending_po_approvals ?? 0)}
              </p>
              {!isLoading && (data?.pending_po_approvals ?? 0) > 0 && (
                <Badge className="bg-indigo-100 text-indigo-700 text-xs">Action needed</Badge>
              )}
            </div>
            <p className="mt-1 text-xs text-slate-500">Purchase orders awaiting approval</p>
          </CardContent>
        </Card>

        {/* Supplier Deliveries */}
        <Card
          className="cursor-pointer hover:shadow-md transition-shadow"
          onClick={() => navigate("/procurement/purchase-orders")}
        >
          <CardHeader className="pb-2">
            <CardDescription className="flex items-center gap-2">
              <Truck className="h-4 w-4 text-emerald-500" />
              Supplier Deliveries (next 7 days)
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex items-center gap-2">
              <p className="text-3xl font-bold text-slate-900">
                {isLoading ? "—" : (data?.upcoming_supplier_deliveries ?? 0)}
              </p>
              {!isLoading && (data?.overdue_deliveries ?? 0) > 0 && (
                <Badge variant="destructive" className="text-xs">
                  {data?.overdue_deliveries} overdue
                </Badge>
              )}
            </div>
            <p className="mt-1 text-xs text-slate-500">Incoming within the week</p>
          </CardContent>
        </Card>

        {/* GRN Pending */}
        <Card
          className="cursor-pointer hover:shadow-md transition-shadow"
          onClick={() => navigate("/procurement/grn")}
        >
          <CardHeader className="pb-2">
            <CardDescription className="flex items-center gap-2">
              <PackageCheck className="h-4 w-4 text-teal-500" />
              GRN Pending
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex items-center gap-2">
              <p className="text-3xl font-bold text-slate-900">
                {isLoading ? "—" : (data?.grn_pending ?? 0)}
              </p>
              {!isLoading && (data?.grn_pending ?? 0) > 0 && (
                <Badge className="bg-teal-100 text-teal-700 text-xs">Receipt needed</Badge>
              )}
            </div>
            <p className="mt-1 text-xs text-slate-500">Goods received but not yet inspected</p>
          </CardContent>
        </Card>

        {/* Material Shortages */}
        <Card
          className="cursor-pointer hover:shadow-md transition-shadow"
          onClick={() => navigate("/work-orders?status=MATERIAL_PENDING")}
        >
          <CardHeader className="pb-2">
            <CardDescription className="flex items-center gap-2">
              <AlertTriangle className="h-4 w-4 text-red-500" />
              Material Shortages
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex items-center gap-2">
              <p className="text-3xl font-bold text-slate-900">
                {isLoading ? "—" : (data?.material_shortages ?? 0)}
              </p>
              {!isLoading && (data?.material_shortages ?? 0) > 0 && (
                <Badge variant="destructive" className="text-xs">Blocking WOs</Badge>
              )}
            </div>
            <p className="mt-1 text-xs text-slate-500">Work orders blocked by shortage</p>
          </CardContent>
        </Card>

        {/* Overdue Deliveries Indicator */}
        <Card>
          <CardHeader className="pb-2">
            <CardDescription className="flex items-center gap-2">
              <Clock className="h-4 w-4 text-orange-500" />
              Overdue Deliveries
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex items-center gap-2">
              <p className="text-3xl font-bold text-slate-900">
                {isLoading ? "—" : (data?.overdue_deliveries ?? 0)}
              </p>
              {!isLoading && (data?.overdue_deliveries ?? 0) > 0 && (
                <Badge variant="destructive" className="text-xs">Overdue</Badge>
              )}
            </div>
            <p className="mt-1 text-xs text-slate-500">Supplier deliveries past expected date</p>
          </CardContent>
        </Card>
      </div>

      {/* Purchase Requisitions Expandable Section */}
      {showRequisitions && (
        <Card>
          <CardHeader>
            <CardTitle>Recent Purchase Requisitions (Pending Approval)</CardTitle>
          </CardHeader>
          <CardContent>
            {requisitionsLoading ? (
              <p className="text-center py-4 text-slate-500">Loading requisitions...</p>
            ) : !requisitions || requisitions.length === 0 ? (
              <p className="text-center py-4 text-slate-500">No pending requisitions</p>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Requisition #</TableHead>
                    <TableHead>Material</TableHead>
                    <TableHead className="text-right">Required Qty</TableHead>
                    <TableHead className="text-right">Shortage Qty</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead className="text-right">Action</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {requisitions.map((req) => (
                    <TableRow key={req.id}>
                      <TableCell className="font-mono text-sm">{req.requisition_number}</TableCell>
                      <TableCell>{req.material_name}</TableCell>
                      <TableCell className="text-right">{req.required_quantity}</TableCell>
                      <TableCell className="text-right">{req.shortage_quantity}</TableCell>
                      <TableCell>
                        <Badge variant="outline" className="bg-amber-50 text-amber-700">
                          {req.status}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-right">
                        <Button
                          size="sm"
                          onClick={() => approveMutation.mutate(req.id)}
                          disabled={approveMutation.isPending}
                          className="gap-1"
                        >
                          <CheckCircle className="h-3 w-3" />
                          Approve
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </CardContent>
        </Card>
      )}

      <div className="flex justify-end gap-3">
        <Button variant="outline" onClick={() => navigate("/procurement/purchase-orders")}>
          Purchase Orders
        </Button>
        <Button variant="outline" onClick={() => navigate("/procurement/suppliers")}>
          Suppliers
        </Button>
      </div>
    </div>
  )
}
