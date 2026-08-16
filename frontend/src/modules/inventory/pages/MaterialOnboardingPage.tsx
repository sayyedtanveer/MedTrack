import { useMemo, useState } from 'react'
import { CheckCircle2, Download, FileSpreadsheet, Pencil, ShieldAlert, Upload, XCircle } from 'lucide-react'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { useToast } from '@/hooks/use-toast'
import { materialOnboardingService, rawMaterialOnboardingColumns, friendlyColumnNames, type OnboardingPreview, type OnboardingPreviewRow } from '@/services/material-onboarding.service'

const steps = ['Upload', 'Mapping', 'Review', 'Summary']
const fieldOptions = rawMaterialOnboardingColumns
const editableFields = ['item_code', 'material_name', 'material_category', 'uom', 'barcode', 'approved_supplier', 'supplier_item_code', 'reorder_level', 'min_stock', 'max_stock', 'batch_tracking_enabled', 'traceability_enabled', 'length_uom', 'decimal_precision']

function messageFrom(error: unknown) {
  return error instanceof Error ? error.message : 'Something went wrong'
}

function downloadBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  link.click()
  URL.revokeObjectURL(url)
}

export default function MaterialOnboardingPage() {
  const [step, setStep] = useState(0)
  const [file, setFile] = useState<File | null>(null)
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [mapping, setMapping] = useState<Record<string, string>>({})
  const [preview, setPreview] = useState<OnboardingPreview | null>(null)
  const [summary, setSummary] = useState<Record<string, any> | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [editingRow, setEditingRow] = useState<OnboardingPreviewRow | null>(null)
  const [editData, setEditData] = useState<Record<string, string>>({})
  const { toast } = useToast()

  const protectedCount = useMemo(() => preview?.rows.reduce((n, r) => n + r.protected_changes.length, 0) ?? 0, [preview])
  const errors = preview?.rows.flatMap((r) => r.issues.filter((i) => i.severity === 'error').map((i) => ({ row: r.row_number, ...i }))) ?? []
  const warnings = preview?.rows.flatMap((r) => r.issues.filter((i) => i.severity !== 'error').map((i) => ({ row: r.row_number, ...i }))) ?? []
  const mappedRequired = ['material_name', 'material_category', 'uom'].every((field) => Object.values(mapping).includes(field))

  async function withBusy(action: () => Promise<void>) {
    setBusy(true)
    setError(null)
    try {
      await action()
    } catch (err) {
      setError(messageFrom(err))
    } finally {
      setBusy(false)
    }
  }

  async function upload() {
    if (!file) return
    await withBusy(async () => {
      const routesAvailable = await materialOnboardingService.backendRoutesAvailable()
      if (!routesAvailable) {
        throw new Error('Material onboarding API is not loaded on the running backend. Restart the backend server, then try the upload again.')
      }
      const res = await materialOnboardingService.upload(file)
      const suggested = JSON.parse(res.data.mapping || '{}')
      setSessionId(res.data.session_id)
      setMapping(Object.fromEntries(res.data.headers.map((header) => [header, suggested[header] ?? ''])))
      setPreview(null)
      setSummary(null)
      setStep(1)
    })
  }

  async function validate() {
    if (!sessionId) return
    await withBusy(async () => {
      await materialOnboardingService.validate(sessionId, mapping)
      const res = await materialOnboardingService.preview(sessionId)
      setPreview(res.data)
      setStep(2)
    })
  }

  async function refreshPreview() {
    if (!sessionId) return
    const res = await materialOnboardingService.preview(sessionId)
    setPreview(res.data)
  }

  async function saveRowCorrection() {
    if (!editingRow) return
    await withBusy(async () => {
      await materialOnboardingService.updateRow(editingRow.id, editData)
      setEditingRow(null)
      setEditData({})
      await refreshPreview()
    })
  }

  async function execute(dryRun: boolean) {
    if (!sessionId) return
    await withBusy(async () => {
      if (!dryRun && protectedCount) await materialOnboardingService.confirmProtected(sessionId)
      const res = await materialOnboardingService.execute(sessionId, dryRun)
      setSummary(res.data)
      setStep(3)
      toast({
        title: dryRun ? "Dry run complete" : "Import successful",
        description: dryRun ? "Review the summary before confirming the import." : "Materials have been successfully imported.",
      })
    })
  }

  async function downloadReport() {
    if (!sessionId) return
    await withBusy(async () => {
      const res = await materialOnboardingService.validationReport(sessionId)
      downloadBlob(res.data, `material-onboarding-validation-${sessionId}.csv`)
    })
  }

  function updateMapping(source: string, target: string) {
    setMapping((current) => {
      const next = { ...current }
      if (target === '_ignore') delete next[source]
      else next[source] = target
      return next
    })
  }

  function openEditor(row: OnboardingPreviewRow) {
    setEditingRow(row)
    setEditData(Object.fromEntries(editableFields.map((field) => [field, row.data[field] ?? ''])))
  }

  return (
    <div className="space-y-6">
      <div className="sticky top-0 z-10 border-b bg-background/95 pb-4 pt-4 backdrop-blur">
        <p className="text-xs font-semibold uppercase tracking-[0.24em] text-blue-600">Master data onboarding</p>
        <h1 className="mt-2 text-3xl font-bold tracking-tight">Raw Material Upload</h1>
        <div className="mt-4 flex flex-wrap gap-2">
          {steps.map((s, i) => <Badge key={s} variant={i <= step ? 'default' : 'outline'}>{i + 1}. {s}</Badge>)}
        </div>
      </div>

      {error && (
        <Alert variant="destructive">
          <XCircle className="h-4 w-4" />
          <AlertTitle>Onboarding failed</AlertTitle>
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {step === 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Upload file</CardTitle>
            <p className="text-sm text-muted-foreground mt-2">
              Download a template, fill in your material data, and upload the file to begin. Ensure your headers match the template for automatic mapping.
            </p>
          </CardHeader>
          <CardContent className="space-y-4">
            <Alert>
              <AlertTitle className="text-sm font-semibold">Best Practice for Updates</AlertTitle>
              <AlertDescription className="text-xs text-muted-foreground mt-1">
                If you are updating existing materials, ensure your file includes the <strong className="font-medium text-foreground">item_code</strong> column. Without the item code, the system relies on exact name matching—any spelling mistakes in the material name will cause the system to create accidental duplicates instead of updating the existing item.
              </AlertDescription>
            </Alert>
            <div className="flex flex-wrap gap-2">
              <Button asChild variant="outline"><a href={materialOnboardingService.templateUrl('csv')}><Download className="mr-2 h-4 w-4" />CSV template</a></Button>
              <Button asChild variant="outline"><a href={materialOnboardingService.templateUrl('xlsx')}><FileSpreadsheet className="mr-2 h-4 w-4" />Excel template</a></Button>
            </div>
            <Input type="file" accept=".csv,.xlsx" onChange={(e) => setFile(e.target.files?.[0] ?? null)} />
            <Button disabled={!file || busy} onClick={upload}><Upload className="mr-2 h-4 w-4" />Upload and map</Button>
          </CardContent>
        </Card>
      )}

      {step === 1 && (
        <Card>
          <CardHeader>
            <CardTitle>Column mapping</CardTitle>
            <p className="text-sm text-muted-foreground mt-2">
              Map the columns from your uploaded file to the system fields. Required fields (material name, category, UOM) must be mapped to proceed.
            </p>
          </CardHeader>
          <CardContent className="space-y-4">
            {Object.entries(mapping).length === 0 && <p className="text-sm text-muted-foreground">No columns were auto-mapped. Add mappings by re-uploading a file with a header row that matches the template.</p>}
            {Object.entries(mapping).map(([source, target]) => (
              <div key={source} className="grid gap-2 md:grid-cols-[minmax(0,1fr)_260px]">
                <div className="rounded-md bg-muted px-3 py-2 text-sm font-medium">{source}</div>
                <Select value={target || '_ignore'} onValueChange={(value) => updateMapping(source, value)}>
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="_ignore">Ignore column</SelectItem>
                    {fieldOptions.map((field) => <SelectItem key={field} value={field}>{friendlyColumnNames[field] || field}</SelectItem>)}
                  </SelectContent>
                </Select>
              </div>
            ))}
            {!mappedRequired && <p className="text-sm text-amber-700">Required mappings: material_name, material_category, and uom.</p>}
            <div className="flex justify-end gap-2">
              <Button variant="outline" onClick={() => setStep(0)} disabled={busy}>Back</Button>
              <Button onClick={validate} disabled={busy || !mappedRequired}>Validate file</Button>
            </div>
          </CardContent>
        </Card>
      )}

      {step === 2 && preview && (
        <>
          <div className="grid gap-4 md:grid-cols-4">
            {Object.entries(preview.summary).map(([k, v]) => <Card key={k}><CardContent className="p-4"><div className="text-sm text-muted-foreground">{k.replace(/_/g, ' ')}</div><div className="mt-2 text-2xl font-bold">{v}</div></CardContent></Card>)}
          </div>
          <Card>
            <CardHeader>
              <CardTitle>Validation review</CardTitle>
              <p className="text-sm text-muted-foreground mt-2">
                Review any issues found during validation. You can correct errors directly here or run a dry run to simulate the import.
              </p>
            </CardHeader>
            <CardContent className="space-y-3">
              {errors.length === 0 ? <p className="flex items-center gap-2 text-emerald-700"><CheckCircle2 className="h-4 w-4" />No blocking validation errors.</p> :
                errors.map((e, i) => <div key={i} className="rounded-md border border-red-200 bg-red-50 p-3 text-sm">Row {e.row}: {e.message}</div>)}
              {warnings.map((e, i) => <div key={i} className="rounded-md border border-amber-200 bg-amber-50 p-3 text-sm">Row {e.row}: {e.message}</div>)}
              {protectedCount > 0 && <div className="rounded-md border border-amber-200 bg-amber-50 p-3 text-sm"><ShieldAlert className="mr-2 inline h-4 w-4" />{protectedCount} protected-field changes require confirmation before commit.</div>}
            </CardContent>
          </Card>
          <Card>
            <CardHeader><CardTitle>Preview</CardTitle></CardHeader>
            <CardContent className="space-y-2">
              {preview.rows.slice(0, 50).map((r) => (
                <div key={r.id} className="rounded-md border p-3">
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <div className="flex flex-wrap items-center gap-2">
                      <Badge variant="outline">Row {r.row_number}</Badge>
                      <Badge>{r.classification}</Badge>
                      <span className="font-medium">{r.data.material_name || 'Unnamed material'}</span>
                      <span className="font-mono text-sm text-muted-foreground">{r.data.item_code || 'Auto item code'}</span>
                    </div>
                    <Button variant="outline" size="sm" onClick={() => openEditor(r)}><Pencil className="mr-2 h-4 w-4" />Correct</Button>
                  </div>
                  {r.protected_changes.length > 0 && <div className="mt-2 text-xs text-amber-700">{r.protected_changes.map((c) => `${c.field}: ${c.from} -> ${c.to}`).join(', ')}</div>}
                </div>
              ))}
            </CardContent>
          </Card>
          <div className="sticky bottom-0 flex flex-wrap justify-end gap-2 border-t bg-background/95 py-4 backdrop-blur">
            <Button variant="outline" onClick={() => setStep(1)} disabled={busy}>Back</Button>
            <Button variant="outline" onClick={downloadReport} disabled={busy}>Download report</Button>
            <Button variant="outline" onClick={() => execute(true)} disabled={busy}>Run dry run</Button>
            <Button onClick={() => execute(false)} disabled={busy || errors.length > 0}>Confirm import</Button>
          </div>
        </>
      )}

      {step === 3 && summary && (
        <Card>
          <CardHeader>
            <CardTitle>{summary.dry_run ? 'Dry run summary' : 'Import summary'}</CardTitle>
            <p className="text-sm text-muted-foreground mt-2">
              {summary.dry_run
                ? 'This was a dry run. No data was modified. If the results look good, go back and confirm the import.'
                : 'Import completed successfully.'}
            </p>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="grid gap-4 md:grid-cols-4">
              {Object.entries(summary).filter(([, v]) => typeof v === 'number').map(([k, v]) => (
                <div key={k} className="rounded-md border p-4"><div className="text-sm text-muted-foreground">{k.replace(/_/g, ' ')}</div><div className="mt-2 text-2xl font-bold">{String(v)}</div></div>
              ))}
            </div>
            
            {summary.error_messages?.length > 0 && (
              <div className="rounded-md border border-red-200 bg-red-50 p-4">
                <h4 className="text-sm font-semibold text-red-800 mb-2">Errors encountered:</h4>
                <ul className="list-disc list-inside text-sm text-red-700 space-y-1">
                  {summary.error_messages.map((msg: string, i: number) => (
                    <li key={i}>{msg}</li>
                  ))}
                </ul>
              </div>
            )}
            
            <div className="flex justify-end gap-2">
              {summary.dry_run ? (
                <Button onClick={() => setStep(2)}>Go back to review</Button>
              ) : (
                <Button onClick={() => {
                  setStep(0);
                  setFile(null);
                  setSessionId(null);
                  setPreview(null);
                  setSummary(null);
                }}>Start new import</Button>
              )}
            </div>
          </CardContent>
        </Card>
      )}

      <Dialog open={Boolean(editingRow)} onOpenChange={(open) => !open && setEditingRow(null)}>
        <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-3xl">
          <DialogHeader><DialogTitle>Correct row {editingRow?.row_number}</DialogTitle></DialogHeader>
          <div className="grid gap-4 md:grid-cols-2">
            {editableFields.map((field) => (
              <div key={field} className="space-y-2">
                <Label htmlFor={`edit-${field}`}>{friendlyColumnNames[field] || field}</Label>
                <Input id={`edit-${field}`} value={editData[field] ?? ''} onChange={(e) => setEditData((data) => ({ ...data, [field]: e.target.value }))} />
              </div>
            ))}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setEditingRow(null)} disabled={busy}>Cancel</Button>
            <Button onClick={saveRowCorrection} disabled={busy}>Save correction</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
