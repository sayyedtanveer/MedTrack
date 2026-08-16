import { useEffect, useState } from "react"
import { supplyChainApi, type Supplier } from "@/services/supply-chain.service"
import { usersService } from "@/services/users.service"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Button } from "@/components/ui/button"
import { Checkbox } from "@/components/ui/checkbox"
import ResponsiveDataList from "@/components/shared/ResponsiveDataList"
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { useToast } from "@/hooks/use-toast"
import type { User } from "@/types/auth.types"
import { Check, Copy, KeyRound, Pencil, Plus, Upload, Download } from "lucide-react"
import { MasterDataImportWizard } from "@/components/data/MasterDataImportWizard"
import apiClient from "@/services/api-client"

type SupplierFormState = {
  code: string
  name: string
  contact_person: string
  email: string
  phone: string
  address: string
  gst: string
  payment_terms: string
}

type PortalCredentials = {
  email: string
  password: string
}

const emptySupplierForm: SupplierFormState = {
  code: "",
  name: "",
  contact_person: "",
  email: "",
  phone: "",
  address: "",
  gst: "",
  payment_terms: "",
}

const clean = (value: string) => value.trim() || undefined

const supplierToForm = (supplier: Supplier): SupplierFormState => ({
  code: supplier.code,
  name: supplier.name,
  contact_person: supplier.contact_person || "",
  email: supplier.email || "",
  phone: supplier.phone || "",
  address: supplier.address || "",
  gst: supplier.gst || "",
  payment_terms: supplier.payment_terms || "",
})

const portalUserName = (form: SupplierFormState) => {
  const source = clean(form.contact_person) || clean(form.name) || "Supplier Portal"
  const parts = source.split(/\s+/).filter(Boolean)

  return {
    first_name: parts[0] || "Supplier",
    last_name: parts.slice(1).join(" ") || "Portal",
  }
}

