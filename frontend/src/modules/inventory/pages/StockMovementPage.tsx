import { useMemo, useState } from "react"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { PageHeader } from "@/components/layout/PageHeader"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Textarea } from "@/components/ui/textarea"
import { toast } from "@/hooks/use-toast"
import { materialService } from "@/services/material.service"
import { ArrowDownToLine, ArrowUpToLine, ArrowRightLeft, Scale } from "lucide-react"
import type { TransactionType } from "@/types/material.types"

type MovementDraft = {
  material_id: string
  quantity: string
  from_location_id: string
  to_location_id: string
  remarks: string
}

const emptyDraft: MovementDraft = {
  material_id: "",
  quantity: "",
  from_location_id: "",
  to_location_id: "",
  remarks: "",
}

export default function StockMovementPage() {
  const queryClient = useQueryClient()
  const [activeType, setActiveType] = useState<TransactionType>("in")
  const [draft, setDraft] = useState<MovementDraft>(emptyDraft)

  const { data: materialsData, isLoading: isLoadingMaterials } = useQuery({
    queryKey: ["materials", "movement-picker"],
    queryFn: () => materialService.getMaterials({ page: 1, page_size: 500 }),
  })

  const { data: locations } = useQuery({
    queryKey: ["locations"],
    queryFn: () => materialService.getLocations(),
  })

  const materials = materialsData?.items || []
  const selectedMaterial = useMemo(
    () => materials.find((material) => material.id === draft.material_id),
    [materials, draft.material_id]
  )

  const mutation = useMutation({
    mutationFn: () => {
      const quantity = Number(draft.quantity)
      return materialService.createTransaction({
        material_id: draft.material_id,
        transaction_type: activeType,
        quantity,
        new_quantity: activeType === "adjustment" ? quantity : undefined,
        from_location_id: activeType === "out" || activeType === "transfer" ? draft.from_location_id || null : null,
        to_location_id: activeType === "in" || activeType === "transfer" ? draft.to_location_id || null : null,
        remarks: draft.remarks || null,
      })
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["materials"] })
      queryClient.invalidateQueries({ queryKey: ["transactions"] })
      queryClient.invalidateQueries({ queryKey: ["realtimeStock"] })
      queryClient.invalidateQueries({ queryKey: ["stockLedger"] })
      setDraft(emptyDraft)
      toast({ title: "Stock movement recorded", description: "Inventory balances are updated from the backend." })
    },
    onError: (error: any) => {
      toast({
        title: "Movement failed",
        description: error?.response?.data?.detail || error?.message || "Unable to record stock movement.",
        variant: "destructive",
      })
    },
  })

  const canSubmit =
    Boolean(draft.material_id) &&
    Number(draft.quantity) > 0 &&
    (activeType !== "transfer" || Boolean(draft.from_location_id && draft.to_location_id))

  const renderForm = (type: TransactionType) => (
    <Card>
      <CardHeader>
        <CardTitle>
          {type === "in" ? "Receive Goods" : type === "out" ? "Issue Materials" : type === "adjustment" ? "Stock Reconciliation" : "Transfer Stock"}
        </CardTitle>
        <CardDescription>
          {type === "in"
            ? "Add stock into inventory for a selected item."
            : type === "out"
              ? "Consume or dispatch stock from inventory."
              : type === "adjustment"
                ? "Reconcile actual physical count. This overrides the current system balance."
                : "Move stock between warehouse locations."}
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid gap-4 sm:grid-cols-2">
          <div className="space-y-2 sm:col-span-2">
            <Label>Item</Label>
            <Select
              value={draft.material_id}
              onValueChange={(value) => setDraft((current) => ({ ...current, material_id: value }))}
              disabled={isLoadingMaterials}
            >
              <SelectTrigger>
                <SelectValue placeholder="Search by item code or name" />
              </SelectTrigger>
              <SelectContent>
                {materials.map((material) => (
                  <SelectItem key={material.id} value={material.id}>
                    {material.code} - {material.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            {selectedMaterial && (
              <p className="text-xs text-slate-500">
                Available: {selectedMaterial.available_stock} | Reserved: {selectedMaterial.reserved_stock}
              </p>
            )}
          </div>

          <div className="space-y-2">
            <Label>{type === "adjustment" ? "New Stock Quantity" : "Quantity"}</Label>
            <Input
              type="number"
              min="0"
              step="0.0001"
              placeholder="0"
              value={draft.quantity}
              onChange={(event) => setDraft((current) => ({ ...current, quantity: event.target.value }))}
            />
          </div>

          {(type === "out" || type === "transfer") && (
            <div className="space-y-2">
              <Label>From Location</Label>
              <Select
                value={draft.from_location_id}
                onValueChange={(value) => setDraft((current) => ({ ...current, from_location_id: value }))}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select source" />
                </SelectTrigger>
                <SelectContent>
                  {locations?.map((location) => (
                    <SelectItem key={location.id} value={location.id}>
                      {location.code ? `${location.code} - ` : ""}{location.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          )}

          {(type === "in" || type === "transfer") && (
            <div className="space-y-2">
              <Label>To Location</Label>
              <Select
                value={draft.to_location_id}
                onValueChange={(value) => setDraft((current) => ({ ...current, to_location_id: value }))}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select destination" />
                </SelectTrigger>
                <SelectContent>
                  {locations?.map((location) => (
                    <SelectItem key={location.id} value={location.id}>
                      {location.code ? `${location.code} - ` : ""}{location.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          )}

          <div className="space-y-2 sm:col-span-2">
            <Label>Remarks</Label>
            <Textarea
              value={draft.remarks}
              onChange={(event) => setDraft((current) => ({ ...current, remarks: event.target.value }))}
              placeholder="Reason, PO number, work order number, or receiving note"
            />
          </div>
        </div>
        <Button className="w-full sm:w-auto" disabled={!canSubmit || mutation.isPending} onClick={() => mutation.mutate()}>
          {mutation.isPending ? "Recording..." : "Record Movement"}
        </Button>
      </CardContent>
    </Card>
  )

  return (
    <div className="max-w-4xl space-y-6">
      <PageHeader
        title="Stock Movements"
        description="Receive, issue, or transfer real inventory items from the backend."
      />

      <Tabs
        value={activeType}
        onValueChange={(value) => {
          setActiveType(value as TransactionType)
          setDraft(emptyDraft)
        }}
        className="w-full"
      >
        <TabsList className="mb-8 grid w-full max-w-2xl grid-cols-4">
          <TabsTrigger value="in">
            <ArrowDownToLine className="mr-2 h-4 w-4" />
            Receive
          </TabsTrigger>
          <TabsTrigger value="out">
            <ArrowUpToLine className="mr-2 h-4 w-4" />
            Issue
          </TabsTrigger>
          <TabsTrigger value="transfer">
            <ArrowRightLeft className="mr-2 h-4 w-4" />
            Transfer
          </TabsTrigger>
          <TabsTrigger value="adjustment">
            <Scale className="mr-2 h-4 w-4" />
            Reconcile
          </TabsTrigger>
        </TabsList>

        <TabsContent value="in">{renderForm("in")}</TabsContent>
        <TabsContent value="out">{renderForm("out")}</TabsContent>
        <TabsContent value="transfer">{renderForm("transfer")}</TabsContent>
        <TabsContent value="adjustment">{renderForm("adjustment")}</TabsContent>
      </Tabs>
    </div>
  )
}
