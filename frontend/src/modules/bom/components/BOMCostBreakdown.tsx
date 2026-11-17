import { useState } from "react"
import { useQuery } from "@tanstack/react-query"
import {
  IndianRupee, RefreshCw, Loader2, AlertCircle, TrendingUp, Package2, Settings2,
  Wrench, ChevronDown, ChevronUp, AlertTriangle,
} from "lucide-react"
import { bomService } from "@/services/bom.service"
import { BOM, BOMTreeNode } from "@/modules/bom/types/bom.types"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Alert, AlertDescription } from "@/components/ui/alert"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { formatCurrency } from "@/utils/currency"

interface BOMCostBreakdownProps {
  bom: BOM
}

export function BOMCostBreakdown({ bom }: BOMCostBreakdownProps) {
  const [maxDepth] = useState(20)
  const [refreshKey, setRefreshKey] = useState(0)
  const [expandMaterials, setExpandMaterials] = useState(true)
  const [expandOperations, setExpandOperations] = useState(false)

  const { data, isLoading, isFetching, isError, error, refetch } = useQuery({
    queryKey: ["bom-cost", bom.id, maxDepth, refreshKey],
    queryFn: () => bomService.getBOMCost(bom.id, maxDepth),
    staleTime: 60_000,
    retry: 1,
  })

  const { data: treeData, isLoading: treeLoading, refetch: refetchTree } = useQuery({
    queryKey: ["bom-tree", bom.id, maxDepth, refreshKey],
    queryFn: () => bomService.getBOMTree(bom.id, { max_depth: maxDepth }),
    staleTime: 60_000,
    retry: 1,
  })

  const { data: operationsList } = useQuery({
    queryKey: ["operations"],
    queryFn: bomService.getOperations,
    staleTime: 60_000,
  })

  const { data: workstationsList } = useQuery({
    queryKey: ["workstations"],
    queryFn: bomService.getWorkstations,
    staleTime: 60_000,
  })

  const isRefreshing = isFetching && !isLoading

  const errorMsg =
    (error as any)?.response?.data?.detail ||
    (error as any)?.message ||
    "Failed to calculate cost"

  // Immediate branches contribute once; descendants explain each child total.
  const getMaterialNodes = (node: BOMTreeNode): BOMTreeNode[] => node.children ?? []

  // Decide whether to show the total — only when is_complete
  const isComplete = data?.is_complete !== false   // true or undefined (old API) → show
  const hasMissingCosts = data?.missing_costs && data.missing_costs.length > 0
  const sym = data?.currency_symbol || "₹"

  // Use the backend total directly (it is 0 when incomplete)
  const displayTotal = isComplete ? (data?.total_cost ?? 0) : null
  // Making cost from new field, with zero fallback for old API responses
  const makingCost = data?.making_cost ?? 0

  return (
    <div className="space-y-4">
      {/* Header row */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2 text-muted-foreground text-sm">
          <IndianRupee className="w-4 h-4" />
          <span>Standard Cost Rollup</span>
          {isRefreshing && (
            <span className="flex items-center gap-1 text-xs text-primary">
              <Loader2 className="w-3 h-3 animate-spin" />
              Recalculating...
            </span>
          )}
        </div>
        <Button
          variant="ghost"
          size="sm"
          className="h-8 gap-1.5 text-xs"
          disabled={isFetching}
          onClick={() => {
            setRefreshKey((k) => k + 1)
            refetch()
            refetchTree()
          }}
        >
          <RefreshCw className={`w-3 h-3 ${isFetching ? "animate-spin" : ""}`} />
          Recalculate
        </Button>
      </div>

      {/* Error state */}
      {isError && (
        <Alert variant="destructive">
          <AlertCircle className="w-4 h-4" />
          <AlertDescription>{errorMsg}</AlertDescription>
        </Alert>
      )}

      {/* Loading state */}
      {isLoading ? (
        <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
          {[1, 2, 3, 4].map((i) => (
            <Skeleton key={i} className="h-24 rounded-xl" />
          ))}
        </div>
      ) : data ? (
        <>
          {/* Incomplete cost banner — shown when any component cost is missing */}
          {hasMissingCosts && (
            <Alert className="border-amber-300 bg-amber-50 text-amber-800">
              <AlertTriangle className="w-4 h-4 text-amber-600" />
              <AlertDescription className="space-y-1">
                <p className="font-medium">Incomplete Cost — total cannot be calculated</p>
                <p className="text-xs text-amber-700">
                  Resolve the following material, child BOM, operation or UOM issues to complete this cost rollup.
                </p>
                <ul className="mt-1.5 space-y-0.5">
                  {data.missing_costs!.map((m, i) => (
                    <li key={i} className="text-xs font-mono flex items-center gap-1.5">
                      <span className="inline-block w-1.5 h-1.5 rounded-full bg-amber-500 shrink-0" />
                      <span className="font-semibold">{m.code || m.component_id.slice(0, 8)}</span>
                      {m.name && <span className="text-amber-700">— {m.name}</span>}
                      <span className="text-amber-600 capitalize">({m.component_type})</span>
                      {m.message && <span>{m.message}</span>}
                    </li>
                  ))}
                </ul>
              </AlertDescription>
            </Alert>
          )}

          {/* Summary cards — 4 categories */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            {/* Total */}
            <Card className={`col-span-2 sm:col-span-1 ${isComplete ? "border-green-100 bg-gradient-to-br from-green-50 to-green-100/30" : "border-amber-200 bg-amber-50/40"}`}>
              <CardHeader className="pb-1 pt-3 px-4">
                <CardTitle className={`text-xs font-medium flex items-center gap-1.5 ${isComplete ? "text-green-700" : "text-amber-700"}`}>
                  <TrendingUp className="w-3.5 h-3.5" />
                  Total Standard Cost
                </CardTitle>
              </CardHeader>
              <CardContent className="px-4 pb-3">
                {displayTotal !== null ? (
                  <div className={`text-2xl font-bold truncate ${isComplete ? "text-green-800" : "text-amber-800"}`}>
                    {formatCurrency(displayTotal, sym)}
                  </div>
                ) : (
                  <div className="flex items-center gap-1.5 text-amber-700 font-semibold text-sm">
                    <AlertTriangle className="w-4 h-4" />
                    Incomplete
                  </div>
                )}
                <p className="text-xs text-muted-foreground mt-1">
                  {isComplete ? "All levels included" : "Missing component costs"}
                </p>
              </CardContent>
            </Card>

            {/* Materials */}
            <Card className="hover:border-primary/30 transition-colors">
              <CardHeader className="pb-1 pt-3 px-4">
                <CardTitle className="text-xs text-muted-foreground font-medium flex items-center gap-1.5">
                  <Package2 className="w-3.5 h-3.5" />
                  Materials
                </CardTitle>
              </CardHeader>
              <CardContent className="px-4 pb-3">
                <div className="text-lg font-bold text-amber-700 truncate">
                  {formatCurrency(data.material_cost, sym)}
                </div>
                <p className="text-xs text-muted-foreground mt-1">Rolled-up components</p>
              </CardContent>
            </Card>

            {/* Outside Making */}
            <Card className="hover:border-primary/30 transition-colors">
              <CardHeader className="pb-1 pt-3 px-4">
                <CardTitle className="text-xs text-muted-foreground font-medium flex items-center gap-1.5">
                  <Wrench className="w-3.5 h-3.5" />
                  Outside Making
                </CardTitle>
              </CardHeader>
              <CardContent className="px-4 pb-3">
                <div className="text-lg font-bold text-purple-700 truncate">
                  {formatCurrency(makingCost, sym)}
                </div>
                <p className="text-xs text-muted-foreground mt-1">
                  {makingCost > 0 ? "Per piece charge" : "Not configured"}
                </p>
              </CardContent>
            </Card>

            {/* Internal Operations */}
            <Card className="hover:border-primary/30 transition-colors">
              <CardHeader className="pb-1 pt-3 px-4">
                <CardTitle className="text-xs text-muted-foreground font-medium flex items-center gap-1.5">
                  <Settings2 className="w-3.5 h-3.5" />
                  Operations
                </CardTitle>
              </CardHeader>
              <CardContent className="px-4 pb-3">
                <div className="text-lg font-bold text-blue-700 truncate">
                  {formatCurrency(data.operation_cost, sym)}
                </div>
                <p className="text-xs text-muted-foreground mt-1">Routing & workstations</p>
              </CardContent>
            </Card>
          </div>

          {/* Reconciliation row — only when complete */}
          {isComplete && displayTotal !== null && (
            <div className="flex items-center gap-2 text-xs text-muted-foreground px-1">
              <span className="font-mono">
                {formatCurrency(data.material_cost, sym)} materials
                {" + "}
                {formatCurrency(makingCost, sym)} making
                {" + "}
                {formatCurrency(data.operation_cost, sym)} ops
                {" = "}
              </span>
              <span className="font-semibold text-foreground">
                {formatCurrency(displayTotal, sym)} total
              </span>
            </div>
          )}

          {/* Material breakdown table */}
          {!treeLoading && treeData && (
            <div className="space-y-3 border-t pt-4">
              <button
                onClick={() => setExpandMaterials(!expandMaterials)}
                className="w-full flex items-center justify-between p-3 bg-muted/40 hover:bg-muted/60 transition-colors rounded-lg"
              >
                <div className="flex items-center gap-2 font-medium text-sm">
                  <Package2 className="w-4 h-4 text-amber-600" />
                  <span>Component Cost Breakdown</span>
                  <span className="text-xs text-muted-foreground">
                    ({getMaterialNodes(treeData).length} items)
                  </span>
                </div>
                {expandMaterials ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
              </button>

              {expandMaterials && (
                <div className="rounded-lg border overflow-hidden">
                  <div className="overflow-x-auto min-w-0">
                    <Table className="text-sm">
                      <TableHeader className="bg-muted/50">
                        <TableRow>
                          <TableHead className="text-xs">Item</TableHead>
                          <TableHead className="text-xs text-right">Qty</TableHead>
                          <TableHead className="text-xs text-right">Unit Cost</TableHead>
                          <TableHead className="text-xs text-right">Total Cost</TableHead>
                          <TableHead className="text-xs text-right">% of Materials</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {getMaterialNodes(treeData)
                          .sort((a, b) => (b.cost || 0) - (a.cost || 0))
                          .map((node) => {
                            const itemCost = node.cost || 0
                            // % of material subtotal (not total) for clarity
                            const pct =
                              Number(data.material_cost) > 0
                                ? ((itemCost / data.material_cost) * 100).toFixed(1)
                                : "0"
                            const unitCost = node.quantity > 0 ? itemCost / node.quantity : 0
                            return (
                              <TableRow key={node.line_id ?? node.id} className="hover:bg-muted/30 transition-colors">
                                <TableCell className="text-xs font-medium">
                                  <div className="flex flex-col gap-0.5">
                                    <span>{node.name}</span>
                                    <span className="text-xs text-muted-foreground">{node.code}</span>
                                    {node.cost_basis === "CHILD_BOM" && <span className="text-xs text-muted-foreground">Child BOM total; includes its materials, operations and making charges once.</span>}
                                    {node.is_complete === false && <span className="text-xs text-amber-700">{node.message ?? "Incomplete child cost"}</span>}
                                  </div>
                                </TableCell>
                                <TableCell className="text-xs text-right">
                                  {node.quantity}{node.unit && ` ${node.unit}`}
                                </TableCell>
                                <TableCell className="text-xs text-right">
                                  {node.is_complete === false || node.cost == null ? "—" : `${sym} ${unitCost.toFixed(4)}`}
                                </TableCell>
                                <TableCell className="text-xs text-right font-semibold">
                                  {node.is_complete === false || node.cost == null ? "Incomplete" : formatCurrency(itemCost, sym)}
                                </TableCell>
                                <TableCell className="text-xs text-right text-amber-600">
                                  {node.is_complete === false || node.cost == null ? "—" : `${pct}%`}
                                </TableCell>
                              </TableRow>
                            )
                          })}
                      </TableBody>
                    </Table>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Operations breakdown */}
          {Number(data.operation_cost) > 0 && (
            <div className="space-y-3 border-t pt-4">
              <button
                onClick={() => setExpandOperations(!expandOperations)}
                className="w-full flex items-center justify-between p-3 bg-muted/40 hover:bg-muted/60 transition-colors rounded-lg"
              >
                <div className="flex items-center gap-2 font-medium text-sm">
                  <Settings2 className="w-4 h-4 text-blue-600" />
                  <span>Operation Cost Breakdown</span>
                </div>
                {expandOperations ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
              </button>

              {expandOperations && (
                <div className="rounded-lg border overflow-hidden">
                  <div className="overflow-x-auto min-w-0">
                    <Table className="text-sm">
                      <TableHeader className="bg-muted/50">
                        <TableRow>
                          <TableHead className="text-xs">Operation</TableHead>
                          <TableHead className="text-xs text-right">Time (min)</TableHead>
                          <TableHead className="text-xs text-right">Rate/hr</TableHead>
                          <TableHead className="text-xs text-right">Cost</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {(bom.operations || []).map((bomOp) => {
                          const op = operationsList?.find((o) => o.id === bomOp.operation_id)
                          const ws = workstationsList?.find((w) => w.id === op?.workstation_id)
                          const totalTime = (op?.setup_time || 0) + (op?.run_time || 0)
                          const hourlyRate = ws?.hourly_rate || 0
                          const opCost = totalTime * (hourlyRate / 60)
                          return (
                            <TableRow key={bomOp.id} className="hover:bg-muted/30 transition-colors">
                              <TableCell className="text-xs font-medium">
                                <div className="flex flex-col gap-0.5">
                                  <span>{op ? op.name : "Unknown Operation"}</span>
                                  <span className="text-xs text-muted-foreground">
                                    {ws ? ws.name : "Unknown Workstation"}
                                  </span>
                                </div>
                              </TableCell>
                              <TableCell className="text-xs text-right text-muted-foreground">{totalTime}</TableCell>
                              <TableCell className="text-xs text-right text-muted-foreground">
                                {sym} {hourlyRate.toFixed(2)}
                              </TableCell>
                              <TableCell className="text-xs text-right font-semibold">
                                {formatCurrency(opCost, sym)}
                              </TableCell>
                            </TableRow>
                          )
                        })}
                        {(!bom.operations || bom.operations.length === 0) && (
                          <TableRow>
                            <TableCell colSpan={4} className="text-center text-muted-foreground py-4 text-xs">
                              No direct operations attached to this BOM.
                            </TableCell>
                          </TableRow>
                        )}
                      </TableBody>
                    </Table>
                  </div>
                </div>
              )}
            </div>
          )}
        </>
      ) : null}
    </div>
  )
}
