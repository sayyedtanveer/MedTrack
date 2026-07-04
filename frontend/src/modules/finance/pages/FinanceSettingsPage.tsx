import { useEffect, useState } from "react"
import { useNavigate } from "react-router-dom"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { ArrowLeft, Building2, Save, Settings2 } from "lucide-react"

import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { financeService, type FinanceSettings } from "@/services/finance.service"
import { toast } from "@/hooks/use-toast"

export default function FinanceSettingsPage() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [formData, setFormData] = useState<Partial<FinanceSettings>>({})

  const { data: settings, isLoading } = useQuery({
    queryKey: ["finance-settings"],
    queryFn: financeService.getFinanceSettings,
  })

  const { data: chartOfAccounts } = useQuery({
    queryKey: ["finance-chart-of-accounts"],
    queryFn: financeService.getChartOfAccounts,
  })

  useEffect(() => {
    if (settings) {
      setFormData({
        invoice_prefix: settings.invoice_prefix,
        supplier_invoice_prefix: settings.supplier_invoice_prefix,
        payment_prefix: settings.payment_prefix,
        supplier_payment_prefix: settings.supplier_payment_prefix,
        invoice_template: settings.invoice_template,
        default_tax_rate: settings.default_tax_rate,
        default_payment_terms_days: settings.default_payment_terms_days,
        gst_number: settings.gst_number || "",
        logo_url: settings.logo_url || "",
        ar_account_code: settings.ar_account_code,
        bank_account_code: settings.bank_account_code,
        ap_account_code: settings.ap_account_code,
        revenue_account_code: settings.revenue_account_code,
        expense_account_code: settings.expense_account_code,
      })
    }
  }, [settings])

  const saveMutation = useMutation({
    mutationFn: () => financeService.updateFinanceSettings(formData),
    onSuccess: () => {
      toast({ title: "Finance settings updated" })
      queryClient.invalidateQueries({ queryKey: ["finance-settings"] })
      queryClient.invalidateQueries({ queryKey: ["finance-dashboard"] })
    },
    onError: (error: any) => {
      toast({
        title: "Unable to save settings",
        description: error.message,
        variant: "destructive",
      })
    },
  })

  const handleChange = (name: keyof FinanceSettings, value: string) => {
    const numericFields = new Set<keyof FinanceSettings>(["default_tax_rate", "default_payment_terms_days"])
    setFormData((prev) => ({
      ...prev,
      [name]: numericFields.has(name) ? Number(value || 0) : value,
    }))
  }

  return (
    <div className="space-y-6 p-4 md:p-6 xl:p-8">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div className="flex items-start gap-3">
          <Button variant="outline" size="icon" onClick={() => navigate("/finance")} aria-label="Back to finance dashboard">
            <ArrowLeft className="h-4 w-4" />
          </Button>
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.3em] text-slate-400">Finance</p>
            <h1 className="text-2xl font-semibold text-slate-900">Billing & Accounting Settings</h1>
            <p className="text-sm text-slate-500">
              Configure numbering, tax defaults, and account mappings for this tenant.
            </p>
          </div>
        </div>

        <Button onClick={() => saveMutation.mutate()} disabled={saveMutation.isPending}>
          <Save className="mr-2 h-4 w-4" />
          {saveMutation.isPending ? "Saving..." : "Save Settings"}
        </Button>
      </div>

      <div className="grid gap-6 xl:grid-cols-3">
        <Card className="xl:col-span-2">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Settings2 className="h-4 w-4 text-blue-600" />
              Tenant Finance Configuration
            </CardTitle>
            <CardDescription>These settings drive invoice numbering, payment references, and ledger posting defaults.</CardDescription>
          </CardHeader>
          <CardContent className="grid gap-4 md:grid-cols-2">
            <div className="space-y-2">
              <label className="text-sm font-medium text-slate-700">Invoice prefix</label>
              <Input value={String(formData.invoice_prefix || "")} onChange={(event) => handleChange("invoice_prefix", event.target.value)} />
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium text-slate-700">Supplier invoice prefix</label>
              <Input value={String(formData.supplier_invoice_prefix || "")} onChange={(event) => handleChange("supplier_invoice_prefix", event.target.value)} />
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium text-slate-700">Payment prefix</label>
              <Input value={String(formData.payment_prefix || "")} onChange={(event) => handleChange("payment_prefix", event.target.value)} />
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium text-slate-700">Supplier payment prefix</label>
              <Input value={String(formData.supplier_payment_prefix || "")} onChange={(event) => handleChange("supplier_payment_prefix", event.target.value)} />
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium text-slate-700">Invoice template</label>
              <Input value={String(formData.invoice_template || "")} onChange={(event) => handleChange("invoice_template", event.target.value)} />
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium text-slate-700">GST number</label>
              <Input value={String(formData.gst_number || "")} onChange={(event) => handleChange("gst_number", event.target.value)} />
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium text-slate-700">Default tax rate</label>
              <Input type="number" step="0.01" value={String(formData.default_tax_rate ?? 0)} onChange={(event) => handleChange("default_tax_rate", event.target.value)} />
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium text-slate-700">Default payment terms (days)</label>
              <Input type="number" value={String(formData.default_payment_terms_days ?? 30)} onChange={(event) => handleChange("default_payment_terms_days", event.target.value)} />
            </div>
            <div className="space-y-2 md:col-span-2">
              <label className="text-sm font-medium text-slate-700">Logo URL</label>
              <Input value={String(formData.logo_url || "")} onChange={(event) => handleChange("logo_url", event.target.value)} />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Building2 className="h-4 w-4 text-emerald-600" />
              Posting Accounts
            </CardTitle>
            <CardDescription>Set the default accounts used by AR, AP, revenue, expense, and bank postings.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {[
              ["ar_account_code", "Accounts receivable"],
              ["bank_account_code", "Bank"],
              ["ap_account_code", "Accounts payable"],
              ["revenue_account_code", "Revenue"],
              ["expense_account_code", "Expense"],
            ].map(([key, label]) => (
              <div key={key} className="space-y-2">
                <label className="text-sm font-medium text-slate-700">{label}</label>
                <Input
                  value={String(formData[key as keyof FinanceSettings] || "")}
                  onChange={(event) => handleChange(key as keyof FinanceSettings, event.target.value)}
                />
              </div>
            ))}
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Chart of Accounts</CardTitle>
          <CardDescription>Read-only view of the tenant chart of accounts currently available for postings.</CardDescription>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
              {Array.from({ length: 6 }).map((_, index) => (
                <div key={index} className="h-24 animate-pulse rounded-2xl bg-slate-100" />
              ))}
            </div>
          ) : chartOfAccounts && chartOfAccounts.length > 0 ? (
            <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
              {chartOfAccounts.map((account) => (
                <div key={account.id} className="rounded-2xl border border-slate-100 bg-slate-50 p-4">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <p className="text-xs font-semibold uppercase tracking-[0.24em] text-slate-400">{account.code}</p>
                      <p className="mt-2 font-medium text-slate-900">{account.name}</p>
                    </div>
                    <span className="rounded-full bg-white px-2.5 py-1 text-xs font-medium text-slate-600 shadow-sm">
                      {account.account_type}
                    </span>
                  </div>
                  <p className="mt-2 text-sm text-slate-500">{account.category}</p>
                  <p className="mt-1 text-xs text-slate-400">
                    {account.normal_balance} · {account.is_system ? "System" : "Custom"} · {account.is_active ? "Active" : "Inactive"}
                  </p>
                </div>
              ))}
            </div>
          ) : (
            <div className="rounded-2xl border border-dashed border-slate-200 p-6 text-sm text-slate-500">
              No chart of accounts is available yet for this tenant.
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
