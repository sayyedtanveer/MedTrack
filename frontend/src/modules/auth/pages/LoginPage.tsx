import { useState } from "react"
import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import { Link } from "react-router-dom"
import { type LoginFormValues, loginSchema } from "@/lib/validations"
import { useAuth } from "@/hooks/useAuth"

import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card"
import ForgotPasswordModal from "@/modules/auth/components/ForgotPasswordModal"

export default function LoginPage() {
  const { login, isLoggingIn } = useAuth()
  const [showForgotPassword, setShowForgotPassword] = useState(false)

  const form = useForm<LoginFormValues>({
    resolver: zodResolver(loginSchema),
    defaultValues: {
      email: "",
      password: "",
      tenant_id: "", // Optional in Phase 0 backend if it can resolve via email
    },
  })

  const onSubmit = (data: LoginFormValues) => {
    login(data)
  }

  return (
    <Card className="w-full">
      <CardHeader>
        <CardTitle>Login</CardTitle>
        <CardDescription>Enter your email and password to sign in</CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="email">Email</Label>
            <Input
              id="email"
              type="email"
              placeholder="name@example.com"
              {...form.register("email")}
              disabled={isLoggingIn}
              autoFocus
            />
            {form.formState.errors.email && (
              <p className="text-sm font-medium text-destructive">{form.formState.errors.email.message}</p>
            )}
          </div>
          
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <Label htmlFor="password">Password</Label>
              <button
                type="button"
                onClick={() => setShowForgotPassword(true)}
                className="text-xs font-medium text-primary hover:underline"
              >
                Forgot password?
              </button>
            </div>
            <Input
              id="password"
              type="password"
              {...form.register("password")}
              disabled={isLoggingIn}
            />
            {form.formState.errors.password && (
              <p className="text-sm font-medium text-destructive">{form.formState.errors.password.message}</p>
            )}
          </div>

          <div className="space-y-2">
            <Label htmlFor="tenant_id">Workspace ID (Tenant ID)</Label>
            <Input
              id="tenant_id"
              placeholder="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
              {...form.register("tenant_id")}
              disabled={isLoggingIn}
            />
            <p className="text-xs text-muted-foreground">Paste the UUID you received when your workspace was created</p>
            {form.formState.errors.tenant_id && (
              <p className="text-sm font-medium text-destructive">{form.formState.errors.tenant_id.message}</p>
            )}
          </div>

          <Button type="submit" className="w-full" disabled={isLoggingIn}>
            {isLoggingIn ? "Signing in..." : "Sign in"}
          </Button>
        </form>
      </CardContent>
      <CardFooter className="flex justify-center text-sm text-muted-foreground">
        Don&apos;t have a workspace?{" "}
        <Link to="/register" className="ml-1 font-medium text-primary hover:underline">
          Create one
        </Link>
      </CardFooter>

      <ForgotPasswordModal
        isOpen={showForgotPassword}
        onClose={() => setShowForgotPassword(false)}
        tenantId={form.watch("tenant_id") || ""}
      />
    </Card>
  )
}
