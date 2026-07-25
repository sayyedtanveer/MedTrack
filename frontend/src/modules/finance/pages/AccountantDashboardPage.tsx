// Accountant Dashboard Page
import { useQuery } from "@tanstack/react-query"
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card"
import { Table, TableHeader, TableRow, TableHead, TableBody, TableCell } from "@/components/ui/table"
import { Badge } from "@/components/ui/badge"
import { DollarSign, AlertCircle, CheckCircle, TrendingUp } from "lucide-react"
import apiClient from "@/services/api-client"

export default function AccountantDashboardPage() {
  const { data: pendingInvoices, isLoading: pendingLoading } = useQuery({
    queryKey: ["accountant-pending-invoices"],
    queryFn: async () => {
      const response = await apiClient.get("/finance/accountant/pending-invoices")
      return response.data
    }
  })

  const { data: overdueInvoices, isLoading: overdueLoading } = useQuery({
    queryKey: ["accountant-overdue-invoices"],
    queryFn: async () => {
      const response = await apiClient.get("/finance/accountant/overdue-invoices")
      return response.data
    }
  })

  const { data: paidInvoices, isLoading: paidLoading } = useQuery({
    queryKey: ["accountant-paid-invoices"],
    queryFn: async () => {
      const response = await apiClient.get("/finance/accountant/paid-invoices")
      return response.data
    }
  })

  const { data: revenueMetrics, isLoading: revenueLoading } = useQuery({
    queryKey: ["accountant-revenue"],
    queryFn: async () => {
      const response = await apiClient.get("/finance/accountant/revenue-metrics")
      return response.data
    }
  })

  if (pendingLoading || overdueLoading || paidLoading || revenueLoading) {
    return <div className="p-8">Loading Accountant Dashboard...</div>
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-end">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Accountant Dashboard</h1>
          <p className="text-muted-foreground mt-2">
            Invoice management, revenue tracking, and financial operations.
          </p>
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <Card className="border-l-4 border-l-blue-500">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground uppercase tracking-wider flex items-center">
              <DollarSign className="w-4 h-4 mr-2 text-blue-500" />
              Pending Invoices
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center">
              <span className="text-3xl font-bold">{pendingInvoices?.length || 0}</span>
            </div>
          </CardContent>
        </Card>

        <Card className="border-l-4 border-l-red-500">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground uppercase tracking-wider flex items-center">
              <AlertCircle className="w-4 h-4 mr-2 text-red-500" />
              Overdue
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center">
              <span className="text-3xl font-bold">{overdueInvoices?.length || 0}</span>
            </div>
          </CardContent>
        </Card>

        <Card className="border-l-4 border-l-green-500">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground uppercase tracking-wider flex items-center">
              <CheckCircle className="w-4 h-4 mr-2 text-green-500" />
              Paid (30d)
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center">
              <span className="text-3xl font-bold">{paidInvoices?.length || 0}</span>
            </div>
          </CardContent>
        </Card>

        <Card className="border-l-4 border-l-purple-500">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground uppercase tracking-wider flex items-center">
              <TrendingUp className="w-4 h-4 mr-2 text-purple-500" />
              Revenue (30d)
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center">
              <span className="text-3xl font-bold">${revenueMetrics?.total_revenue || 0}</span>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Revenue Metrics Card */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center">
            <TrendingUp className="w-5 h-5 mr-2" />
            Revenue Metrics (Last 30 Days)
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-3 gap-4">
            <div>
              <p className="text-sm text-muted-foreground">Paid Invoices</p>
              <p className="text-2xl font-bold">{revenueMetrics?.paid_invoice_count || 0}</p>
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Total Revenue</p>
              <p className="text-2xl font-bold">${revenueMetrics?.total_revenue || 0}</p>
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Avg Invoice Value</p>
              <p className="text-2xl font-bold">${revenueMetrics?.average_invoice_value || 0}</p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Pending Invoices Table */}
      <Card>
        <CardHeader>
          <CardTitle>Pending Invoices</CardTitle>
        </CardHeader>
        <CardContent>
          {pendingInvoices && pendingInvoices.length > 0 ? (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Invoice Number</TableHead>
                  <TableHead>Customer ID</TableHead>
                  <TableHead>Amount</TableHead>
                  <TableHead>Due Date</TableHead>
                  <TableHead>Status</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {pendingInvoices.map((inv: any) => (
                  <TableRow key={inv.invoice_id}>
                    <TableCell className="font-mono">{inv.invoice_number}</TableCell>
                    <TableCell className="font-mono text-xs">{inv.customer_id}</TableCell>
                    <TableCell>${inv.amount}</TableCell>
                    <TableCell>{inv.due_date || '-'}</TableCell>
                    <TableCell>
                      <Badge variant="outline">{inv.status}</Badge>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          ) : (
            <p className="text-muted-foreground text-center py-4">No pending invoices</p>
          )}
        </CardContent>
      </Card>

      {/* Overdue Invoices Table */}
      <Card>
        <CardHeader>
          <CardTitle>Overdue Invoices</CardTitle>
        </CardHeader>
        <CardContent>
          {overdueInvoices && overdueInvoices.length > 0 ? (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Invoice Number</TableHead>
                  <TableHead>Customer ID</TableHead>
                  <TableHead>Amount</TableHead>
                  <TableHead>Due Date</TableHead>
                  <TableHead>Status</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {overdueInvoices.map((inv: any) => (
                  <TableRow key={inv.invoice_id}>
                    <TableCell className="font-mono">{inv.invoice_number}</TableCell>
                    <TableCell className="font-mono text-xs">{inv.customer_id}</TableCell>
                    <TableCell className="text-red-600">${inv.amount}</TableCell>
                    <TableCell className="text-red-600">{inv.due_date}</TableCell>
                    <TableCell>
                      <Badge variant="destructive">{inv.status}</Badge>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          ) : (
            <p className="text-muted-foreground text-center py-4">No overdue invoices</p>
          )}
        </CardContent>
      </Card>

      {/* Paid Invoices Table */}
      <Card>
        <CardHeader>
          <CardTitle>Paid Invoices (Last 30 Days)</CardTitle>
        </CardHeader>
        <CardContent>
          {paidInvoices && paidInvoices.length > 0 ? (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Invoice Number</TableHead>
                  <TableHead>Customer ID</TableHead>
                  <TableHead>Amount</TableHead>
                  <TableHead>Paid Date</TableHead>
                  <TableHead>Status</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {paidInvoices.map((inv: any) => (
                  <TableRow key={inv.invoice_id}>
                    <TableCell className="font-mono">{inv.invoice_number}</TableCell>
                    <TableCell className="font-mono text-xs">{inv.customer_id}</TableCell>
                    <TableCell>${inv.amount}</TableCell>
                    <TableCell>{inv.paid_date || '-'}</TableCell>
                    <TableCell>
                      <Badge variant="default">{inv.status}</Badge>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          ) : (
            <p className="text-muted-foreground text-center py-4">No paid invoices in the last 30 days</p>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
