import { useState, useEffect } from "react"
import { useQuery } from "@tanstack/react-query"
import { useNavigate } from "react-router-dom"
import { PackageSearch, Plus, Search, AlertCircle } from "lucide-react"
import { productService } from "@/services/product.service"
import { materialService } from "@/services/material.service"
import { usePermissions } from "@/hooks/usePermissions"
import { useToast } from "@/hooks/use-toast"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Badge } from "@/components/ui/badge"
import ResponsiveDataList from "@/components/shared/ResponsiveDataList"

export default function ProductTemplateListPage() {
  const navigate = useNavigate()
  const { hasRole } = usePermissions()
  const { toast } = useToast()
  const canEdit = hasRole(["ADMIN", "MANAGER"])

  const [query, setQuery] = useState("")
  const [debouncedQuery, setDebouncedQuery] = useState("")
  const [page, setPage] = useState(1)

  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedQuery(query)
      setPage(1)
    }, 400)
    return () => clearTimeout(handler)
  }, [query])

  const { data, isLoading, error, isError } = useQuery({
    queryKey: ["products", "templates", debouncedQuery, page],
    queryFn: () => productService.getTemplates({ query: debouncedQuery, page, page_size: 20 }),
    staleTime: 10_000,
  })

  const { data: categories } = useQuery({
    queryKey: ["categories"],
    queryFn: materialService.getCategories,
    staleTime: 60_000,
  })

  const getCategoryName = (id: string | null | undefined) => {
    if (!id || !categories) return "—"
    const cat = categories.find(c => c.id === id)
    return cat ? cat.name : "—"
  }

  useEffect(() => {
    if (isError && error && !isLoading) {
      toast({
        title: "Error loading templates",
        description: error instanceof Error ? error.message : "Failed to load product templates. Please try again.",
        variant: "destructive",
      })
    }
  }, [isError, error, isLoading, toast])

  return (
    <div className="space-y-6">
      <div className="flex flex-col items-start justify-between gap-4 sm:flex-row sm:items-center">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Finished Goods</h1>
          <p className="text-muted-foreground">
            Manage sellable product templates here. Raw materials stay under inventory for BOM and procurement planning.
          </p>
        </div>
        {canEdit && (
          <Button onClick={() => navigate("/products/new")}>
            <Plus className="mr-2 h-4 w-4" />
            New Template
          </Button>
        )}
      </div>

      <div className="flex flex-wrap gap-2">
        <Button size="sm">Finished Goods</Button>
        <Button variant="outline" size="sm" onClick={() => navigate("/inventory/materials")}>
          Raw Materials
        </Button>
      </div>

      <div className="flex items-center gap-2">
        <div className="relative max-w-sm flex-1">
          <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Search by code or name..."
            className="pl-8"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
        </div>
      </div>

      {isError ? (
        <div className="rounded-3xl border border-destructive/40 bg-destructive/5 p-4">
          <div className="flex max-w-md items-start gap-3">
            <AlertCircle className="mt-0.5 h-5 w-5 flex-shrink-0 text-destructive" />
            <div className="flex-1">
              <p className="font-medium text-destructive">Failed to load templates</p>
              <p className="mt-1 text-sm text-destructive/80">
                {error instanceof Error ? error.message : "An error occurred while loading product templates."}
              </p>
              <Button variant="outline" size="sm" onClick={() => window.location.reload()} className="mt-3">
                Retry
              </Button>
            </div>
          </div>
        </div>
      ) : isLoading ? (
        <div className="rounded-3xl border bg-card py-10 text-center text-muted-foreground">
          Loading templates...
        </div>
      ) : data?.items.length === 0 ? (
        <div className="rounded-3xl border bg-card py-12 text-center text-muted-foreground">
          <PackageSearch className="mx-auto mb-3 h-8 w-8 opacity-50" />
          <p>No product templates found.</p>
        </div>
      ) : (
        <ResponsiveDataList
          data={data?.items ?? []}
          getRowKey={(tpl) => tpl.id}
          columns={[
            { key: "code", header: "Code", cell: (tpl) => <span className="font-mono">{tpl.code}</span> },
            { key: "name", header: "Name", cell: (tpl) => <span className="font-medium">{tpl.name}</span> },
            { key: "category", header: "Category", cell: (tpl) => <span className="text-muted-foreground">{getCategoryName(tpl.category_id)}</span> },
            {
              key: "status",
              header: "Status",
              cell: (tpl) => <Badge variant={tpl.is_active ? "outline" : "secondary"}>{tpl.is_active ? "Active" : "Inactive"}</Badge>,
            },
            {
              key: "actions",
              header: "Actions",
              headerClassName: "text-right",
              className: "text-right",
              cell: (tpl) => (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={(event) => {
                    event.stopPropagation()
                    navigate(`/products/${tpl.id}/edit`)
                  }}
                >
                  {canEdit ? "Edit" : "View"}
                </Button>
              ),
            },
          ]}
          onRowClick={(tpl) => navigate(`/products/${tpl.id}/edit`)}
          renderMobileCard={(tpl) => (
            <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm transition-all hover:shadow-md" onClick={() => navigate(`/products/${tpl.id}/edit`)}>
              <div className="flex items-start justify-between gap-3">
                <div>
                  <p className="font-mono text-sm text-slate-500">{tpl.code}</p>
                  <p className="mt-1 text-base font-semibold text-slate-900">{tpl.name}</p>
                </div>
                <Badge variant={tpl.is_active ? "outline" : "secondary"}>
                  {tpl.is_active ? "Active" : "Inactive"}
                </Badge>
              </div>
              <div className="mt-4 flex items-center justify-between gap-3 text-sm">
                <span className="text-slate-500">Category</span>
                <span className="text-slate-700">{getCategoryName(tpl.category_id)}</span>
              </div>
              <div className="mt-4">
                <Button
                  variant="outline"
                  className="w-full"
                  onClick={(event) => {
                    event.stopPropagation()
                    navigate(`/products/${tpl.id}/edit`)
                  }}
                >
                  {canEdit ? "Edit template" : "View template"}
                </Button>
              </div>
            </div>
          )}
        />
      )}

      {data && data.total > data.page_size && (
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <p className="text-sm text-muted-foreground">
            Showing {(page - 1) * data.page_size + 1}–{Math.min(page * data.page_size, data.total)} of {data.total}
          </p>
          <div className="flex gap-2">
            <Button variant="outline" size="sm" disabled={page === 1} onClick={() => setPage((p) => Math.max(1, p - 1))}>
              Previous
            </Button>
            <Button variant="outline" size="sm" disabled={page * data.page_size >= data.total} onClick={() => setPage((p) => p + 1)}>
              Next
            </Button>
          </div>
        </div>
      )}
    </div>
  )
}
