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
import { useNavigate, useSearchParams } from "react-router-dom"
import { ColumnDef } from "@tanstack/react-table"
import { usePermissions } from "@/hooks/usePermissions"
import { MaterialFormDrawer } from "../components/MaterialFormDrawer"
import { StockOperationDrawer } from "../components/StockOperationDrawer"

export default function MaterialListPage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const [searchQuery, setSearchQuery] = useState("")
  const { canWrite } = usePermissions()
  const navigate = useNavigate()
  
  const materialId = searchParams.get("materialId")
  const filter = searchParams.get("filter")
  const isDrawerOpen = materialId !== null
  
  const operationMaterialId = searchParams.get("operation")
  const isOperationOpen = operationMaterialId !== null

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
        const qty = product.current_stock ?? 0
        const isLow = product.is_low_stock
        const unit = units?.find(u => u.id === product.base_unit_id)
        return (
          <div className="flex items-center gap-2">
            <span className={isLow ? "text-destructive font-medium" : ""}>
              {qty} {unit?.code || ""}
            </span>
            {isLow && <StatusBadge status="low-stock" label="Low" />}
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
  ], [setSearchParams])

  const actionButtons = (
    <>
      {canWrite() && (
        <Button variant="outline" onClick={() => navigate("/inventory/material-onboarding")}>
          <Upload className="mr-2 h-4 w-4" />
          Upload Raw Materials
        </Button>
      )}
      {canWrite() && (
        <Button onClick={() => setSearchParams({ materialId: "new" })}>
          <Plus className="mr-2 h-4 w-4" />
          Add Material
        </Button>
      )}
    </>
  )

  const items = (materialsData?.items || []).filter((material) =>
    filter === "low-stock" ? material.is_low_stock : true
  )

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
        <>
          <div className="hidden md:block">
            <DataTable 
              columns={columns} 
              data={items}
            />
          </div>
          <div className="md:hidden grid gap-4 grid-cols-1 sm:grid-cols-2">
            {items.map((product) => {
              const qty = product.current_stock ?? 0;
              const isLow = product.is_low_stock;
              
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
                      <div className="flex items-center gap-2">
                        <span className={isLow ? "text-destructive font-medium text-sm" : "text-sm font-medium"}>
                          {qty} {units?.find(u => u.id === product.base_unit_id)?.code || ""}
                        </span>
                        {isLow && (
                          <StatusBadge status="low-stock" label="Low" />
                        )}
                      </div>
                    </div>
                  </CardContent>
                </Card>
              )
            })}
          </div>
        </>
      )}
      
      <MaterialFormDrawer 
        open={isDrawerOpen} 
        onClose={handleCloseDrawer} 
        materialId={materialId} 
      />

      <StockOperationDrawer
        open={isOperationOpen}
        onClose={handleCloseDrawer}
        materialId={operationMaterialId}
      />
    </div>
  )
}
