// Worker Dashboard Page
import { useQuery } from "@tanstack/react-query"
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card"
import { Table, TableHeader, TableRow, TableHead, TableBody, TableCell } from "@/components/ui/table"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Play, Pause, CheckCircle, Package } from "lucide-react"
import apiClient from "@/services/api-client"

export default function WorkerDashboardPage() {
  const { data: workerQueue, isLoading } = useQuery({
    queryKey: ["worker-queue"],
    queryFn: async () => {
      const response = await apiClient.get("/work-orders/worker/queue")
      return response.data
    }
  })

  if (isLoading) {
    return <div className="p-8">Loading Worker Dashboard...</div>
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-end">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Worker Dashboard</h1>
          <p className="text-muted-foreground mt-2">
            Assigned work orders and production operations.
          </p>
        </div>
      </div>

      {/* Summary Card */}
      <Card className="border-l-4 border-l-green-500">
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-medium text-muted-foreground uppercase tracking-wider flex items-center">
            <Package className="w-4 h-4 mr-2 text-green-500" />
            Assigned Work Orders
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center">
            <span className="text-3xl font-bold">{workerQueue?.length || 0}</span>
          </div>
        </CardContent>
      </Card>

      {/* Worker Queue Table */}
      <Card>
        <CardHeader>
          <CardTitle>Assigned Work Orders & Operations</CardTitle>
        </CardHeader>
        <CardContent>
          {workerQueue && workerQueue.length > 0 ? (
            <div className="space-y-4">
              {workerQueue.map((wo: any) => (
                <div key={wo.work_order_id} className="border rounded-lg p-4">
                  <div className="flex justify-between items-start mb-3">
                    <div>
                      <h3 className="font-semibold text-lg">{wo.wo_number}</h3>
                      <p className="text-sm text-muted-foreground">
                        Due: {wo.due_date || 'Not specified'} | Priority: {wo.priority}
                      </p>
                    </div>
                    <Badge variant="outline">{wo.status}</Badge>
                  </div>
                  
                  {/* Job Cards Table */}
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Operation ID</TableHead>
                        <TableHead>Sequence</TableHead>
                        <TableHead>Status</TableHead>
                        <TableHead>Assigned To</TableHead>
                        <TableHead>Actions</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {wo.job_cards.map((jc: any) => (
                        <TableRow key={jc.job_card_id}>
                          <TableCell className="font-mono text-xs">{jc.operation_id}</TableCell>
                          <TableCell>{jc.sequence}</TableCell>
                          <TableCell>
                            <Badge 
                              variant={
                                jc.status === 'DONE' ? 'default' :
                                jc.status === 'IN_PROGRESS' ? 'secondary' :
                                jc.status === 'PAUSED' ? 'outline' :
                                'outline'
                              }
                            >
                              {jc.status}
                            </Badge>
                          </TableCell>
                          <TableCell className="font-mono text-xs">
                            {jc.assigned_to || 'Unassigned'}
                          </TableCell>
                          <TableCell>
                            <div className="flex gap-2">
                              {jc.status === 'PENDING' && (
                                <Button size="sm" variant="outline">
                                  <Play className="w-3 h-3 mr-1" />
                                  Start
                                </Button>
                              )}
                              {jc.status === 'IN_PROGRESS' && (
                                <>
                                  <Button size="sm" variant="outline">
                                    <Pause className="w-3 h-3 mr-1" />
                                    Pause
                                  </Button>
                                  <Button size="sm" variant="default">
                                    <CheckCircle className="w-3 h-3 mr-1" />
                                    Complete
                                  </Button>
                                </>
                              )}
                              {jc.status === 'PAUSED' && (
                                <>
                                  <Button size="sm" variant="outline">
                                    <Play className="w-3 h-3 mr-1" />
                                    Resume
                                  </Button>
                                  <Button size="sm" variant="default">
                                    <CheckCircle className="w-3 h-3 mr-1" />
                                    Complete
                                  </Button>
                                </>
                              )}
                            </div>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-muted-foreground text-center py-4">No assigned work orders</p>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
