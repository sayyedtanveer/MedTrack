// Inventory Dashboard Page
import { useQuery } from "@tanstack/react-query"
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card"
import { Table, TableHead, TableHeader, TableRow, TableBody, TableCell } from "@/components/ui/table"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Link } from "react-router-dom"
import { AlertCircle, ArrowDown, ArrowUp, Activity } from "lucide-react"
import { materialService } from "@/services/material.service"

export default function InventoryDashboard() {
  const { data: realtimeStock, isLoading: stockLoading } = useQuery({
    queryKey: ["realtimeStock"],
    queryFn: () => materialService.getRealtimeStock()
  })

  const { data: ledger, isLoading: ledgerLoading } = useQuery({
    queryKey: ["stockLedger"],
    queryFn: () => materialService.getStockLedger({ limit: 10 })
  })

  if (stockLoading || ledgerLoading) {
    return <div className="p-8">Loading Dashboard...</div>
  }

  const lowStockItems = realtimeStock?.filter((s: any) => s.available_stock <= 10) || []

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-end">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Inventory Dashboard</h1>
          <p className="text-muted-foreground mt-2">
            Real-time stock overview, reservations, and recent movements.
          </p>
        </div>
        <div className="flex flex-wrap gap-3">
          <Button variant="outline" asChild>
            <Link to="/inventory/materials">View Materials</Link>
          </Button>
          <Button variant="outline" asChild>
            <Link to="/inventory/movements">Stock Movements</Link>
          </Button>
          <Button variant="outline" asChild>
            <Link to="/inventory/transactions">View Transactions</Link>
          </Button>
          <Button variant="outline" asChild>
            <Link to="/inventory/batches">Batches</Link>
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Card className="border-l-4 border-l-blue-500">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground uppercase tracking-wider">
              Total Monitored Items
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center">
              <span className="text-3xl font-bold">{realtimeStock?.length || 0}</span>
            </div>
          </CardContent>
        </Card>

        <Card className="border-l-4 border-l-orange-500">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground uppercase tracking-wider flex items-center">
              Items with Reservations
              <Activity className="w-4 h-4 ml-2 text-orange-500" />
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center">
              <span className="text-3xl font-bold">
                {realtimeStock?.filter((s: any) => s.reserved_stock > 0).length || 0}
              </span>
            </div>
          </CardContent>
        </Card>

        <Card className="border-l-4 border-l-red-500">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground uppercase tracking-wider flex items-center">
              Low Stock Alerts
              <AlertCircle className="w-4 h-4 ml-2 text-red-500" />
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center">
              <span className="text-3xl font-bold text-red-600">{lowStockItems.length}</span>
            </div>
          </CardContent>
        </Card>
      </div>

      {lowStockItems.length > 0 && (
        <Card className="border-red-200 bg-red-50/50">
          <CardHeader>
            <CardTitle className="text-red-700 flex items-center">
              <AlertCircle className="w-5 h-5 mr-2" /> Critical Stock Alerts
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4">
              {lowStockItems.map((item: any) => (
                <div key={item.material_id} className="flex justify-between items-center p-3 bg-white rounded-md shadow-sm border border-red-100">
                  <span className="font-medium text-sm">{item.material_name} ({item.material_code})</span>
                  <Badge variant="destructive">{item.available_stock.toFixed(2)} left</Badge>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle>Real-time Stock Levels</CardTitle>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Item</TableHead>
                  <TableHead className="text-right">In Stock</TableHead>
                  <TableHead className="text-right">Reserved</TableHead>
                  <TableHead className="text-right">Available</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {realtimeStock?.slice(0, 10).map((row: any) => (
                  <TableRow key={row.material_id}>
                    <TableCell data-label="Item" className="font-medium text-right md:text-left">{row.material_name}</TableCell>
                    <TableCell data-label="In Stock" className="text-right">{row.current_stock.toFixed(2)}</TableCell>
                    <TableCell data-label="Reserved" className="text-right text-orange-600 font-medium">
                      {row.reserved_stock > 0 ? row.reserved_stock.toFixed(2) : '-'}
                    </TableCell>
                    <TableCell data-label="Available" className="text-right font-bold text-blue-700">
                      {row.available_stock.toFixed(2)}
                    </TableCell>
                  </TableRow>
                ))}
                {(!realtimeStock || realtimeStock.length === 0) && (
                  <TableRow>
                    <TableCell colSpan={4} className="text-center text-muted-foreground py-8">
                      No stock data available.
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Recent Ledger Operations</CardTitle>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Date</TableHead>
                  <TableHead>Type</TableHead>
                  <TableHead className="text-right">Change</TableHead>
                  <TableHead className="text-right">Balance</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {ledger?.map((entry: any) => (
                  <TableRow key={entry.id}>
                    <TableCell data-label="Date" className="text-xs text-muted-foreground text-right md:text-left">
                      {new Date(entry.transaction_date).toLocaleString()}
                    </TableCell>
                    <TableCell data-label="Type" className="text-right md:text-left">
                      <Badge variant={
                        entry.transaction_type === 'in' ? 'outline' : 
                        entry.transaction_type === 'out' ? 'destructive' : 'secondary'
                      }>
                        {entry.transaction_type.toUpperCase()}
                      </Badge>
                    </TableCell>
                    <TableCell data-label="Change" className="text-right">
                      {entry.quantity_change > 0 ? (
                        <span className="text-green-600 flex items-center justify-end">
                          <ArrowUp className="w-3 h-3 mr-1" /> {entry.quantity_change}
                        </span>
                      ) : (
                        <span className="text-red-600 flex items-center justify-end">
                          <ArrowDown className="w-3 h-3 mr-1" /> {Math.abs(entry.quantity_change)}
                        </span>
                      )}
                    </TableCell>
                    <TableCell data-label="Balance" className="text-right font-mono font-medium">
                      {entry.running_balance}
                    </TableCell>
                  </TableRow>
                ))}
                {(!ledger || ledger.length === 0) && (
                  <TableRow>
                    <TableCell colSpan={4} className="text-center text-muted-foreground py-8">
                      No recent ledger history.
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
