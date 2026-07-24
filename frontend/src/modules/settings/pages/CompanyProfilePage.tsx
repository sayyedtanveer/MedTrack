import { useState, useEffect, useCallback, useMemo, useRef } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { toast } from "sonner"
import { Building2, Upload, X } from "lucide-react"

import { tenantService } from "@/services/tenant.service"
import type { UpdateTenantPayload } from "@/types/tenant.types"

import { PageHeader } from "@/components/layout/PageHeader"
import { BusinessAssistantPanel } from "@/components/shared/BusinessAssistantPanel"
import { companyProfileAssistant } from "@/modules/settings/business-assistant/companyProfileAssistant"

import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"

// ── Constants ─────────────────────────────────────────────────────────────────

const GST_REGEX = /^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$/

const TIMEZONES = [
  "Asia/Kolkata",
  "Asia/Dubai",
  "Asia/Singapore",
  "Asia/Tokyo",
  "Asia/Shanghai",
  "Europe/London",
  "Europe/Paris",
  "Europe/Berlin",
  "America/New_York",
  "America/Chicago",
  "America/Los_Angeles",
  "UTC",
  "America/Toronto",
  "America/Sao_Paulo",
  "Africa/Johannesburg",
  "Australia/Sydney",
]

const CURRENCIES = [
  { code: "INR", name: "Indian Rupee", symbol: "₹" },
  { code: "USD", name: "US Dollar", symbol: "$" },
  { code: "EUR", name: "Euro", symbol: "€" },
  { code: "GBP", name: "British Pound", symbol: "£" },
  { code: "AED", name: "UAE Dirham", symbol: "د.إ" },
  { code: "SGD", name: "Singapore Dollar", symbol: "S$" },
  { code: "JPY", name: "Japanese Yen", symbol: "¥" },
  { code: "AUD", name: "Australian Dollar", symbol: "A$" },
  { code: "CAD", name: "Canadian Dollar", symbol: "C$" },
]

const LOGO_MAX_BYTES = 2 * 1024 * 1024 // 2 MB
const LOGO_ACCEPT = ["image/png", "image/jpeg"]

// ── Form state type ───────────────────────────────────────────────────────────

interface FormState {
  company_name: string
  gst_number: string
  address: string
  phone: string
  email: string
  logo_url: string
  footer_text: string
  default_warehouse_name: string
  currency_code: string
  currency_symbol: string
  timezone: string
}

const EMPTY_FORM: FormState = {
  company_name: "",
  gst_number: "",
  address: "",
  phone: "",
  email: "",
  logo_url: "",
  footer_text: "",
  default_warehouse_name: "",
  currency_code: "",
  currency_symbol: "",
  timezone: "",
}

function profileToForm(profile: Partial<UpdateTenantPayload>): FormState {
  return {
    company_name: profile.company_name ?? "",
    gst_number: profile.gst_number ?? "",
    address: profile.address ?? "",
    phone: profile.phone ?? "",
    email: profile.email ?? "",
    logo_url: profile.logo_url ?? "",
    footer_text: profile.footer_text ?? "",
    default_warehouse_name: profile.default_warehouse_name ?? "",
    currency_code: profile.currency_code ?? "",
    currency_symbol: profile.currency_symbol ?? "",
    timezone: profile.timezone ?? "",
  }
}

/** Build the payload — only include non-empty string fields (or null to clear) */
function buildPayload(form: FormState): Partial<UpdateTenantPayload> {
  const payload: Partial<UpdateTenantPayload> = {}
  const keys = Object.keys(form) as (keyof FormState)[]
  for (const key of keys) {
    const val = form[key]
    payload[key] = val.trim() === "" ? null : val.trim()
  }
  return payload
}

// ── Main Page ─────────────────────────────────────────────────────────────────

