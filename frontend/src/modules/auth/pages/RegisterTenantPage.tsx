import { useState, useEffect } from "react"
import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import { Link } from "react-router-dom"
import { type RegisterTenantFormValues, registerTenantSchema } from "@/lib/validations"
import { useAuth } from "@/hooks/useAuth"

import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card"
import { Separator } from "@/components/ui/separator"

function generateSlug(name: string): string {
  return name
    .normalize("NFKD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+/, "")
    .slice(0, 100)
    .replace(/-+$/, "")
}

export default function RegisterTenantPage() {
  const { register, isRegistering } = useAuth()
  const [step, setStep] = useState<1 | 2>(1)
  const [slugManuallyEdited, setSlugManuallyEdited] = useState(false)

  const form = useForm<RegisterTenantFormValues>({
    resolver: zodResolver(registerTenantSchema),
    defaultValues: {
      name: "",
      slug: "",
      plan: "starter",
      admin_first_name: "",
      admin_last_name: "",
      admin_email: "",
      admin_password: "",
    },
    mode: "onBlur",
  })

  const companyName = form.watch("name")

  useEffect(() => {
    if (!slugManuallyEdited) {
      const autoSlug = generateSlug(companyName)
      form.setValue("slug", autoSlug, { shouldValidate: Boolean(companyName) || form.getFieldState("slug").invalid })
    }
  }, [companyName, slugManuallyEdited, form])

  const validateStep1 = async () => {
    const isValid = await form.trigger(["name", "slug"])
    if (isValid) setStep(2)
  }

  const onSubmit = (data: RegisterTenantFormValues) => {
    register(data)
  }

  return (
    <Card className="w-full">
      <CardHeader>
        <CardTitle>Create a Workspace</CardTitle>
        <CardDescription>
          {step === 1 ? "Step 1: Company Information" : "Step 2: Admin Account"}
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
          <div className={step === 1 ? "space-y-4" : "hidden"}>
            <div className="space-y-2">
              <Label htmlFor="name">Company/Tenant Name</Label>
              <Input
                id="name"
                placeholder="Acme Corp"
                {...form.register("name")}
                autoFocus
              />
              {form.formState.errors.name && (
                <p className="text-sm font-medium text-destructive">{form.formState.errors.name.message}</p>
              )}
            </div>
            
            <div className="space-y-2">
              <Label htmlFor="slug">Workspace URL (Slug)</Label>
              <Input
                id="slug"
                maxLength={100}
                placeholder="acme-corp"
                {...form.register("slug", {
                  onChange: () => setSlugManuallyEdited(true)
                })}
              />
              <p className="text-xs text-muted-foreground">
                Filled from the company name when possible. You can enter a different slug.
              </p>
              {form.formState.errors.slug && (
                <p className="text-sm font-medium text-destructive">{form.formState.errors.slug.message}</p>
              )}
            </div>

            <Button type="button" className="w-full" onClick={validateStep1}>
              Continue
            </Button>
          </div>

          <div className={step === 2 ? "space-y-4" : "hidden"}>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="admin_first_name">First Name</Label>
                <Input id="admin_first_name" {...form.register("admin_first_name")} />
                {form.formState.errors.admin_first_name && (
                  <p className="text-sm font-medium text-destructive">{form.formState.errors.admin_first_name.message}</p>
                )}
              </div>
              <div className="space-y-2">
                <Label htmlFor="admin_last_name">Last Name</Label>
                <Input id="admin_last_name" {...form.register("admin_last_name")} />
                {form.formState.errors.admin_last_name && (
                  <p className="text-sm font-medium text-destructive">{form.formState.errors.admin_last_name.message}</p>
                )}
              </div>
            </div>

            <div className="space-y-2">
              <Label htmlFor="admin_email">Admin Email</Label>
              <Input id="admin_email" type="email" {...form.register("admin_email")} />
              {form.formState.errors.admin_email && (
                <p className="text-sm font-medium text-destructive">{form.formState.errors.admin_email.message}</p>
              )}
            </div>

            <div className="space-y-2">
              <Label htmlFor="admin_password">Admin Password</Label>
              <Input id="admin_password" type="password" {...form.register("admin_password")} />
              {form.formState.errors.admin_password && (
                <p className="text-sm font-medium text-destructive">{form.formState.errors.admin_password.message}</p>
              )}
            </div>

            <div className="flex gap-2">
              <Button type="button" variant="outline" onClick={() => setStep(1)} disabled={isRegistering} className="w-full">
                Back
              </Button>
              <Button type="submit" className="w-full" disabled={isRegistering}>
                {isRegistering ? "Creating..." : "Create Workspace"}
              </Button>
            </div>
          </div>
        </form>
      </CardContent>
      <Separator />
      <CardFooter className="mt-4 flex justify-center text-sm text-muted-foreground">
        Already have an account?{" "}
        <Link to="/login" className="ml-1 font-medium text-primary hover:underline">
          Sign in
        </Link>
      </CardFooter>
    </Card>
  )
}
