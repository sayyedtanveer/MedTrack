import { useMemo, useState } from "react"
import { useMutation } from "@tanstack/react-query"
import { useNavigate, useSearchParams } from "react-router-dom"
import {
  ArrowRight,
  BadgeCheck,
  Building2,
  CreditCard,
  Eye,
  EyeOff,
  FileDown,
  KeyRound,
  LockKeyhole,
  Mail,
  Route,
  ShieldCheck,
} from "lucide-react"
import { useAuthStore } from "@/app/store/authStore"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { cn } from "@/lib/utils"
import { clientService } from "../services/client.service"

type Mode = "login" | "forgot" | "reset"

const getErrorMessage = (error: any, fallback: string) =>
  error?.response?.data?.detail || error?.message || fallback

const isValidEmail = (value: string) => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value)

const modeTabs: Array<{ value: Mode; label: string }> = [
  { value: "login", label: "Login" },
  { value: "forgot", label: "Forgot" },
  { value: "reset", label: "Reset" },
]

const featureCards = [
  { label: "Order timeline", helper: "Live progress", icon: Route },
  { label: "Invoice download", helper: "Ready documents", icon: FileDown },
  { label: "Credit alerts", helper: "Balance visibility", icon: CreditCard },
]

const modeContent: Record<Mode, { title: string; description: string }> = {
  login: {
    title: "Client Access",
    description: "Sign in with your client role account to continue.",
  },
  forgot: {
    title: "Recover Access",
    description: "Request reset instructions for a client portal account.",
  },
  reset: {
    title: "Set New Password",
    description: "Use your reset token to update your client password.",
  },
}

