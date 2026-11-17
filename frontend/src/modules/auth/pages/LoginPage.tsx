import { useState } from "react"
import { isAxiosError } from "axios"
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
  const [showWorkspace, setShowWorkspace] = useState(false)

  const form = useForm<LoginFormValues>({
    resolver: zodResolver(loginSchema),
    defaultValues: {
      email: "",
      password: "",
      workspace_slug: "",
    },
  })

  const onSubmit = (data: LoginFormValues) => {
    form.clearErrors("root.login")
    login({ ...data, workspace_slug: data.workspace_slug || undefined }, {
      onError: (error) => {
        if (!isAxiosError(error) || error.response?.status !== 401) return
        const workspaceRequired = error.response.data?.detail?.code === "WORKSPACE_REQUIRED"
        if (workspaceRequired) setShowWorkspace(true)
        form.setError("root.login", {
          message: workspaceRequired
            ? "This email is used in multiple workspaces. Enter your workspace slug to sign in."
            : data.workspace_slug
              ? "Couldn’t sign in. Check your email, password, and workspace slug."
              : "Couldn’t sign in. Check your email and password.",
        })
      },
    })
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

          {showWorkspace ? (
            <div className="space-y-2">
              <Label htmlFor="workspace_slug">Workspace slug</Label>
              <Input id="workspace_slug" placeholder="acme-corp" {...form.register("workspace_slug")} disabled={isLoggingIn} />
              {form.formState.errors.workspace_slug && (
                <p className="text-sm text-destructive">{form.formState.errors.workspace_slug.message}</p>
              )}
            </div>
          ) : (
            <button type="button" className="text-sm text-primary hover:underline" onClick={() => setShowWorkspace(true)}>
              Use a workspace slug
            </button>
          )}

          {form.formState.errors.root?.login?.message && (
            <p role="alert" className="text-sm text-destructive">{form.formState.errors.root.login.message}</p>
          )}

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
        workspaceSlug={form.watch("workspace_slug")?.trim().toLowerCase()}
      />
    </Card>
  )
}
