import { z } from "zod"

export const loginSchema = z.object({
  email: z.string().email("Please enter a valid email address"),
  password: z.string().min(1, "Password is required"),
  workspace_slug: z.string().trim().toLowerCase()
    .regex(/^(?:[a-z0-9-]{2,100})?$/, "Enter the workspace slug, for example acme-corp")
    .optional(),
})

export type LoginFormValues = z.infer<typeof loginSchema>

export const registerTenantSchema = z.object({
  name: z.string().min(2, "Company name must be at least 2 characters"),
  slug: z.string().min(2, "Workspace URL must be at least 2 characters")
    .max(100, "Workspace URL must have at most 100 characters")
    .regex(/^[a-z0-9-]+$/, "Only lowercase letters, numbers, and dashes allowed"),
  plan: z.string(),
  admin_email: z.string().email("Valid email required"),
  admin_password: z.string()
    .min(8, "Password must be at least 8 characters")
    .regex(/[A-Z]/, "Password requires at least one uppercase letter")
    .regex(/[0-9]/, "Password requires at least one number"),
  admin_first_name: z.string().min(1, "First name is required"),
  admin_last_name: z.string().min(1, "Last name is required"),
})

export type RegisterTenantFormValues = z.infer<typeof registerTenantSchema>
