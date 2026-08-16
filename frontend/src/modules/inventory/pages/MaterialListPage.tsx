import { useQuery } from "@tanstack/react-query"
import { useMemo, useState } from "react"
import { materialService } from "@/services/material.service"
import { Material } from "@/types/material.types"
import { DataTable } from "@/components/shared/DataTable"
import { PageHeader } from "@/components/layout/PageHeader"
import { StatusBadge } from "@/components/shared/StatusBadge"
import { TableSkeleton } from "@/components/shared/LoadingSkeleton"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { Plus, Replace, Upload } from "lucide-react"
import { Link, useNavigate, useSearchParams } from "react-router-dom"
import { ColumnDef } from "@tanstack/react-table"
import { usePermissions } from "@/hooks/usePermissions"
import { MaterialFormDrawer } from "../components/MaterialFormDrawer"
import { StockOperationDrawer } from "../components/StockOperationDrawer"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"

export default function MaterialListPage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const [searchQuery, setSearchQuery] = useState("")
  const { canWrite } = usePermissions()
  const navigate = useNavigate()
  
  const materialId = searchParams.get("materialId")
  const presetType = searchParams.get("presetType") as "raw" | "finished" | undefined
  const filter = searchParams.get("filter")
  const currentTab = searchParams.get("tab") || "raw"
  const isDrawerOpen = materialId !== null
  
  const operationMaterialId = searchParams.get("operation")
  const isOperationOpen = operationMaterialId !== null

  const setTab = (tab: string) => {
    setSearchParams(prev => {
      prev.set("tab", tab)
      return prev
    })
  }

  const handleCloseDrawer = () => {
    setSearchParams({})
  }

  const { data: materialsData, isLoading: isFetchingMaterials } = useQuery({
    queryKey: ["materials", searchQuery],
    queryFn: () => materialService.getMaterials({ 
      page: 1, 
      page_size: 100,
      query: searchQuery || undefined,
    }),
  })

  const { data: categories, isLoading: isFetchingCategories } = useQuery({
    queryKey: ["categories"],
    queryFn: () => materialService.getCategories(),
  })

  const { data: units, isLoading: isFetchingUnits } = useQuery({
    queryKey: ["units"],
    queryFn: () => materialService.getUnits(),
  })

  const isLoading = isFetchingMaterials || isFetchingCategories || isFetchingUnits;

  // Define columns for TanStack Table
  const columns = useMemo<ColumnDef<Material>[]>(() => [
    {
      accessorKey: "code",
      header: "Code",
      cell: ({ row }) => <span className="font-medium text-primary">{row.original.code}</span>,
    },
    {
      accessorKey: "name",
      header: "Material Name",
    },
    {
      id: "category_id",
      header: "Category",
      cell: ({ row }) => {
        const catId = row.original.category_id;
        const category = categories?.find(c => c.id === catId);
        return <span>{category?.name || "Uncategorized"}</span>
      }
    },
    {
      id: "current_stock",
      header: "Stock",
      cell: ({ row }) => {
        const product = row.original
        const qty = Number(product.current_stock ?? 0)
        const isLow = product.is_low_stock
        const unit = units?.find(u => u.id === product.base_unit_id)
        const unitLabel = unit?.code || ""
        const reservedStock = Number(product.reserved_stock ?? 0)
        const availableStock = Math.max(0, qty - reservedStock)
        return (
          <div className="flex flex-col">
            <div className="flex items-center gap-2">
              <span className={isLow ? "text-destructive font-medium" : ""}>
                {qty} {unitLabel}
              </span>
              {isLow && <StatusBadge status="low-stock" label="Low" />}
            </div>
            {reservedStock > 0 && (
              <span className="text-xs text-muted-foreground">
                {reservedStock} quantity is reserved remaining is {availableStock}
              </span>
            )}
            {isLow && (
              <Link
                to="/procurement/purchase-orders"
                state={{ shortagePrefill: { lines: [{ material_id: product.id, quantity: product.reorder_level ?? 0 }] } }}
                className="text-xs text-blue-600 hover:underline"
                onClick={(e) => e.stopPropagation()}
              >
                Suggest PO
              </Link>
            )}
          </div>
        )
      },
    },
    {
      id: "actions",
      cell: ({ row }) => {
        return (
          <div className="flex gap-2 justify-end">
            <Button variant="ghost" size="sm" onClick={() => setSearchParams({ operation: row.original.id })}>
              <Replace className="mr-2 h-4 w-4" />
              Stock
            </Button>
            <Button variant="ghost" size="sm" onClick={() => setSearchParams({ materialId: row.original.id })}>
              Edit
            </Button>
          </div>
        )
      },
    },
  ], [setSearchParams, units, categories])

  const actionButtons = (
    <>
      {canWrite() && (
        <Button variant="outline" onClick={() => navigate("/inventory/material-onboarding")}>
          <Upload className="mr-2 h-4 w-4" />
          Upload Raw Materials
        </Button>
      )}
      {canWrite() && (
        <div className="flex gap-2">
          <Button onClick={() => setSearchParams({ materialId: "new", presetType: "raw" })}>
            <Plus className="mr-2 h-4 w-4" />
            Add Raw Material
          </Button>
          <Button variant="secondary" onClick={() => setSearchParams({ materialId: "new", presetType: "finished" })}>
            <Plus className="mr-2 h-4 w-4" />
            Add Finished Good
          </Button>
        </div>
      )}
    </>
  )

  const allItems = materialsData?.items || []
  
  const filteredItems = useMemo(() => {
    return allItems.filter(material => {
      // First apply low-stock filter if active
      if (filter === "low-stock" && !material.is_low_stock) {
        return false
      }
      
      // Then apply tab filter
      const type = (material.material_type || "").toLowerCase()
      if (currentTab === "finished") {
        return type.includes("finish") || type === "fg" || type === "finished"
      } else {
        // raw or semi_finished
        return !type.includes("finish") || type === "semi_finished"
      }
    })
  }, [allItems, filter, currentTab])

  return (
    <div className="w-full space-y-6">
      <PageHeader 
        title="Materials Catalog" 
        description="Manage your base inventory catalog, raw materials, and components."
        action={actionButtons}
      />

      {/* Search Input */}
      <div className="flex gap-2">
        <div className="flex-1 max-w-md">
          <input
            type="text"
            placeholder="Search by code or name..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full px-3 py-2 border border-input rounded-md bg-background text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
          />
        </div>
      </div>

      {isLoading ? (
        <TableSkeleton rows={8} />
      ) : (
        <Tabs value={currentTab} onValueChange={setTab} className="w-full">
          <TabsList className="mb-4">
            <TabsTrigger value="raw">Raw & Semi-Finished</TabsTrigger>
            <TabsTrigger value="finished">Finished Goods</TabsTrigger>
          </TabsList>
          
          <TabsContent value={currentTab} className="mt-0 border-none p-0">
            <div className="hidden md:block">
              <DataTable 
                columns={columns} 
                data={filteredItems}
              />
            </div>
            <div className="md:hidden grid gap-4 grid-cols-1 sm:grid-cols-2">
              {filteredItems.map((product) => {
                const qty = Number(product.current_stock ?? 0);
                const isLow = product.is_low_stock;
                const reservedStock = Number(product.reserved_stock ?? 0);
                
                return (
                  <Card key={product.id} className="cursor-pointer hover:bg-accent/50 transition-colors" onClick={() => setSearchParams({ materialId: product.id })}>
                    <CardContent className="p-4">
                      <div className="flex justify-between items-start mb-2">
                        <div>
                          <h3 className="font-medium text-base">{product.name}</h3>
                          <p className="text-xs text-muted-foreground font-mono">{product.code}</p>
                        </div>
                        <Button variant="ghost" size="sm" onClick={(e) => { e.stopPropagation(); setSearchParams({ operation: product.id }); }}>
                          <Replace className="h-4 w-4 mr-1"/> Stock
                        </Button>
                      </div>
                      <div className="flex justify-between items-end mt-4">
                        <span className="text-sm text-muted-foreground">
                          {categories?.find(c => c.id === product.category_id)?.name || "Uncategorized"}
                        </span>
                        <div className="flex flex-col items-end">
                          <div className="flex items-center gap-2">
                            <span className={isLow ? "text-destructive font-medium text-sm" : "text-sm font-medium"}>
                              {qty} {units?.find(u => u.id === product.base_unit_id)?.code || ""}
                            </span>
                            {isLow && (
                              <StatusBadge status="low-stock" label="Low" />
                            )}
                          </div>
                          {reservedStock > 0 && (
                            <span className="text-xs text-muted-foreground">
                              {reservedStock} quantity is reserved remaining is {Math.max(0, qty - reservedStock)}
                            </span>
                          )}
                          {isLow && (
                            <Link
                              to="/procurement/purchase-orders"
                              state={{ shortagePrefill: { lines: [{ material_id: product.id, quantity: product.reorder_level ?? 0 }] } }}
                              className="text-xs text-blue-600 hover:underline"
                              onClick={(e) => e.stopPropagation()}
                            >
                              Suggest PO
                            </Link>
                          )}
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                )
              })}
            </div>
          </TabsContent>
        </Tabs>
      )}
      
      <MaterialFormDrawer 
        open={isDrawerOpen} 
        onClose={handleCloseDrawer} 
        materialId={materialId} 
        presetType={presetType}
      />

      <StockOperationDrawer
        open={isOperationOpen}
        onClose={handleCloseDrawer}
        materialId={operationMaterialId}
      />
    </div>
  )
}
