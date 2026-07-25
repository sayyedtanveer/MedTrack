// Planner Dashboard Page
import { useQuery } from "@tanstack/react-query"
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card"
import { Table, TableHeader, TableRow, TableHead, TableBody, TableCell } from "@/components/ui/table"
import { Badge } from "@/components/ui/badge"
import { Calendar, AlertTriangle, Package, RefreshCw, TrendingUp } from "lucide-react"
import apiClient from "@/services/api-client"

export default function PlannerDashboardPage() {
  const { data: planningQueue, isLoading: planningLoading } = useQuery({
    queryKey: ["planner-planning-queue"],
    queryFn: async () => {
      const response = await apiClient.get("/work-orders/planner/planning-queue")
      return response.data
    }
  })

  const { data: overdueQueue, isLoading: overdueLoading } = useQuery({
    queryKey: ["planner-overdue-queue"],
    queryFn: async () => {
      const response = await apiClient.get("/work-orders/planner/overdue-queue")
      return response.data
    }
  })

  const { data: shortageQueue, isLoading: shortageLoading } = useQuery({
    queryKey: ["planner-shortage-queue"],
    queryFn: async () => {
      const response = await apiClient.get("/work-orders/planner/shortage-queue")
      return response.data
    }
  })

  const { data: reworkQueue, isLoading: reworkLoading } = useQuery({
    queryKey: ["planner-rework-queue"],
    queryFn: async () => {
      const response = await apiClient.get("/work-orders/planner/rework-queue")
      return response.data
    }
  })

  const { data: capacityUtilization, isLoading: capacityLoading } = useQuery({
    queryKey: ["planner-capacity"],
    queryFn: async () => {
      const response = await apiClient.get("/work-orders/planner/capacity")
      return response.data
    }
  })

  if (planningLoading || overdueLoading || shortageLoading || reworkLoading || capacityLoading) {
    return <div className="p-8">Loading Planner Dashboard...</div>
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-end">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Planner Dashboard</h1>
          <p className="text-muted-foreground mt-2">
            Work order planning, capacity utilization, and exception management.
          </p>
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <Card className="border-l-4 border-l-blue-500">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground uppercase tracking-wider flex items-center">
              <Calendar className="w-4 h-4 mr-2 text-blue-500" />
              Planning Queue
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center">
              <span className="text-3xl font-bold">{planningQueue?.length || 0}</span>
            </div>
          </CardContent>
        </Card>

        <Card className="border-l-4 border-l-red-500">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground uppercase tracking-wider flex items-center">
              <AlertTriangle className="w-4 h-4 mr-2 text-red-500" />
              Overdue
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center">
              <span className="text-3xl font-bold">{overdueQueue?.length || 0}</span>
            </div>
          </CardContent>
        </Card>

        <Card className="border-l-4 border-l-orange-500">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground uppercase tracking-wider flex items-center">
              <Package className="w-4 h-4 mr-2 text-orange-500" />
              Shortages
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center">
              <span className="text-3xl font-bold">{shortageQueue?.length || 0}</span>
            </div>
          </CardContent>
        </Card>

        <Card className="border-l-4 border-l-amber-500">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground uppercase tracking-wider flex items-center">
              <RefreshCw className="w-4 h-4 mr-2 text-amber-500" />
              Rework
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center">
              <span className="text-3xl font-bold">{reworkQueue?.length || 0}</span>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Capacity Utilization Card */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center">
            <TrendingUp className="w-5 h-5 mr-2" />
            Capacity Utilization
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-3 gap-4">
            <div>
              <p className="text-sm text-muted-foreground">Active WOs</p>
              <p className="text-2xl font-bold">{capacityUtilization?.active_wo_count || 0}</p>
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Total Planned Quantity</p>
              <p className="text-2xl font-bold">{capacityUtilization?.total_planned_quantity || 0}</p>
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Utilization</p>
              <p className="text-2xl font-bold">{capacityUtilization?.utilization_percent || 0}%</p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Planning Queue Table */}
      <Card>
        <CardHeader>
          <CardTitle>Planning Queue</CardTitle>
        </CardHeader>
        <CardContent>
          {planningQueue && planningQueue.length > 0 ? (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>WO Number</TableHead>
                  <TableHead>Product ID</TableHead>
                  <TableHead>Quantity</TableHead>
                  <TableHead>Due Date</TableHead>
                  <TableHead>Priority</TableHead>
                  <TableHead>Status</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {planningQueue.map((wo: any) => (
                  <TableRow key={wo.work_order_id}>
                    <TableCell className="font-mono">{wo.wo_number}</TableCell>
                    <TableCell className="font-mono text-xs">{wo.product_id}</TableCell>
                    <TableCell>{wo.quantity}</TableCell>
                    <TableCell>{wo.due_date || '-'}</TableCell>
                    <TableCell>
                      <Badge variant="outline">{wo.priority}</Badge>
                    </TableCell>
                    <TableCell>
                      <Badge variant="outline">{wo.status}</Badge>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          ) : (
            <p className="text-muted-foreground text-center py-4">No WOs in planning queue</p>
          )}
        </CardContent>
      </Card>

      {/* Overdue Queue Table */}
      <Card>
        <CardHeader>
          <CardTitle>Overdue Work Orders</CardTitle>
        </CardHeader>
        <CardContent>
          {overdueQueue && overdueQueue.length > 0 ? (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>WO Number</TableHead>
                  <TableHead>Product ID</TableHead>
                  <TableHead>Quantity</TableHead>
                  <TableHead>Due Date</TableHead>
                  <TableHead>Priority</TableHead>
                  <TableHead>Status</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {overdueQueue.map((wo: any) => (
                  <TableRow key={wo.work_order_id}>
                    <TableCell className="font-mono">{wo.wo_number}</TableCell>
                    <TableCell className="font-mono text-xs">{wo.product_id}</TableCell>
                    <TableCell>{wo.quantity}</TableCell>
                    <TableCell className="text-red-600">{wo.due_date}</TableCell>
                    <TableCell>
                      <Badge variant="destructive">{wo.priority}</Badge>
                    </TableCell>
                    <TableCell>
                      <Badge variant="destructive">{wo.status}</Badge>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          ) : (
            <p className="text-muted-foreground text-center py-4">No overdue WOs</p>
          )}
        </CardContent>
      </Card>

      {/* Shortage Queue Table */}
      <Card>
        <CardHeader>
          <CardTitle>Material Shortages</CardTitle>
        </CardHeader>
        <CardContent>
          {shortageQueue && shortageQueue.length > 0 ? (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>WO Number</TableHead>
                  <TableHead>Product ID</TableHead>
                  <TableHead>Quantity</TableHead>
                  <TableHead>Due Date</TableHead>
                  <TableHead>Priority</TableHead>
                  <TableHead>Status</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {shortageQueue.map((wo: any) => (
                  <TableRow key={wo.work_order_id}>
                    <TableCell className="font-mono">{wo.wo_number}</TableCell>
                    <TableCell className="font-mono text-xs">{wo.product_id}</TableCell>
                    <TableCell>{wo.quantity}</TableCell>
                    <TableCell>{wo.due_date || '-'}</TableCell>
                    <TableCell>
                      <Badge variant="outline">{wo.priority}</Badge>
                    </TableCell>
                    <TableCell>
                      <Badge variant="destructive">{wo.status}</Badge>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          ) : (
            <p className="text-muted-foreground text-center py-4">No shortages</p>
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
                  <TableHead>Quantity</TableHead>
                  <TableHead>Due Date</TableHead>
                  <TableHead>Priority</TableHead>
                  <TableHead>Status</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {reworkQueue.map((wo: any) => (
                  <TableRow key={wo.work_order_id}>
                    <TableCell className="font-mono">{wo.wo_number}</TableCell>
                    <TableCell className="font-mono text-xs">{wo.product_id}</TableCell>
                    <TableCell>{wo.quantity}</TableCell>
                    <TableCell>{wo.due_date || '-'}</TableCell>
                    <TableCell>
                      <Badge variant="outline">{wo.priority}</Badge>
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
    </div>
  )
}
