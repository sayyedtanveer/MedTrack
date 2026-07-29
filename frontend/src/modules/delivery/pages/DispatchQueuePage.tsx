/**
 * Dispatch Queue Page
 * Shows all READY_FOR_DISPATCH sales orders for the Dispatch officer.
 * Each row has a "Create Delivery Note" button that navigates to the
 * delivery creation form pre-filled with the SO ID.
 *
 * Requirements: 33 — Gap #5
 */

import { useQuery } from "@tanstack/react-query"
import { useNavigate } from "react-router-dom"
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card"
import { Table, TableHeader, TableRow, TableHead, TableBody, TableCell } from "@/components/ui/table"

import { PackageCheck } from "lucide-react"
import apiClient from "@/services/api-client"
import { AssistantEngine } from "@/lib/assistant/AssistantEngine"
import { MedTrackAssistant } from "@/components/shared/assistant/MedTrackAssistant"
import { AssistantButton } from "@/components/shared/assistant/AssistantButton"

interface DispatchQueueItem {
  id: string
  order_number: string
  customer_name: string | null
  grand_total: number
  ready_at: string | null
}

const formatCurrency = (val: number | null | undefined) => {
  if (val == null) return "—"
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
  }).format(val)
}

function formatReadySince(isoString: string | null): string {
  if (!isoString) return "—"
  return new Date(isoString).toLocaleString()
}

export default function DispatchQueuePage() {
  const navigate = useNavigate()

  const { data: queue, isLoading, isError } = useQuery<DispatchQueueItem[]>({
    queryKey: ["dispatch-queue"],
    queryFn: async () => {
      const response = await apiClient.get("/delivery/dispatch-queue")
      return response.data
    },
  })

  if (isLoading) {
    return <div className="p-8">Loading dispatch queue...</div>
  }

  if (isError) {
    return (
      <div className="p-8 text-destructive">
        Failed to load dispatch queue. Please try again.
      </div>
    )
  }

  // Calculate top priority dispatch guidance
  const topGuidance = (() => {
    if (!queue || queue.length === 0) return null;
    
    const guidances = queue
      .map(item => AssistantEngine.getGuidance({ ...item, type: 'dispatch_order', status: 'CONFIRMED' }))
      .filter(Boolean) as any[];
      
    if (guidances.length === 0) return null;
    
    // Sort logic similar to InboxProvider
    const weights: Record<string, number> = { 'critical': 5, 'high': 4, 'medium': 3, 'low': 2, 'info': 1 };
    guidances.sort((a, b) => {
      const pA = weights[a.priority] || 0;
      const pB = weights[b.priority] || 0;
      if (pA !== pB) return pB - pA;
      if (a.dueDate && b.dueDate) return new Date(a.dueDate).getTime() - new Date(b.dueDate).getTime();
      return a.dueDate ? -1 : (b.dueDate ? 1 : 0);
    });
    
    return guidances[0];
  })();

  return (
    <div className="space-y-6 p-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Dispatch Queue</h1>
        <p className="text-muted-foreground mt-2">
          Sales orders ready for dispatch
        </p>
      </div>

      {topGuidance && (
        <div className="mb-2">
          <MedTrackAssistant guidance={topGuidance} />
        </div>
      )}

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <PackageCheck className="h-5 w-5 text-blue-500" />
            Ready for Dispatch
          </CardTitle>
        </CardHeader>
        <CardContent>
          {queue && queue.length > 0 ? (
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Order #</TableHead>
                    <TableHead>Customer</TableHead>
                    <TableHead className="text-right">Grand Total</TableHead>
                    <TableHead>Ready Since</TableHead>
                    <TableHead className="text-right">Action</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {queue.map((item) => (
                    <TableRow key={item.id}>
                      <TableCell className="font-mono font-medium">
                        {item.order_number}
                      </TableCell>
                      <TableCell>{item.customer_name ?? "—"}</TableCell>
                      <TableCell className="text-right">
                        {formatCurrency(item.grand_total)}
                      </TableCell>
                      <TableCell>{formatReadySince(item.ready_at)}</TableCell>
                      <TableCell className="text-right">
                        <AssistantButton
                          size="sm"
                          onClick={() =>
                            navigate(`/deliveries/new?so_id=${item.id}`)
                          }
                          pulse={topGuidance?.route?.id === item.id || (!topGuidance?.route?.id && queue.indexOf(item) === 0)}
                        >
                          Create Delivery Note
                        </AssistantButton>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          ) : (
            <p className="text-center py-8 text-muted-foreground">
              No orders are currently ready for dispatch.
            </p>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
