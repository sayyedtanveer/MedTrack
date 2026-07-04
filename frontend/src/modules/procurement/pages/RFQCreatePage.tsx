import { useEffect, useState } from "react"
import { useNavigate } from "react-router-dom"
import { supplyChainApi } from "@/services/supply-chain.service"
import { materialService } from "@/services/material.service"
import type { Material } from "@/types/material.types"
import type { Supplier } from "@/services/supply-chain.service"
import { useToast } from "@/hooks/use-toast"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Checkbox } from "@/components/ui/checkbox"
import { Badge } from "@/components/ui/badge"
import { Plus, Trash2, FileText, Users } from "lucide-react"

type RFQLine = {
  material_id: string
  quantity: number
  description: string
}

export default function RFQCreatePage() {
  const navigate = useNavigate()
  const { toast } = useToast()

  const [title, setTitle] = useState("")
  const [deadline, setDeadline] = useState("")
  const [notes, setNotes] = useState("")
  const [lines, setLines] = useState<RFQLine[]>([
    { material_id: "", quantity: 1, description: "" },
  ])
  const [selectedSuppliers, setSelectedSuppliers] = useState<string[]>([])
  const [materials, setMaterials] = useState<Material[]>([])
  const [suppliers, setSuppliers] = useState<Supplier[]>([])
  const [submitting, setSubmitting] = useState(false)

  useEffect(() => {
    materialService.getMaterials({ page: 1, page_size: 300 }).then((m) => setMaterials(m.items))
    supplyChainApi.listSuppliers().then((r) => setSuppliers(r.data))
  }, [])

  const addLine = () =>
    setLines((prev) => [...prev, { material_id: "", quantity: 1, description: "" }])

  const removeLine = (idx: number) =>
    setLines((prev) => prev.filter((_, i) => i !== idx))

  const updateLine = <K extends keyof RFQLine>(idx: number, key: K, val: RFQLine[K]) =>
    setLines((prev) => prev.map((l, i) => (i === idx ? { ...l, [key]: val } : l)))

  const toggleSupplier = (id: string) =>
    setSelectedSuppliers((prev) =>
      prev.includes(id) ? prev.filter((s) => s !== id) : [...prev, id]
    )

  const handleSubmit = async () => {
    if (!lines.some((l) => l.material_id)) {
      toast({ title: "Add at least one material line", variant: "destructive" })
      return
    }
    if (selectedSuppliers.length === 0) {
      toast({ title: "Select at least one supplier", variant: "destructive" })
      return
    }
    setSubmitting(true)
    try {
      const res = await supplyChainApi.createRFQ({
        title: title || undefined,
        deadline: deadline || undefined,
        notes: notes || undefined,
        lines: lines
          .filter((l) => l.material_id)
          .map((l) => ({ ...l, quantity: Number(l.quantity) })),
        supplier_ids: selectedSuppliers,
      })
      toast({ title: `RFQ ${res.data.rfq_number} created` })
      navigate(`/procurement/rfq/${res.data.id}`)
    } catch (e: any) {
      toast({ title: e?.message ?? "Create failed", variant: "destructive" })
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="space-y-6 p-6 max-w-4xl mx-auto">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Create Request for Quotation</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Define materials needed, add suppliers, then send the RFQ for competitive pricing.
        </p>
      </div>

      {/* ── Header fields ── */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <FileText className="h-4 w-4" /> RFQ Details
          </CardTitle>
        </CardHeader>
        <CardContent className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="space-y-1.5">
            <Label htmlFor="rfq-title">Title (optional)</Label>
            <Input
              id="rfq-title"
              placeholder="e.g. Q2 Raw Material Sourcing"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
            />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="rfq-deadline">Quotation Deadline</Label>
            <Input
              id="rfq-deadline"
              type="date"
              value={deadline}
              onChange={(e) => setDeadline(e.target.value)}
            />
          </div>
          <div className="space-y-1.5 md:col-span-2">
            <Label htmlFor="rfq-notes">Notes</Label>
            <Textarea
              id="rfq-notes"
              placeholder="Terms, special requirements…"
              rows={3}
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
            />
          </div>
        </CardContent>
      </Card>

      {/* ── Material lines ── */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <div>
            <CardTitle className="text-base">Material Lines</CardTitle>
            <CardDescription>Specify what materials and quantities you need quoted.</CardDescription>
          </div>
          <Button id="rfq-add-line" size="sm" variant="outline" onClick={addLine}>
            <Plus className="h-4 w-4 mr-1" /> Add Line
          </Button>
        </CardHeader>
        <CardContent className="space-y-3">
          {lines.map((line, idx) => (
            <div key={idx} className="grid grid-cols-12 gap-3 items-end border rounded-lg p-3 bg-muted/30">
              <div className="col-span-5 space-y-1">
                <Label className="text-xs">Material</Label>
                <Select
                  value={line.material_id}
                  onValueChange={(v) => updateLine(idx, "material_id", v)}
                >
                  <SelectTrigger id={`rfq-line-mat-${idx}`}>
                    <SelectValue placeholder="Select material" />
                  </SelectTrigger>
                  <SelectContent>
                    {materials.map((m) => (
                      <SelectItem key={m.id} value={m.id}>
                        {m.code} — {m.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="col-span-2 space-y-1">
                <Label className="text-xs">Quantity</Label>
                <Input
                  id={`rfq-line-qty-${idx}`}
                  type="number"
                  min={0.01}
                  step={0.01}
                  value={line.quantity}
                  onChange={(e) => updateLine(idx, "quantity", Number(e.target.value))}
                />
              </div>
              <div className="col-span-4 space-y-1">
                <Label className="text-xs">Description / Spec (optional)</Label>
                <Input
                  id={`rfq-line-desc-${idx}`}
                  placeholder="Grade, dimensions…"
                  value={line.description}
                  onChange={(e) => updateLine(idx, "description", e.target.value)}
                />
              </div>
              <div className="col-span-1 flex justify-end">
                <Button
                  size="icon"
                  variant="ghost"
                  className="text-destructive hover:text-destructive"
                  disabled={lines.length === 1}
                  aria-label="Remove line"
                  onClick={() => removeLine(idx)}
                >
                  <Trash2 className="h-4 w-4" />
                </Button>
              </div>
            </div>
          ))}
        </CardContent>
      </Card>

      {/* ── Supplier selection ── */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <Users className="h-4 w-4" /> Invite Suppliers
            {selectedSuppliers.length > 0 && (
              <Badge variant="secondary">{selectedSuppliers.length} selected</Badge>
            )}
          </CardTitle>
          <CardDescription>Select one or more suppliers to receive this RFQ.</CardDescription>
        </CardHeader>
        <CardContent>
          {suppliers.length === 0 ? (
            <p className="text-sm text-muted-foreground">No active suppliers. Add suppliers first.</p>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
              {suppliers.map((s) => (
                <label
                  key={s.id}
                  htmlFor={`sup-${s.id}`}
                  className={`flex items-start gap-3 rounded-lg border p-3 cursor-pointer transition-colors hover:bg-accent ${
                    selectedSuppliers.includes(s.id) ? "border-primary bg-primary/5" : ""
                  }`}
                >
                  <Checkbox
                    id={`sup-${s.id}`}
                    checked={selectedSuppliers.includes(s.id)}
                    onCheckedChange={() => toggleSupplier(s.id)}
                    className="mt-0.5"
                  />
                  <div className="leading-tight">
                    <p className="font-medium text-sm">{s.name}</p>
                    <p className="text-xs text-muted-foreground">{s.code}</p>
                    {s.email && (
                      <p className="text-xs text-muted-foreground truncate max-w-[160px]">{s.email}</p>
                    )}
                  </div>
                </label>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* ── Actions ── */}
      <div className="flex gap-3 justify-end">
        <Button variant="outline" onClick={() => navigate("/procurement/rfq")}>
          Cancel
        </Button>
        <Button id="rfq-submit-btn" onClick={handleSubmit} disabled={submitting}>
          {submitting ? "Creating…" : "Create RFQ"}
        </Button>
      </div>
    </div>
  )
}
