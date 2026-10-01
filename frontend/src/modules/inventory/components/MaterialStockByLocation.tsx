import { useQuery } from "@tanstack/react-query"
import { materialService } from "@/services/material.service"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Skeleton } from "@/components/ui/skeleton"
import { Package, Warehouse, Building2, AlertCircle } from "lucide-react"
import { Link } from "react-router-dom"

interface StockLocation {
  location_id: string
  location_name: string
  location_type: string
  location_code?: string
  quantity: number
  stock_status: string
  vendor_name?: string
  subcontract_orders?: Array<{
    order_id: string
    order_number: string
    supplier_name: string
    issued_date: string
    status: string
  }>
}

interface StockByLocationData {
  material_id: string
  material_code: string
  material_name: string
  total_stock: number
  warehouse_stock: number
  subcontractor_stock: number
  reserved_stock: number
  available_stock: number
  locations: StockLocation[]
}

async function fetchStockByLocation(materialId: string): Promise<StockByLocationData> {
  return materialService.getMaterialStockByLocation(materialId)
}

interface MaterialStockByLocationProps {
  materialId: string
}

export function MaterialStockByLocation({ materialId }: MaterialStockByLocationProps) {
  const { data, isLoading, error } = useQuery({
    queryKey: ['material-stock-by-location', materialId],
    queryFn: () => fetchStockByLocation(materialId),
  })

  if (isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-32 w-full" />
        <Skeleton className="h-48 w-full" />
      </div>
    )
  }

  if (error) {
    return (
      <Card>
        <CardContent className="p-6">
          <div className="flex items-center gap-2 text-destructive">
            <AlertCircle className="h-5 w-5" />
            <span>Failed to load stock information</span>
          </div>
        </CardContent>
      </Card>
    )
  }

  if (!data) return null

  const warehouseLocations = data.locations.filter(l => 
    ['warehouse', 'zone', 'rack', 'bin', 'production'].includes(l.location_type)
  )
  const subcontractorLocations = data.locations.filter(l => l.location_type === 'subcontractor')

  return (
    <div className="space-y-6">
      {/* Stock Summary */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Stock Summary</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div>
              <div className="text-sm text-muted-foreground mb-1">Total Stock</div>
              <div className="text-2xl font-bold">{data.total_stock.toFixed(2)}</div>
            </div>
            <div>
              <div className="text-sm text-muted-foreground mb-1">Warehouse</div>
              <div className="text-2xl font-bold text-green-600">{data.warehouse_stock.toFixed(2)}</div>
            </div>
            <div>
              <div className="text-sm text-muted-foreground mb-1">With Subcontractors</div>
              <div className="text-2xl font-bold text-amber-600">{data.subcontractor_stock.toFixed(2)}</div>
            </div>
            <div>
              <div className="text-sm text-muted-foreground mb-1">Available</div>
              <div className="text-2xl font-bold text-blue-600">{data.available_stock.toFixed(2)}</div>
            </div>
          </div>
          
          {data.subcontractor_stock > 0 && (
            <div className="mt-4 p-3 bg-amber-50 border border-amber-200 rounded-lg flex items-start gap-2">
              <AlertCircle className="h-5 w-5 text-amber-600 mt-0.5 flex-shrink-0" />
              <div className="text-sm">
                <span className="font-medium text-amber-900">
                  {data.subcontractor_stock.toFixed(2)} units with subcontractors
                </span>
                <p className="text-amber-700 mt-1">
                  These materials have been issued to vendors for processing and are not immediately available in your warehouse.
                </p>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Stock by Location */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Stock by Location</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-6">
            {/* Warehouse Locations */}
            {warehouseLocations.length > 0 && (
              <div>
                <h4 className="text-sm font-medium text-muted-foreground mb-3 flex items-center gap-2">
                  <Warehouse className="h-4 w-4" />
                  Warehouse Locations
                </h4>
                <div className="space-y-2">
                  {warehouseLocations.map(location => (
                    <div
                      key={location.location_id}
                      className="flex items-center justify-between p-3 border rounded-lg hover:bg-muted/50 transition-colors"
                    >
                      <div className="flex items-center gap-3">
                        <Package className="h-5 w-5 text-muted-foreground" />
                        <div>
                          <div className="font-medium">{location.location_name}</div>
                          <div className="text-xs text-muted-foreground capitalize">
                            {location.location_type}
                            {location.location_code && ` · ${location.location_code}`}
                          </div>
                        </div>
                      </div>
                      <div className="text-right">
                        <div className="font-semibold">{location.quantity.toFixed(2)}</div>
                        <Badge variant="outline" className="text-xs">
                          {location.stock_status}
                        </Badge>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Subcontractor Locations */}
            {subcontractorLocations.length > 0 && (
              <div>
                <h4 className="text-sm font-medium text-muted-foreground mb-3 flex items-center gap-2">
                  <Building2 className="h-4 w-4" />
                  Subcontractor Stock
                </h4>
                <div className="space-y-3">
                  {subcontractorLocations.map(location => (
                    <div
                      key={location.location_id}
                      className="border rounded-lg p-4 bg-amber-50/50 border-amber-200"
                    >
                      <div className="flex items-start justify-between mb-3">
                        <div className="flex items-start gap-3">
                          <Building2 className="h-5 w-5 text-amber-600 mt-0.5" />
                          <div>
                            <div className="font-medium text-amber-900">
                              {location.vendor_name || location.location_name}
                            </div>
                            <div className="text-xs text-amber-700 mt-0.5">
                              Subcontractor Location
                            </div>
                          </div>
                        </div>
                        <div className="text-right">
                          <div className="text-xl font-bold text-amber-900">
                            {location.quantity.toFixed(2)}
                          </div>
                          <Badge variant="outline" className="text-xs border-amber-300">
                            {location.stock_status}
                          </Badge>
                        </div>
                      </div>

                      {/* Subcontract Orders */}
                      {location.subcontract_orders && location.subcontract_orders.length > 0 && (
                        <div className="mt-3 pt-3 border-t border-amber-200">
                          <div className="text-xs font-medium text-amber-900 mb-2">
                            Related Subcontract Orders:
                          </div>
                          <div className="space-y-1">
                            {location.subcontract_orders.map(order => (
                              <Link
                                key={order.order_id}
                                to={`/procurement/subcontract-orders/${order.order_id}`}
                                className="block text-xs text-amber-700 hover:text-amber-900 hover:underline"
                              >
                                <div className="flex items-center justify-between">
                                  <span>📋 {order.order_number}</span>
                                  <span className="text-amber-600">
                                    {new Date(order.issued_date).toLocaleDateString()}
                                  </span>
                                </div>
                              </Link>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* No Stock */}
            {data.locations.length === 0 && (
              <div className="text-center py-8 text-muted-foreground">
                <Package className="h-12 w-12 mx-auto mb-2 opacity-50" />
                <p>No stock available at any location</p>
              </div>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
