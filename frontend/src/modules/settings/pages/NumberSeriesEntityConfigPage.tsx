import { useCallback, useEffect, useMemo, useRef, useState } from "react"
import { useParams, useNavigate } from "react-router-dom"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import {
  numberSeriesService,
  type NumberSeriesConfig,
  type NumberSeriesPrefix,
} from "@/services/number-series.service"
import { useToast } from "@/hooks/use-toast"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Checkbox } from "@/components/ui/checkbox"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { ArrowLeft, Save, Eye } from "lucide-react"

// ── Validation helpers ────────────────────────────────────────────────────────

interface FieldErrors {
  abbreviation_length?: string
  sequence_length?: string
  separator?: string
  prefixes?: Record<string, string>
}

function validateConfig(
  config: Partial<NumberSeriesConfig>,
  prefixes: NumberSeriesPrefix[]
): FieldErrors {
  const errors: FieldErrors = {}

  if (config.include_abbreviation) {
    const abbrevLen = config.abbreviation_length ?? 0
    if (!Number.isInteger(abbrevLen) || abbrevLen < 2 || abbrevLen > 6) {
      errors.abbreviation_length = "Must be an integer between 2 and 6"
    }
  }

  const seqLen = config.sequence_length ?? 0
  if (!Number.isInteger(seqLen) || seqLen < 4 || seqLen > 10) {
    errors.sequence_length = "Must be an integer between 4 and 10"
  }

  const sep = config.separator ?? ""
  if (sep.length > 5) {
    errors.separator = "Maximum 5 characters"
  }

  // Validate prefixes
  const prefixErrors: Record<string, string> = {}
  for (const p of prefixes) {
    if (!p.prefix || p.prefix.length === 0) {
      prefixErrors[p.sub_type] = "Prefix is required (1-10 uppercase alphanumeric chars)"
    } else if (p.prefix.length > 10) {
      prefixErrors[p.sub_type] = "Maximum 10 characters"
    } else if (!/^[A-Z0-9]+$/.test(p.prefix)) {
      prefixErrors[p.sub_type] = "Only uppercase letters and digits allowed"
    }
  }
  if (Object.keys(prefixErrors).length > 0) {
    errors.prefixes = prefixErrors
  }

  return errors
}

function hasErrors(errors: FieldErrors): boolean {
  if (errors.abbreviation_length || errors.sequence_length || errors.separator) return true
  if (errors.prefixes && Object.keys(errors.prefixes).length > 0) return true
  return false
}

// ── Component ─────────────────────────────────────────────────────────────────