export default function CompanyProfilePage() {
  const queryClient = useQueryClient()

  // ── Data loading ─────────────────────────────────────────────────────────
  const { data: profile, isLoading } = useQuery({
    queryKey: ["tenant-profile"],
    queryFn: tenantService.getProfile,
  })

  // ── Form state ───────────────────────────────────────────────────────────
  const [form, setForm] = useState<FormState>(EMPTY_FORM)
  const [isDirty, setIsDirty] = useState(false)

  // Populate form when data loads
  useEffect(() => {
    if (profile) {
      setForm(profileToForm(profile))
      setIsDirty(false)
    }
  }, [profile])

  const patch = useCallback((updates: Partial<FormState>) => {
    setForm((prev) => ({ ...prev, ...updates }))
    setIsDirty(true)
  }, [])

  // ── GST validation ───────────────────────────────────────────────────────
  const [gstError, setGstError] = useState("")

  const validateGst = useCallback(() => {
    if (!form.gst_number.trim()) {
      setGstError("")
      return
    }
    if (!GST_REGEX.test(form.gst_number.trim())) {
      setGstError(
        "Invalid GST number. Expected format: 22AAAAA0000A1Z5 (2-digit state + 5-letter PAN + 4 digits + 3 check chars)"
      )
    } else {
      setGstError("")
    }
  }, [form.gst_number])

  // ── Timezone searchable dropdown ─────────────────────────────────────────
  const [timezoneSearch, setTimezoneSearch] = useState("")
  const timezoneRef = useRef<HTMLDivElement>(null)

  const filteredTimezones = useMemo(() => {
    if (!timezoneSearch.trim()) return []
    const q = timezoneSearch.toLowerCase()
    return TIMEZONES.filter((tz) => tz.toLowerCase().includes(q))
  }, [timezoneSearch])

  // Close timezone dropdown when clicking outside
  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (timezoneRef.current && !timezoneRef.current.contains(e.target as Node)) {
        setTimezoneSearch("")
      }
    }
    document.addEventListener("mousedown", handleClickOutside)
    return () => document.removeEventListener("mousedown", handleClickOutside)
  }, [])

  // ── Logo upload ──────────────────────────────────────────────────────────
  const [logoError, setLogoError] = useState("")
  const [logoUploading, setLogoUploading] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const handleLogoFile = useCallback(
    async (file: File) => {
      setLogoError("")

      if (!LOGO_ACCEPT.includes(file.type)) {
        setLogoError("Only PNG and JPG files are accepted.")
        return
      }
      if (file.size > LOGO_MAX_BYTES) {
        setLogoError("File must be under 2 MB.")
        return
      }

      setLogoUploading(true)
      try {
        const { url } = await tenantService.uploadLogo(file)
        patch({ logo_url: url })
      } catch {
        setLogoError("Logo upload failed. Please try again.")
      } finally {
        setLogoUploading(false)
      }
    },
    [patch]
  )

  // ── Save mutation ────────────────────────────────────────────────────────
  const saveMutation = useMutation({
    mutationFn: (payload: Partial<UpdateTenantPayload>) =>
      tenantService.updateProfile(payload),
    onSuccess: () => {
      toast.success("Company profile saved")
      queryClient.invalidateQueries({ queryKey: ["tenant-profile"] })
      setIsDirty(false)
    },
    onError: (err: Error) => {
      toast.error(err.message || "Failed to save profile.")
    },
  })

  const handleSave = useCallback(() => {
    if (!form.company_name.trim()) {
      toast.error("Company name is required.")
      return
    }
    if (form.gst_number.trim() && !GST_REGEX.test(form.gst_number.trim())) {
      toast.error("Please fix the GST number before saving.")
      return
    }
    saveMutation.mutate(buildPayload(form))
  }, [form, saveMutation])

  // ── Unsaved-changes guard ────────────────────────────────────────────────
  useEffect(() => {
    const handler = (e: BeforeUnloadEvent) => {
      if (isDirty) {
        e.preventDefault()
        e.returnValue = ""
      }
    }
    window.addEventListener("beforeunload", handler)
    return () => window.removeEventListener("beforeunload", handler)
  }, [isDirty])

  // ── Derived ──────────────────────────────────────────────────────────────
  const isSaveDisabled = !isDirty || saveMutation.isPending || logoUploading

  // ── Render ───────────────────────────────────────────────────────────────
  return (
    <div className="space-y-6 p-6">
      <PageHeader
        title="Company Profile"
        description="Configure your organisation's identity, contact details, branding, and regional preferences. These values appear on every invoice, purchase order, and delivery note."
        action={
          <div className="flex items-center gap-2">
            <BusinessAssistantPanel
              config={companyProfileAssistant}
              triggerLabel="Business Assistant"
            />
            <Button
              onClick={handleSave}
              disabled={isSaveDisabled}
            >
              {saveMutation.isPending ? "Saving…" : "Save"}
            </Button>
          </div>
        }
      />

      {isLoading ? (
        <div className="space-y-4">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="h-48 animate-pulse rounded-xl bg-slate-100" />
          ))}
        </div>
      ) : (
        <div className="grid gap-6 max-w-3xl">

          {/* ── Section 1: Identity ── */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-base">
                <Building2 className="h-4 w-4 text-slate-500" />
                Identity
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {/* Company Name */}
              <div className="space-y-1.5">
                <Label htmlFor="company_name">
                  Company Name <span className="text-red-500">*</span>
                </Label>
                <Input
                  id="company_name"
                  value={form.company_name}
                  placeholder="e.g. Acme Pharmaceuticals Pvt Ltd"
                  onChange={(e) => patch({ company_name: e.target.value })}
                />
              </div>

              {/* GST Number */}
              <div className="space-y-1.5">
                <Label htmlFor="gst_number">GST Number</Label>
                <Input
                  id="gst_number"
                  value={form.gst_number}
                  placeholder="e.g. 22AAAAA0000A1Z5"
                  onChange={(e) => {
                    patch({ gst_number: e.target.value.toUpperCase() })
                    if (gstError) setGstError("")
                  }}
                  onBlur={validateGst}
                  className={gstError ? "border-red-400 focus-visible:ring-red-400" : ""}
                />
                {gstError && (
                  <p className="text-xs text-red-500">{gstError}</p>
                )}
              </div>
            </CardContent>
          </Card>

          {/* ── Section 2: Contact ── */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Contact</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {/* Address */}
              <div className="space-y-1.5">
                <Label htmlFor="address">Address</Label>
                <Textarea
                  id="address"
                  value={form.address}
                  placeholder="e.g. Plot 12, Industrial Area Phase 2, Pune, Maharashtra 411018"
                  rows={3}
                  onChange={(e) => patch({ address: e.target.value })}
                />
              </div>

              <div className="grid gap-4 sm:grid-cols-2">
                {/* Phone */}
                <div className="space-y-1.5">
                  <Label htmlFor="phone">Phone</Label>
                  <Input
                    id="phone"
                    value={form.phone}
                    placeholder="+91 98765 43210"
                    onChange={(e) => patch({ phone: e.target.value })}
                  />
                </div>

                {/* Email */}
                <div className="space-y-1.5">
                  <Label htmlFor="email">Email</Label>
                  <Input
                    id="email"
                    type="email"
                    value={form.email}
                    placeholder="accounts@company.in"
                    onChange={(e) => patch({ email: e.target.value })}
                  />
                </div>
              </div>
            </CardContent>
          </Card>

          {/* ── Section 3: Branding ── */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Branding</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {/* Logo upload zone */}
              <div className="space-y-2">
                <Label>Company Logo</Label>
                <div className="flex flex-col gap-3 sm:flex-row sm:items-start">
                  {/* Preview */}
                  {form.logo_url ? (
                    <div className="flex items-center gap-3">
                      <img
                        src={form.logo_url}
                        alt="Company logo preview"
                        className="h-16 w-auto max-w-[200px] rounded border border-slate-200 object-contain p-1"
                      />
                      <Button
                        type="button"
                        variant="ghost"
                        size="sm"
                        className="h-8 gap-1.5 text-xs text-red-500 hover:text-red-600 hover:bg-red-50"
                        onClick={() => {
                          patch({ logo_url: "" })
                          setLogoError("")
                          if (fileInputRef.current) fileInputRef.current.value = ""
                        }}
                      >
                        <X className="h-3.5 w-3.5" />
                        Remove
                      </Button>
                    </div>
                  ) : (
                    <div className="flex h-16 w-40 items-center justify-center rounded border-2 border-dashed border-slate-200 bg-slate-50 text-xs text-slate-400">
                      No logo
                    </div>
                  )}

                  {/* Upload button */}
                  <div className="space-y-1">
                    <input
                      ref={fileInputRef}
                      type="file"
                      accept=".png,.jpg,.jpeg"
                      className="hidden"
                      onChange={(e) => {
                        const file = e.target.files?.[0]
                        if (file) handleLogoFile(file)
                      }}
                    />
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      className="gap-2"
                      disabled={logoUploading}
                      onClick={() => fileInputRef.current?.click()}
                    >
                      <Upload className="h-3.5 w-3.5" />
                      {logoUploading ? "Uploading…" : "Upload Logo"}
                    </Button>
                    <p className="text-xs text-slate-400">PNG or JPG, max 2 MB</p>
                    {logoError && (
                      <p className="text-xs text-red-500">{logoError}</p>
                    )}
                  </div>
                </div>
              </div>

              {/* Footer text */}
              <div className="space-y-1.5">
                <Label htmlFor="footer_text">Footer Text</Label>
                <Textarea
                  id="footer_text"
                  value={form.footer_text}
                  placeholder="e.g. Bank: HDFC | A/C: 50100123456789 | IFSC: HDFC0001234 | Thank you for your business!"
                  rows={3}
                  onChange={(e) => patch({ footer_text: e.target.value })}
                />
                <p className="text-xs text-slate-400">Appears at the bottom of all printed PDFs.</p>
              </div>

              {/* Default warehouse name */}
              <div className="space-y-1.5">
                <Label htmlFor="default_warehouse_name">Default Warehouse Name</Label>
                <Input
                  id="default_warehouse_name"
                  value={form.default_warehouse_name}
                  placeholder="e.g. Main Facility, Pune Plant"
                  onChange={(e) => patch({ default_warehouse_name: e.target.value })}
                />
                <p className="text-xs text-slate-400">Label used on delivery notes and stock reports.</p>
              </div>
            </CardContent>
          </Card>

          {/* ── Section 4: Regional ── */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Regional</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {/* Currency */}
              <div className="grid gap-4 sm:grid-cols-2">
                <div className="space-y-1.5">
                  <Label htmlFor="currency_code">Currency</Label>
                  <Select
                    value={form.currency_code || ""}
                    onValueChange={(val) => {
                      const found = CURRENCIES.find((c) => c.code === val)
                      patch({
                        currency_code: val,
                        currency_symbol: found?.symbol ?? form.currency_symbol,
                      })
                    }}
                  >
                    <SelectTrigger id="currency_code">
                      <SelectValue placeholder="Select currency" />
                    </SelectTrigger>
                    <SelectContent>
                      {CURRENCIES.map((c) => (
                        <SelectItem key={c.code} value={c.code}>
                          {c.symbol} — {c.code} — {c.name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-1.5">
                  <Label htmlFor="currency_symbol">Currency Symbol</Label>
                  <Select
                    value={form.currency_symbol || ""}
                    onValueChange={(val) => patch({ currency_symbol: val })}
                  >
                    <SelectTrigger id="currency_symbol">
                      <SelectValue placeholder="Select or type symbol" />
                    </SelectTrigger>
                    <SelectContent>
                      {CURRENCIES.map((c) => (
                        <SelectItem key={c.code} value={c.symbol}>
                          {c.symbol} ({c.code})
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  {/* Manual override if needed */}
                  {form.currency_symbol && !CURRENCIES.find((c) => c.symbol === form.currency_symbol) && (
                    <p className="text-xs text-amber-600">Custom symbol: {form.currency_symbol}</p>
                  )}
                </div>
              </div>

              {/* Timezone */}
              <div className="space-y-1.5">
                <Label htmlFor="timezone_search">Timezone</Label>
                <div ref={timezoneRef} className="relative">
                  {/* Selected timezone display */}
                  {form.timezone && !timezoneSearch && (
                    <div className="mb-1.5 flex items-center gap-2">
                      <span className="rounded bg-blue-50 px-2 py-0.5 text-sm font-medium text-blue-700 border border-blue-200">
                        {form.timezone}
                      </span>
                      <button
                        type="button"
                        className="text-xs text-slate-400 hover:text-slate-600"
                        onClick={() => {
                          patch({ timezone: "" })
                          setTimezoneSearch("")
                        }}
                      >
                        <X className="h-3 w-3" />
                      </button>
                    </div>
                  )}

                  {/* Search input */}
                  <Input
                    id="timezone_search"
                    value={timezoneSearch}
                    placeholder={form.timezone ? "Type to change timezone…" : "Search timezone, e.g. Kolkata, London, UTC"}
                    onChange={(e) => setTimezoneSearch(e.target.value)}
                    autoComplete="off"
                  />

                  {/* Dropdown */}
                  {filteredTimezones.length > 0 && (
                    <div className="absolute z-50 mt-1 w-full rounded-md border border-slate-200 bg-white shadow-lg">
                      <ul className="max-h-48 overflow-y-auto py-1">
                        {filteredTimezones.map((tz) => (
                          <li
                            key={tz}
                            className="cursor-pointer px-3 py-2 text-sm hover:bg-blue-50 hover:text-blue-700"
                            onMouseDown={(e) => {
                              // Use mousedown so it fires before blur
                              e.preventDefault()
                              patch({ timezone: tz })
                              setTimezoneSearch("")
                            }}
                          >
                            {tz}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
                <p className="text-xs text-slate-400">
                  IANA timezone — all transaction timestamps are displayed in this timezone.
                </p>
              </div>
            </CardContent>
          </Card>

          {/* ── Bottom save strip ── */}
          {isDirty && (
            <div className="flex items-center justify-between rounded-lg border border-amber-200 bg-amber-50 px-4 py-3">
              <p className="text-sm text-amber-700">You have unsaved changes.</p>
              <Button
                onClick={handleSave}
                disabled={isSaveDisabled}
                size="sm"
              >
                {saveMutation.isPending ? "Saving…" : "Save Changes"}
              </Button>
            </div>
          )}

        </div>
      )}
    </div>
  )
}