export default function ClientLogin() {
  const [searchParams, setSearchParams] = useSearchParams()
  const navigate = useNavigate()
  const erpLoginUrl = `${window.location.origin}/login`
  const { setAuth, setUser, setPermissions, setSupplierAndClient } = useAuthStore()
  const [loginForm, setLoginForm] = useState({ email: "", password: "", tenant_id: "" })
  const [forgotForm, setForgotForm] = useState({ email: "", tenant_id: "" })
  const [resetForm, setResetForm] = useState({ token: searchParams.get("token") ?? "", new_password: "" })
  const [message, setMessage] = useState<string | null>(null)
  const [showLoginPassword, setShowLoginPassword] = useState(false)
  const [showResetPassword, setShowResetPassword] = useState(false)

  const mode = useMemo<Mode>(() => {
    const raw = searchParams.get("mode")
    return raw === "forgot" || raw === "reset" ? raw : "login"
  }, [searchParams])

  const loginMutation = useMutation({
    mutationFn: clientService.login,
    onSuccess: async (session) => {
      setAuth(session.access_token, session.tenant_id)
      setSupplierAndClient(null, session.client_id)
      setPermissions(["client:read", "sales:read", "sales:view_orders", "sales:create_order", "inventory:read"])
      try {
        const profile = await clientService.getProfile()
        setUser({
          id: profile.contact.id,
          email: profile.contact.email,
          first_name: profile.contact.first_name,
          last_name: profile.contact.last_name,
          role: "CLIENT",
          client_id: session.client_id,
          tenant_id: session.tenant_id,
          is_active: true,
        })
      } catch {
        const names = session.full_name.split(" ")
        setUser({
          id: session.user_id,
          email: session.email,
          first_name: names[0] ?? "Client",
          last_name: names.slice(1).join(" "),
          role: "CLIENT",
          client_id: session.client_id,
          tenant_id: session.tenant_id,
          is_active: true,
        })
      }
      navigate("/client", { replace: true })
    },
    onError: (error: any) => {
      const message = getErrorMessage(error, "Unable to sign in.")
      setMessage(
        `${message}. This page accepts client users only. Supplier and admin users must sign in at ${erpLoginUrl}.`
      )
    },
  })

  const forgotMutation = useMutation({
    mutationFn: clientService.forgotPassword,
    onSuccess: (data) => {
      const token = data.reset_token?.trim()
      if (token) {
        setMessage("Development reset token generated and filled below.")
        setResetForm((current) => ({ ...current, token }))
        setSearchParams({ mode: "reset", token })
        return
      }

      setMessage(`${data.message} Supplier and internal users should use the main ERP login page.`)
      setSearchParams({ mode: "forgot" })
    },
    onError: (error: any) => setMessage(getErrorMessage(error, "Unable to start password reset.")),
  })

  const resetMutation = useMutation({
    mutationFn: clientService.resetPassword,
    onSuccess: (data) => {
      setMessage(data.message)
      setSearchParams({ mode: "login" })
      setResetForm({ token: "", new_password: "" })
    },
    onError: (error: any) => setMessage(getErrorMessage(error, "Unable to reset password.")),
  })

  const setMode = (nextMode: Mode) => {
    setMessage(null)
    if (nextMode === "login") {
      setSearchParams({})
      return
    }

    if (nextMode === "reset" && resetForm.token.trim()) {
      setSearchParams({ mode: nextMode, token: resetForm.token.trim() })
      return
    }

    setSearchParams({ mode: nextMode })
  }

  const activeModeContent = modeContent[mode]

  return (
    <div className="min-h-[100svh] overflow-x-hidden bg-[radial-gradient(circle_at_top_left,#dbeafe_0%,#fff7ed_38%,#ffffff_100%)] px-3 py-4 sm:px-4 sm:py-8 lg:py-12">
      <div className="mx-auto flex w-full max-w-5xl flex-col gap-4 md:grid md:grid-cols-[1.08fr_0.92fr] md:items-stretch md:gap-8">
        <section className="order-2 rounded-[24px] border border-white/70 bg-white/75 p-5 shadow-xl shadow-slate-900/10 backdrop-blur md:order-1 md:rounded-[32px] md:p-8">
          <p className="text-[11px] font-semibold uppercase tracking-[0.28em] text-slate-500">MedTrack Client Portal</p>
          <h1 className="mt-3 text-2xl font-semibold leading-tight text-slate-950 sm:text-4xl">
            Track orders, download invoices, and reorder from one client workspace.
          </h1>
          <p className="mt-3 max-w-xl text-sm leading-6 text-slate-600 sm:text-base">
              Use your dedicated client account to follow delivery progress, monitor credit usage, manage addresses, and reach support without touching the internal ERP.
          </p>
          <div className="mt-5 grid gap-2 sm:grid-cols-3 md:mt-8 md:gap-4">
            {featureCards.map((item) => {
              const Icon = item.icon
              return (
                <div key={item.label} className="flex items-center gap-3 rounded-2xl bg-slate-950 px-4 py-3 text-white md:block md:p-5">
                  <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-white/10">
                    <Icon className="h-4 w-4" />
                  </span>
                  <span className="min-w-0">
                    <span className="block text-sm font-semibold">{item.label}</span>
                    <span className="block text-xs text-slate-300">{item.helper}</span>
                  </span>
                </div>
              )
            })}
          </div>
        </section>

        <Card data-client-login-card className="order-1 overflow-hidden rounded-[24px] border-white/80 bg-white/95 shadow-2xl shadow-slate-900/15 md:order-2 md:rounded-[32px]">
          <CardHeader className="space-y-4 p-5 pb-3 sm:p-6">
            <div className="flex items-start gap-3">
              <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl bg-blue-50 text-blue-700">
                <ShieldCheck className="h-5 w-5" />
              </span>
              <div className="min-w-0">
                <CardTitle className="text-2xl leading-7 text-slate-950">{activeModeContent.title}</CardTitle>
                <CardDescription className="mt-1 text-sm leading-5 text-slate-600">
                  {activeModeContent.description} Supplier and admin users use{" "}
                  <a className="font-medium text-blue-700 underline-offset-4 hover:underline" href="/login" title={erpLoginUrl}>
                    main ERP login
                  </a>
                  .
                </CardDescription>
              </div>
            </div>

            <div className="grid grid-cols-3 rounded-2xl bg-slate-100 p-1">
              {modeTabs.map((tab) => (
                <button
                  key={tab.value}
                  type="button"
                  aria-pressed={mode === tab.value}
                  onClick={() => setMode(tab.value)}
                  className={cn(
                    "h-10 rounded-xl px-2 text-sm font-semibold text-slate-600 transition-all",
                    mode === tab.value
                      ? "bg-white text-blue-700 shadow-sm"
                      : "hover:bg-white/60 hover:text-slate-900"
                  )}
                >
                  {tab.label}
                </button>
              ))}
            </div>
          </CardHeader>
          <CardContent className="space-y-4 p-5 pt-2 sm:p-6 sm:pt-2">
            {message && (
              <div className="rounded-2xl border border-blue-100 bg-blue-50 px-4 py-3 text-sm leading-5 text-slate-700">
                {message}
              </div>
            )}

            {mode === "login" && (
              <form
                className="space-y-4"
                onSubmit={(event) => {
                  event.preventDefault()
                  if (!isValidEmail(loginForm.email)) {
                    setMessage("Please enter a valid email address before signing in.")
                    return
                  }
                  loginMutation.mutate(loginForm)
                }}
              >
                <div className="space-y-2">
                  <Label htmlFor="client-email">Email</Label>
                  <div className="relative">
                    <Mail className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
                    <Input
                      id="client-email"
                      type="email"
                      autoComplete="email"
                      value={loginForm.email}
                      onChange={(event) => setLoginForm({ ...loginForm, email: event.target.value })}
                      className="h-12 rounded-2xl bg-slate-50 pl-10 text-base shadow-sm focus-visible:bg-white"
                    />
                  </div>
                  {!isValidEmail(loginForm.email) && loginForm.email.trim() !== "" && (
                    <p className="text-sm font-medium text-destructive">Please enter a valid email address.</p>
                  )}
                </div>
                <div className="space-y-2">
                  <Label htmlFor="client-password">Password</Label>
                  <div className="relative">
                    <LockKeyhole className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
                    <Input
                      id="client-password"
                      type={showLoginPassword ? "text" : "password"}
                      autoComplete="current-password"
                      value={loginForm.password}
                      onChange={(event) => setLoginForm({ ...loginForm, password: event.target.value })}
                      className="h-12 rounded-2xl bg-slate-50 pl-10 pr-12 text-base shadow-sm focus-visible:bg-white"
                    />
                    <button
                      type="button"
                      onClick={() => setShowLoginPassword((visible) => !visible)}
                      className="absolute right-2 top-1/2 flex h-9 w-9 -translate-y-1/2 items-center justify-center rounded-xl text-slate-500 transition hover:bg-slate-100 hover:text-slate-900"
                      aria-label={showLoginPassword ? "Hide password" : "Show password"}
                    >
                      {showLoginPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                    </button>
                  </div>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="client-tenant">Tenant ID</Label>
                  <div className="relative">
                    <Building2 className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
                    <Input
                      id="client-tenant"
                      value={loginForm.tenant_id}
                      onChange={(event) => setLoginForm({ ...loginForm, tenant_id: event.target.value })}
                      placeholder="Workspace UUID"
                      autoComplete="off"
                      className="h-12 rounded-2xl bg-slate-50 pl-10 text-base shadow-sm focus-visible:bg-white"
                    />
                  </div>
                </div>
                <Button type="submit" className="h-12 w-full rounded-2xl text-base font-semibold shadow-lg shadow-blue-600/20 transition-all hover:-translate-y-0.5" disabled={loginMutation.isPending}>
                  {loginMutation.isPending ? "Signing In..." : "Enter Client Portal"}
                  {!loginMutation.isPending && <ArrowRight className="h-4 w-4" />}
                </Button>
              </form>
            )}

            {mode === "forgot" && (
              <form
                className="space-y-4"
                onSubmit={(event) => {
                  event.preventDefault()
                  if (!isValidEmail(forgotForm.email)) {
                    setMessage("Please enter a valid email address before requesting a reset.")
                    return
                  }
                  forgotMutation.mutate(forgotForm)
                }}
              >
                <div className="space-y-2">
                  <Label htmlFor="forgot-email">Email</Label>
                  <div className="relative">
                    <Mail className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
                    <Input
                      id="forgot-email"
                      type="email"
                      autoComplete="email"
                      value={forgotForm.email}
                      onChange={(event) => setForgotForm({ ...forgotForm, email: event.target.value })}
                      className="h-12 rounded-2xl bg-slate-50 pl-10 text-base shadow-sm focus-visible:bg-white"
                    />
                  </div>
                  {!isValidEmail(forgotForm.email) && forgotForm.email.trim() !== "" && (
                    <p className="text-sm font-medium text-destructive">Please enter a valid email address.</p>
                  )}
                </div>
                <div className="space-y-2">
                  <Label htmlFor="forgot-tenant">Tenant ID</Label>
                  <div className="relative">
                    <Building2 className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
                    <Input
                      id="forgot-tenant"
                      value={forgotForm.tenant_id}
                      onChange={(event) => setForgotForm({ ...forgotForm, tenant_id: event.target.value })}
                      placeholder="Workspace UUID"
                      autoComplete="off"
                      className="h-12 rounded-2xl bg-slate-50 pl-10 text-base shadow-sm focus-visible:bg-white"
                    />
                  </div>
                </div>
                <Button type="submit" className="h-12 w-full rounded-2xl text-base font-semibold shadow-lg shadow-blue-600/20 transition-all hover:-translate-y-0.5" disabled={forgotMutation.isPending}>
                  {forgotMutation.isPending ? "Generating..." : "Send Reset Instructions"}
                  {!forgotMutation.isPending && <ArrowRight className="h-4 w-4" />}
                </Button>
              </form>
            )}

            {mode === "reset" && (
              <form
                className="space-y-4"
                onSubmit={(event) => {
                  event.preventDefault()
                  const token = resetForm.token.trim()
                  const newPassword = resetForm.new_password.trim()

                  if (!token) {
                    setMessage("Paste the reset token from the reset instructions before setting a new password.")
                    return
                  }

                  if (/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(token)) {
                    setMessage("That looks like an email address. The reset token is the long secure token from the reset instructions.")
                    return
                  }

                  if (newPassword.length < 8) {
                    setMessage("New password must be at least 8 characters.")
                    return
                  }

                  resetMutation.mutate({ token, new_password: newPassword })
                }}
              >
                <div className="space-y-2">
                  <Label htmlFor="reset-token">Reset Token</Label>
                  <div className="relative">
                    <KeyRound className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
                    <Input
                      id="reset-token"
                      value={resetForm.token}
                      onChange={(event) => setResetForm({ ...resetForm, token: event.target.value })}
                      className="h-12 rounded-2xl bg-slate-50 pl-10 text-base shadow-sm focus-visible:bg-white"
                    />
                  </div>
                  <p className="flex items-start gap-2 text-xs leading-5 text-slate-500">
                    <BadgeCheck className="mt-0.5 h-3.5 w-3.5 shrink-0 text-blue-600" />
                    Use the reset token, not the email address. Suppliers use /login, not the client portal.
                  </p>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="reset-password">New Password</Label>
                  <div className="relative">
                    <LockKeyhole className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
                    <Input
                      id="reset-password"
                      type={showResetPassword ? "text" : "password"}
                      autoComplete="new-password"
                      value={resetForm.new_password}
                      onChange={(event) => setResetForm({ ...resetForm, new_password: event.target.value })}
                      className="h-12 rounded-2xl bg-slate-50 pl-10 pr-12 text-base shadow-sm focus-visible:bg-white"
                    />
                    <button
                      type="button"
                      onClick={() => setShowResetPassword((visible) => !visible)}
                      className="absolute right-2 top-1/2 flex h-9 w-9 -translate-y-1/2 items-center justify-center rounded-xl text-slate-500 transition hover:bg-slate-100 hover:text-slate-900"
                      aria-label={showResetPassword ? "Hide password" : "Show password"}
                    >
                      {showResetPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                    </button>
                  </div>
                </div>
                <Button type="submit" className="h-12 w-full rounded-2xl text-base font-semibold shadow-lg shadow-blue-600/20 transition-all hover:-translate-y-0.5" disabled={resetMutation.isPending}>
                  {resetMutation.isPending ? "Updating..." : "Set New Password"}
                  {!resetMutation.isPending && <ArrowRight className="h-4 w-4" />}
                </Button>
              </form>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