export default function SuppliersListPage() {
  const { toast } = useToast()
  const supplierLoginUrl = `${window.location.origin}/login`
  const [items, setItems] = useState<Supplier[]>([])
  const [form, setForm] = useState<SupplierFormState>(emptySupplierForm)
  const [open, setOpen] = useState(false)
  const [createPortalUser, setCreatePortalUser] = useState(false)
  const [portalCredentials, setPortalCredentials] = useState<PortalCredentials | null>(null)
  const [copiedCredentials, setCopiedCredentials] = useState(false)
  const [saving, setSaving] = useState(false)
  const [supplierUsers, setSupplierUsers] = useState<User[]>([])
  const [portalSavingSupplierId, setPortalSavingSupplierId] = useState<string | null>(null)
  const [showImportDialog, setShowImportDialog] = useState(false)

  const handleExport = async () => {
    try {
      const response = await apiClient.get('/suppliers/export', { responseType: 'blob' })
      const url = window.URL.createObjectURL(new Blob([response.data]))
      const link = document.createElement('a')
      link.href = url
      link.setAttribute('download', 'suppliers_export.xlsx')
      document.body.appendChild(link)
      link.click()
      link.remove()
    } catch (err: any) {
      toast({ title: 'Export failed', description: err.message, variant: 'destructive' })
    }
  }

  const [editOpen, setEditOpen] = useState(false)
  const [editing, setEditing] = useState<Supplier | null>(null)
  const [editForm, setEditForm] = useState<SupplierFormState>(emptySupplierForm)
  const [editActive, setEditActive] = useState(true)

  const loadSuppliers = () => supplyChainApi.listSuppliers().then((r) => setItems(r.data))
  const loadSupplierUsers = () => usersService.getUsers({ role: "supplier" }).then(setSupplierUsers)
  const refresh = async () => {
    await Promise.all([loadSuppliers(), loadSupplierUsers()])
  }

  useEffect(() => {
    refresh().catch(() => toast({ title: "Failed to load suppliers", variant: "destructive" }))
  }, [toast])

  const updateCreateField = (field: keyof SupplierFormState, value: string) => {
    setForm((current) => ({ ...current, [field]: value }))
  }

  const updateEditField = (field: keyof SupplierFormState, value: string) => {
    setEditForm((current) => ({ ...current, [field]: value }))
  }

  const resetCreateDialog = () => {
    setForm(emptySupplierForm)
    setCreatePortalUser(false)
    setPortalCredentials(null)
    setCopiedCredentials(false)
  }

  const handleCreateOpenChange = (nextOpen: boolean) => {
    setOpen(nextOpen)
    if (!nextOpen) {
      resetCreateDialog()
    }
  }

  const copyPortalCredentials = async () => {
    if (!portalCredentials) return

    await navigator.clipboard.writeText(
      [
        "Supplier portal login",
        `URL: ${supplierLoginUrl}`,
        `Email: ${portalCredentials.email}`,
        `Temporary password: ${portalCredentials.password}`,
      ].join("\n")
    )
    setCopiedCredentials(true)
    setTimeout(() => setCopiedCredentials(false), 2000)
  }

  const create = async () => {
    if (!clean(form.name)) {
      toast({ title: "Supplier name is required", variant: "destructive" })
      return
    }

    if (createPortalUser && !clean(form.email)) {
      toast({ title: "Email is required to create supplier login", variant: "destructive" })
      return
    }

    try {
      setSaving(true)
      const supplierResponse = await supplyChainApi.createSupplier({
        code: form.code.trim(),
        name: form.name.trim(),
        contact_person: clean(form.contact_person),
        email: clean(form.email),
        phone: clean(form.phone),
        address: clean(form.address),
        gst: clean(form.gst),
        payment_terms: clean(form.payment_terms),
      })

      if (createPortalUser) {
        const names = portalUserName(form)
        const createdUser = await usersService.createUser({
          email: form.email.trim(),
          first_name: names.first_name,
          last_name: names.last_name,
          role: "supplier",
          supplier_id: supplierResponse.data.id,
          is_active: true,
        })

        if (createdUser.temporary_password) {
          setPortalCredentials({
            email: createdUser.email,
            password: createdUser.temporary_password,
          })
        }
      } else {
        handleCreateOpenChange(false)
      }

      await refresh()
      toast({
        title: createPortalUser ? "Supplier and portal login created" : "Supplier created",
        description: createPortalUser
          ? "Copy the temporary password below and share it securely with the supplier."
          : undefined,
      })
    } catch (error: any) {
      toast({
        title: "Create failed",
        description: error?.response?.data?.detail || error?.message || "Unable to create supplier",
        variant: "destructive",
      })
    } finally {
      setSaving(false)
    }
  }

  const openEdit = (supplier: Supplier) => {
    setEditing(supplier)
    setEditForm(supplierToForm(supplier))
    setEditActive(supplier.is_active)
    setEditOpen(true)
  }

  const saveEdit = async () => {
    if (!editing) return

    try {
      await supplyChainApi.updateSupplier(editing.id, {
        name: editForm.name.trim(),
        contact_person: clean(editForm.contact_person),
        email: clean(editForm.email),
        phone: clean(editForm.phone),
        address: clean(editForm.address),
        gst: clean(editForm.gst),
        payment_terms: clean(editForm.payment_terms),
        is_active: editActive,
      })
      toast({ title: "Supplier updated" })
      setEditOpen(false)
      await refresh()
    } catch (error: any) {
      toast({
        title: "Update failed",
        description: error?.response?.data?.detail || error?.message || "Unable to update supplier",
        variant: "destructive",
      })
    }
  }

  const supplierUserBySupplierId = new Map(
    supplierUsers
      .filter((user) => user.supplier_id)
      .map((user) => [user.supplier_id as string, user])
  )

  const createPortalLogin = async (supplier: Supplier) => {
    if (!supplier.email) {
      toast({ title: "Supplier email is required before creating portal login", variant: "destructive" })
      return
    }

    const supplierForm = supplierToForm(supplier)
    const names = portalUserName(supplierForm)
    try {
      setPortalSavingSupplierId(supplier.id)
      const createdUser = await usersService.createUser({
        email: supplier.email,
        first_name: names.first_name,
        last_name: names.last_name,
        role: "supplier",
        supplier_id: supplier.id,
        is_active: true,
      })

      if (createdUser.temporary_password) {
        setPortalCredentials({
          email: createdUser.email,
          password: createdUser.temporary_password,
        })
      }
      await refresh()
      toast({
        title: "Supplier portal login created",
        description: "Copy the temporary password and share it securely with the supplier.",
      })
    } catch (error: any) {
      toast({
        title: "Portal login failed",
        description: error?.response?.data?.detail || error?.message || "Unable to create supplier portal login",
        variant: "destructive",
      })
    } finally {
      setPortalSavingSupplierId(null)
    }
  }

  const resetPortalPassword = async (supplier: Supplier, supplierUser: User) => {
    try {
      setPortalSavingSupplierId(supplier.id)
      const response = await usersService.resetTemporaryPassword(supplierUser.id)
      setPortalCredentials({
        email: response.email,
        password: response.temporary_password,
      })
      toast({
        title: "Temporary password regenerated",
        description: "Copy it now. The supplier's previous password will no longer work.",
      })
    } catch (error: any) {
      toast({
        title: "Password reset failed",
        description: error?.response?.data?.detail || error?.message || "Unable to reset supplier password",
        variant: "destructive",
      })
    } finally {
      setPortalSavingSupplierId(null)
    }
  }

  return (
    <div className="space-y-6 max-w-6xl">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-semibold">Suppliers</h1>
          <p className="text-sm text-muted-foreground">
            Manage supplier master data and create portal access for purchase order collaboration.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" onClick={handleExport}>
            <Download className="mr-2 h-4 w-4" />
            Export
          </Button>

          <Dialog open={showImportDialog} onOpenChange={setShowImportDialog}>
            <DialogTrigger asChild>
              <Button variant="outline">
                <Upload className="mr-2 h-4 w-4" />
                Import
              </Button>
            </DialogTrigger>
            <DialogContent className="max-w-2xl">
              <MasterDataImportWizard 
                moduleName="suppliers"
                apiPrefix="/suppliers"
                onCancel={() => setShowImportDialog(false)}
                onComplete={() => {
                  setShowImportDialog(false)
                  refresh()
                }}
              />
            </DialogContent>
          </Dialog>

          <Dialog open={open} onOpenChange={handleCreateOpenChange}>
            <DialogTrigger asChild>
              <Button>
                <Plus className="mr-2 h-4 w-4" />
                Add supplier
              </Button>
            </DialogTrigger>
          <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-2xl">
            <DialogHeader>
              <DialogTitle>New supplier</DialogTitle>
            </DialogHeader>
            <div className="space-y-4 py-2">
              <Alert className="border-blue-200 bg-blue-50 text-blue-950">
                <KeyRound className="h-4 w-4" />
                <AlertTitle>Supplier login details</AlertTitle>
                <AlertDescription>
                  Supplier master data does not automatically create a login. Enable portal access below to create a
                  linked supplier user and generate the one-time temporary password.
                </AlertDescription>
              </Alert>

              <div className="grid gap-4 sm:grid-cols-2">
                <div className="space-y-2">
                  <Label htmlFor="supplier-code">Supplier code (optional)</Label>
                  <Input
                    id="supplier-code"
                    value={form.code}
                    onChange={(event) => updateCreateField("code", event.target.value)}
                    placeholder="SUP-001"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="supplier-name">Legal / trade name *</Label>
                  <Input
                    id="supplier-name"
                    value={form.name}
                    onChange={(event) => updateCreateField("name", event.target.value)}
                    placeholder="Acme Packaging Pvt Ltd"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="supplier-contact">Contact person</Label>
                  <Input
                    id="supplier-contact"
                    value={form.contact_person}
                    onChange={(event) => updateCreateField("contact_person", event.target.value)}
                    placeholder="Procurement contact"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="supplier-email">Email {createPortalUser ? "*" : ""}</Label>
                  <Input
                    id="supplier-email"
                    type="email"
                    value={form.email}
                    onChange={(event) => updateCreateField("email", event.target.value)}
                    placeholder="supplier@example.com"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="supplier-phone">Phone</Label>
                  <Input
                    id="supplier-phone"
                    value={form.phone}
                    onChange={(event) => updateCreateField("phone", event.target.value)}
                    placeholder="+91 98765 43210"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="supplier-gst">GST / tax ID</Label>
                  <Input
                    id="supplier-gst"
                    value={form.gst}
                    onChange={(event) => updateCreateField("gst", event.target.value)}
                    placeholder="27ABCDE1234F1Z5"
                  />
                </div>
                <div className="space-y-2 sm:col-span-2">
                  <Label htmlFor="supplier-payment-terms">Payment terms</Label>
                  <Input
                    id="supplier-payment-terms"
                    value={form.payment_terms}
                    onChange={(event) => updateCreateField("payment_terms", event.target.value)}
                    placeholder="Net 30, advance, milestone, etc."
                  />
                </div>
                <div className="space-y-2 sm:col-span-2">
                  <Label htmlFor="supplier-address">Registered address</Label>
                  <Textarea
                    id="supplier-address"
                    value={form.address}
                    onChange={(event) => updateCreateField("address", event.target.value)}
                    placeholder="Billing and dispatch address"
                  />
                </div>
              </div>

              <div className="flex items-start gap-3 rounded-md border p-3">
                <Checkbox
                  id="supplier-portal-user"
                  checked={createPortalUser}
                  onCheckedChange={(value) => setCreatePortalUser(value === true)}
                />
                <div className="space-y-1">
                  <Label htmlFor="supplier-portal-user">Create supplier portal login now</Label>
                  <p className="text-xs text-muted-foreground">
                    This creates a `supplier` role user linked to this supplier. Share the generated temporary password
                    with the supplier so they can log in from the main ERP login page.
                  </p>
                </div>
              </div>

              {portalCredentials && (
                <Alert className="border-green-200 bg-green-50 text-green-950">
                  <KeyRound className="h-4 w-4" />
                  <AlertTitle>Portal credentials generated</AlertTitle>
                  <AlertDescription>
                    <div className="mt-2 space-y-2">
                      <p>The password is shown only once. Copy and share it securely with the supplier.</p>
                      <div className="rounded-md border bg-white p-3 text-sm">
                        <div>
                          <span className="font-medium">Login URL:</span>{" "}
                          <a className="text-blue-700 underline" href="/login">
                            {supplierLoginUrl}
                          </a>
                        </div>
                        <div>
                          <span className="font-medium">Email:</span> {portalCredentials.email}
                        </div>
                        <div>
                          <span className="font-medium">Temporary password:</span>{" "}
                          <code>{portalCredentials.password}</code>
                        </div>
                      </div>
                      <Button type="button" variant="outline" size="sm" onClick={copyPortalCredentials}>
                        {copiedCredentials ? <Check className="mr-2 h-4 w-4" /> : <Copy className="mr-2 h-4 w-4" />}
                        {copiedCredentials ? "Copied" : "Copy credentials"}
                      </Button>
                    </div>
                  </AlertDescription>
                </Alert>
              )}
            </div>
            <DialogFooter>
              {portalCredentials ? (
                <Button onClick={() => handleCreateOpenChange(false)}>Done</Button>
              ) : (
                <Button onClick={create} disabled={saving}>
                  {saving ? "Saving..." : "Save supplier"}
                </Button>
              )}
            </DialogFooter>
          </DialogContent>
        </Dialog>
        </div>
      </div>

      <Alert>
        <KeyRound className="h-4 w-4" />
        <AlertTitle>Business workflow</AlertTitle>
        <AlertDescription>
          Create the supplier master first, then create a linked supplier user for portal access. The linked user is
          what lets the supplier view POs, submit quotes, and acknowledge orders without seeing admin screens.
        </AlertDescription>
      </Alert>

      {portalCredentials && !open && (
        <Alert className="border-green-200 bg-green-50 text-green-950">
          <KeyRound className="h-4 w-4" />
          <AlertTitle>Portal credentials ready</AlertTitle>
          <AlertDescription>
            <div className="mt-2 space-y-2">
              <p>The password is shown only once. Copy and share it securely with the supplier.</p>
              <div className="rounded-md border bg-white p-3 text-sm">
                <div>
                  <span className="font-medium">Login URL:</span>{" "}
                  <a className="text-blue-700 underline" href="/login">
                    {supplierLoginUrl}
                  </a>
                </div>
                <div>
                  <span className="font-medium">Email:</span> {portalCredentials.email}
                </div>
                <div>
                  <span className="font-medium">Temporary password:</span>{" "}
                  <code>{portalCredentials.password}</code>
                </div>
              </div>
              <Button type="button" variant="outline" size="sm" onClick={copyPortalCredentials}>
                {copiedCredentials ? <Check className="mr-2 h-4 w-4" /> : <Copy className="mr-2 h-4 w-4" />}
                {copiedCredentials ? "Copied" : "Copy credentials"}
              </Button>
            </div>
          </AlertDescription>
        </Alert>
      )}

      <ResponsiveDataList
        data={items}
        getRowKey={(supplier) => supplier.id}
        columns={[
          { key: "code", header: "Code", cell: (supplier) => <span className="font-medium">{supplier.code}</span> },
          { key: "name", header: "Name", cell: (supplier) => supplier.name },
          { key: "contact", header: "Contact", cell: (supplier) => supplier.contact_person || "-" },
          { key: "email", header: "Email", cell: (supplier) => supplier.email || "-" },
          { key: "phone", header: "Phone", cell: (supplier) => supplier.phone || "-" },
          { key: "payment_terms", header: "Payment terms", cell: (supplier) => supplier.payment_terms || "-" },
          {
            key: "portal_access",
            header: "Portal access",
            cell: (supplier) => {
              const supplierUser = supplierUserBySupplierId.get(supplier.id)
              const portalActionLoading = portalSavingSupplierId === supplier.id
              return supplierUser ? (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={(event) => {
                    event.stopPropagation()
                    void resetPortalPassword(supplier, supplierUser)
                  }}
                  disabled={portalActionLoading}
                >
                  <KeyRound className="mr-2 h-4 w-4" />
                  {portalActionLoading ? "Generating..." : "Reset password"}
                </Button>
              ) : (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={(event) => {
                    event.stopPropagation()
                    void createPortalLogin(supplier)
                  }}
                  disabled={portalActionLoading || !supplier.email}
                >
                  <KeyRound className="mr-2 h-4 w-4" />
                  {portalActionLoading ? "Creating..." : "Create login"}
                </Button>
              )
            },
          },
          { key: "active", header: "Active", cell: (supplier) => (supplier.is_active ? "Yes" : "No") },
          {
            key: "actions",
            header: "",
            headerClassName: "text-right",
            className: "text-right",
            cell: (supplier) => (
              <Button variant="ghost" size="icon" onClick={(event) => { event.stopPropagation(); openEdit(supplier) }} aria-label="Edit supplier">
                <Pencil className="h-4 w-4" />
              </Button>
            ),
          },
        ]}
        renderMobileCard={(supplier) => {
          const supplierUser = supplierUserBySupplierId.get(supplier.id)
          const portalActionLoading = portalSavingSupplierId === supplier.id
          return (
            <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm transition-all hover:shadow-md">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <p className="text-base font-semibold text-slate-900">{supplier.name}</p>
                  <p className="mt-1 text-xs font-mono text-slate-500">{supplier.code}</p>
                </div>
                <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-medium text-slate-700">
                  {supplier.is_active ? "Active" : "Inactive"}
                </span>
              </div>
              <div className="mt-4 space-y-2 text-sm">
                <div className="flex items-center justify-between gap-3">
                  <span className="text-slate-500">Contact</span>
                  <span>{supplier.contact_person || "-"}</span>
                </div>
                <div className="flex items-center justify-between gap-3">
                  <span className="text-slate-500">Email</span>
                  <span className="text-right">{supplier.email || "-"}</span>
                </div>
                <div className="flex items-center justify-between gap-3">
                  <span className="text-slate-500">Phone</span>
                  <span>{supplier.phone || "-"}</span>
                </div>
                <div className="flex items-center justify-between gap-3">
                  <span className="text-slate-500">Payment terms</span>
                  <span>{supplier.payment_terms || "-"}</span>
                </div>
              </div>
              <div className="mt-4 flex flex-col gap-2">
                {supplierUser ? (
                  <Button
                    variant="outline"
                    className="w-full"
                    onClick={() => void resetPortalPassword(supplier, supplierUser)}
                    disabled={portalActionLoading}
                  >
                    <KeyRound className="mr-2 h-4 w-4" />
                    {portalActionLoading ? "Generating..." : "Reset password"}
                  </Button>
                ) : (
                  <Button
                    variant="outline"
                    className="w-full"
                    onClick={() => void createPortalLogin(supplier)}
                    disabled={portalActionLoading || !supplier.email}
                  >
                    <KeyRound className="mr-2 h-4 w-4" />
                    {portalActionLoading ? "Creating..." : "Create login"}
                  </Button>
                )}
                <Button variant="outline" className="w-full" onClick={() => openEdit(supplier)}>
                  <Pencil className="mr-2 h-4 w-4" />
                  Edit supplier
                </Button>
              </div>
            </div>
          )
        }}
      />

      <Dialog open={editOpen} onOpenChange={setEditOpen}>
        <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-2xl">
          <DialogHeader>
            <DialogTitle>Edit supplier</DialogTitle>
          </DialogHeader>
          {editing && (
            <div className="space-y-4 py-2">
              <p className="text-sm text-muted-foreground font-mono">{editing.code}</p>
              <div className="grid gap-4 sm:grid-cols-2">
                <div className="space-y-2 sm:col-span-2">
                  <Label htmlFor="edit-supplier-name">Legal / trade name</Label>
                  <Input
                    id="edit-supplier-name"
                    value={editForm.name}
                    onChange={(event) => updateEditField("name", event.target.value)}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="edit-supplier-contact">Contact person</Label>
                  <Input
                    id="edit-supplier-contact"
                    value={editForm.contact_person}
                    onChange={(event) => updateEditField("contact_person", event.target.value)}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="edit-supplier-email">Email</Label>
                  <Input
                    id="edit-supplier-email"
                    type="email"
                    value={editForm.email}
                    onChange={(event) => updateEditField("email", event.target.value)}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="edit-supplier-phone">Phone</Label>
                  <Input
                    id="edit-supplier-phone"
                    value={editForm.phone}
                    onChange={(event) => updateEditField("phone", event.target.value)}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="edit-supplier-gst">GST / tax ID</Label>
                  <Input
                    id="edit-supplier-gst"
                    value={editForm.gst}
                    onChange={(event) => updateEditField("gst", event.target.value)}
                  />
                </div>
                <div className="space-y-2 sm:col-span-2">
                  <Label htmlFor="edit-supplier-payment-terms">Payment terms</Label>
                  <Input
                    id="edit-supplier-payment-terms"
                    value={editForm.payment_terms}
                    onChange={(event) => updateEditField("payment_terms", event.target.value)}
                  />
                </div>
                <div className="space-y-2 sm:col-span-2">
                  <Label htmlFor="edit-supplier-address">Registered address</Label>
                  <Textarea
                    id="edit-supplier-address"
                    value={editForm.address}
                    onChange={(event) => updateEditField("address", event.target.value)}
                  />
                </div>
              </div>
              <div className="flex items-center gap-2">
                <Checkbox id="active" checked={editActive} onCheckedChange={(value) => setEditActive(!!value)} />
                <Label htmlFor="active">Active</Label>
              </div>
              <p className="text-xs text-muted-foreground">
                Use the Portal access action in the supplier list to create or regenerate this supplier's one-time
                temporary password.
              </p>
            </div>
          )}
          <DialogFooter>
            <Button onClick={saveEdit}>Save changes</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