export default function NumberSeriesEntityConfigPage() {
  const { entityType } = useParams<{ entityType: string }>()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const { toast } = useToast()

  // ─ Form state ──────────────────────────────────────────────────────────────
  const [formState, setFormState] = useState<Partial<NumberSeriesConfig>>({})
  const [editedPrefixes, setEditedPrefixes] = useState<NumberSeriesPrefix[]>([])
  const [errors, setErrors] = useState<FieldErrors>({})
  const [preview, setPreview] = useState<string>("")
  const [previewLoading, setPreviewLoading] = useState(false)
  const [initialized, setInitialized] = useState(false)

  // ─ Data fetching ───────────────────────────────────────────────────────────
  const { data: config, isLoading: configLoading } = useQuery({
    queryKey: ["number-series-config", entityType],
    queryFn: () => numberSeriesService.getConfig(entityType!),
    enabled: !!entityType,
  })

  const { data: prefixes, isLoading: prefixesLoading } = useQuery({
    queryKey: ["number-series-prefixes", entityType],
    queryFn: () => numberSeriesService.getPrefixes(entityType!),
    enabled: !!entityType,
  })

  // Initialize form state from fetched data
  useEffect(() => {
    if (config && !initialized) {
      setFormState({
        auto_generate: config.auto_generate,
        manual_override: config.manual_override,
        include_abbreviation: config.include_abbreviation,
        abbreviation_length: config.abbreviation_length,
        sequence_length: config.sequence_length,
        separator: config.separator,
        lock_after_save: config.lock_after_save,
      })
      setInitialized(true)
    }
  }, [config, initialized])

  useEffect(() => {
    if (prefixes && editedPrefixes.length === 0) {
      setEditedPrefixes([...prefixes])
    }
  }, [prefixes, editedPrefixes.length])

  // ─ Debounced preview ───────────────────────────────────────────────────────
  const previewTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  const fetchPreview = useCallback(async () => {
    if (!entityType) return
    setPreviewLoading(true)
    try {
      const firstPrefix = editedPrefixes.length > 0 ? editedPrefixes[0] : undefined
      const result = await numberSeriesService.previewCode(
        entityType,
        firstPrefix?.sub_type,
        "Sample Item"
      )
      setPreview(result.preview || result.format_pattern || "")
    } catch {
      setPreview("Unable to load preview")
    } finally {
      setPreviewLoading(false)
    }
  }, [entityType, editedPrefixes])

  // Trigger debounced preview on form change
  const debouncedPreview = useCallback(() => {
    if (previewTimerRef.current) {
      clearTimeout(previewTimerRef.current)
    }
    previewTimerRef.current = setTimeout(() => {
      fetchPreview()
    }, 500)
  }, [fetchPreview])

  // Re-fetch preview whenever form state or prefixes change
  useEffect(() => {
    if (initialized) {
      debouncedPreview()
    }
    return () => {
      if (previewTimerRef.current) {
        clearTimeout(previewTimerRef.current)
      }
    }
  }, [formState, editedPrefixes, initialized, debouncedPreview])

  // Initial preview
  useEffect(() => {
    if (initialized && entityType) {
      fetchPreview()
    }
  }, [initialized, entityType, fetchPreview])

  // ─ Validation on change ────────────────────────────────────────────────────
  useEffect(() => {
    if (initialized) {
      const validationErrors = validateConfig(formState, editedPrefixes)
      setErrors(validationErrors)
    }
  }, [formState, editedPrefixes, initialized])

  // ─ Save mutations ──────────────────────────────────────────────────────────
  const configMutation = useMutation({
    mutationFn: async () => {
      if (!entityType) throw new Error("No entity type")

      // Save config
      await numberSeriesService.updateConfig(entityType, {
        auto_generate: formState.auto_generate,
        manual_override: formState.manual_override,
        include_abbreviation: formState.include_abbreviation,
        abbreviation_length: formState.abbreviation_length,
        sequence_length: formState.sequence_length,
        separator: formState.separator,
        lock_after_save: formState.lock_after_save,
      })

      // Save edited prefixes
      for (const p of editedPrefixes) {
        const original = prefixes?.find((op) => op.sub_type === p.sub_type)
        if (original && original.prefix !== p.prefix) {
          await numberSeriesService.updatePrefix(entityType, p.sub_type, p.prefix)
        }
      }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["number-series-config", entityType] })
      queryClient.invalidateQueries({ queryKey: ["number-series-prefixes", entityType] })
      queryClient.invalidateQueries({ queryKey: ["number-series"] })
      toast({
        title: "Configuration saved",
        description: `Number series settings for ${formatEntityType(entityType || "")} updated successfully.`,
      })
    },
    onError: (error: any) => {
      const message =
        error?.response?.data?.detail || error?.message || "Failed to save configuration"
      toast({
        title: "Save failed",
        description: message,
        variant: "destructive",
      })
    },
  })

  const handleSave = () => {
    const validationErrors = validateConfig(formState, editedPrefixes)
    setErrors(validationErrors)
    if (hasErrors(validationErrors)) return
    configMutation.mutate()
  }

  // ─ Form handlers ───────────────────────────────────────────────────────────
  const updateField = <K extends keyof NumberSeriesConfig>(
    field: K,
    value: NumberSeriesConfig[K]
  ) => {
    setFormState((prev) => ({ ...prev, [field]: value }))
  }

  const updatePrefixValue = (subType: string, value: string) => {
    setEditedPrefixes((prev) =>
      prev.map((p) => (p.sub_type === subType ? { ...p, prefix: value.toUpperCase() } : p))
    )
  }

  // ─ Computed ────────────────────────────────────────────────────────────────
  const entityLabel = useMemo(() => formatEntityType(entityType || ""), [entityType])
  const isLoading = configLoading || prefixesLoading

  if (isLoading) {
    return (
      <div className="p-8 flex items-center justify-center">
        <div className="animate-pulse text-muted-foreground">Loading configuration...</div>
      </div>
    )
  }

  return (
    <div className="max-w-3xl space-y-6 pb-8">
      {/* Header */}
      <div className="flex items-center gap-3">
        <Button variant="ghost" size="sm" onClick={() => navigate(-1)}>
          <ArrowLeft className="h-4 w-4" />
        </Button>
        <div>
          <h1 className="text-2xl font-bold">Number Series — {entityLabel}</h1>
          <p className="text-sm text-muted-foreground">
            Configure code generation settings for {entityLabel.toLowerCase()} entities
          </p>
        </div>
      </div>

      {/* Live Preview */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-sm font-medium flex items-center gap-2">
            <Eye className="h-4 w-4" />
            Live Preview
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="rounded-md bg-muted px-4 py-3 font-mono text-lg">
            {previewLoading ? (
              <span className="text-muted-foreground animate-pulse">Generating...</span>
            ) : (
              preview || "—"
            )}
          </div>
        </CardContent>
      </Card>

      {/* Configuration Form */}
      <Card>
        <CardHeader>
          <CardTitle>General Settings</CardTitle>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Auto Generate Toggle */}
          <div className="flex items-center space-x-3">
            <Checkbox
              id="auto_generate"
              checked={formState.auto_generate ?? true}
              onCheckedChange={(checked) => updateField("auto_generate", checked === true)}
            />
            <Label htmlFor="auto_generate" className="cursor-pointer">
              Auto-generate codes
            </Label>
          </div>

          {/* Manual Override */}
          <div className="space-y-2">
            <Label htmlFor="manual_override">Manual Override Policy</Label>
            <Select
              value={formState.manual_override || "never"}
              onValueChange={(val) =>
                updateField("manual_override", val as "never" | "admin_only" | "always")
              }
            >
              <SelectTrigger id="manual_override">
                <SelectValue placeholder="Select policy" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="never">Never — always auto-generate</SelectItem>
                <SelectItem value="admin_only">Admin Only — admins can enter manual codes</SelectItem>
                <SelectItem value="always">Always — any user can enter manual codes</SelectItem>
              </SelectContent>
            </Select>
          </div>

          {/* Include Abbreviation Toggle */}
          <div className="flex items-center space-x-3">
            <Checkbox
              id="include_abbreviation"
              checked={formState.include_abbreviation ?? false}
              onCheckedChange={(checked) => updateField("include_abbreviation", checked === true)}
            />
            <Label htmlFor="include_abbreviation" className="cursor-pointer">
              Include abbreviation in code
            </Label>
          </div>

          {/* Abbreviation Length — only visible when include_abbreviation is on */}
          {formState.include_abbreviation && (
            <div className="space-y-2">
              <Label htmlFor="abbreviation_length">Abbreviation Length</Label>
              <Input
                id="abbreviation_length"
                type="number"
                min={2}
                max={6}
                value={formState.abbreviation_length ?? 3}
                onChange={(e) => updateField("abbreviation_length", parseInt(e.target.value, 10) || 0)}
                className={errors.abbreviation_length ? "border-destructive" : ""}
              />
              {errors.abbreviation_length && (
                <p className="text-xs text-destructive">{errors.abbreviation_length}</p>
              )}
            </div>
          )}

          {/* Sequence Length */}
          <div className="space-y-2">
            <Label htmlFor="sequence_length">Sequence Length</Label>
            <Input
              id="sequence_length"
              type="number"
              min={4}
              max={10}
              value={formState.sequence_length ?? 6}
              onChange={(e) => updateField("sequence_length", parseInt(e.target.value, 10) || 0)}
              className={errors.sequence_length ? "border-destructive" : ""}
            />
            {errors.sequence_length && (
              <p className="text-xs text-destructive">{errors.sequence_length}</p>
            )}
          </div>

          {/* Separator */}
          <div className="space-y-2">
            <Label htmlFor="separator">Separator</Label>
            <Input
              id="separator"
              type="text"
              maxLength={5}
              value={formState.separator ?? "-"}
              onChange={(e) => updateField("separator", e.target.value)}
              className={errors.separator ? "border-destructive" : ""}
              placeholder="-"
            />
            {errors.separator && (
              <p className="text-xs text-destructive">{errors.separator}</p>
            )}
          </div>

          {/* Lock After Save Toggle */}
          <div className="flex items-center space-x-3">
            <Checkbox
              id="lock_after_save"
              checked={formState.lock_after_save ?? true}
              onCheckedChange={(checked) => updateField("lock_after_save", checked === true)}
            />
            <Label htmlFor="lock_after_save" className="cursor-pointer">
              Lock code after save (immutable)
            </Label>
          </div>
        </CardContent>
      </Card>

      {/* Sub-Type Prefix Table */}
      {editedPrefixes.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Sub-Type Prefixes</CardTitle>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Sub-Type</TableHead>
                  <TableHead>Prefix</TableHead>
                  <TableHead>Status</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {editedPrefixes.map((p) => (
                  <TableRow key={p.sub_type}>
                    <TableCell className="font-medium capitalize">
                      {p.sub_type.replace(/_/g, " ")}
                    </TableCell>
                    <TableCell>
                      <Input
                        value={p.prefix}
                        onChange={(e) => updatePrefixValue(p.sub_type, e.target.value)}
                        className={`w-24 uppercase ${errors.prefixes?.[p.sub_type] ? "border-destructive" : ""}`}
                        maxLength={10}
                        placeholder="RM"
                      />
                      {errors.prefixes?.[p.sub_type] && (
                        <p className="text-xs text-destructive mt-1">
                          {errors.prefixes[p.sub_type]}
                        </p>
                      )}
                    </TableCell>
                    <TableCell>
                      <span
                        className={`inline-flex px-2 py-0.5 rounded-full text-xs font-medium ${
                          p.is_active
                            ? "bg-green-100 text-green-800"
                            : "bg-gray-100 text-gray-600"
                        }`}
                      >
                        {p.is_active ? "Active" : "Inactive"}
                      </span>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}

      {/* Save Button */}
      <div className="flex justify-end gap-3">
        <Button variant="outline" onClick={() => navigate(-1)}>
          Cancel
        </Button>
        <Button
          onClick={handleSave}
          disabled={configMutation.isPending || hasErrors(errors)}
        >
          <Save className="mr-2 h-4 w-4" />
          {configMutation.isPending ? "Saving..." : "Save Configuration"}
        </Button>
      </div>
    </div>
  )
}

// ── Utility ───────────────────────────────────────────────────────────────────

function formatEntityType(entityType: string): string {
  return entityType
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase())
}
