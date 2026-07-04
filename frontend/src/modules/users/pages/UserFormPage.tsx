import { useNavigate, useParams } from "react-router-dom"
import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import * as z from "zod"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { usersService } from "@/services/users.service"
import { AVAILABLE_ROLES } from "@/lib/roles.config"
import { PageHeader } from "@/components/layout/PageHeader"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { FormSkeleton } from "@/components/shared/LoadingSkeleton"
import { ArrowLeft, Save } from "lucide-react"
import { Checkbox } from "@/components/ui/checkbox"

const userSchema = z.object({
  email: z.string().email("Invalid email address"),
  first_name: z.string().min(2, "First name is required"),
  last_name: z.string().min(2, "Last name is required"),
  role: z.string().min(1, "Role is required"),
  is_active: z.boolean(),
})

type UserFormValues = z.infer<typeof userSchema>

export default function UserFormPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const isEditing = Boolean(id && id !== "new")

  const { data: user, isLoading: isFetching } = useQuery({
    queryKey: ["user", id],
    queryFn: () => usersService.getUser(id!),
    enabled: isEditing,
  })

  const { register, handleSubmit, formState: { errors }, setValue, watch } = useForm<UserFormValues>({
    resolver: zodResolver(userSchema),
    values: user ? {
      email: user.email,
      first_name: user.first_name,
      last_name: user.last_name,
      role: user.role,
      is_active: user.is_active,
    } : {
      email: "",
      first_name: "",
      last_name: "",
      role: "operator",
      is_active: true,
    }
  })

  const saveMutation = useMutation({
    mutationFn: async (data: UserFormValues) => {
      if (isEditing) {
        return usersService.updateUser(id!, data)
      } else {
        return usersService.createUser(data)
      }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["users"] })
      navigate("/users")
    }
  })

  const onSubmit = (data: UserFormValues) => {
    saveMutation.mutate(data)
  }

  if (isEditing && isFetching) {
    return (
      <div className="space-y-6">
        <PageHeader title="Edit User" />
        <FormSkeleton fields={4} />
      </div>
    )
  }

  return (
    <div className="max-w-2xl space-y-6">
      <div className="flex items-center gap-4">
        <Button variant="ghost" size="icon" onClick={() => navigate("/users")} aria-label="Back to users list">
          <ArrowLeft className="h-5 w-5" />
        </Button>
        <PageHeader 
          title={isEditing ? "Edit User" : "Invite User"} 
          description={isEditing ? `Update details for ${user?.email}` : "Add a new team member."}
          action={
            <Button onClick={handleSubmit(onSubmit)} disabled={saveMutation.isPending}>
              <Save className="mr-2 h-4 w-4" />
              {saveMutation.isPending ? "Saving..." : "Save User"}
            </Button>
          }
        />
      </div>

      <div className="grid gap-6 p-6 border rounded-xl bg-card">
        <div className="space-y-2">
          <Label htmlFor="email">Email Address</Label>
          <Input id="email" type="email" placeholder="user@acme.com" {...register("email")} disabled={isEditing} />
          {errors.email && <p className="text-xs text-destructive">{errors.email.message}</p>}
        </div>

        <div className="grid sm:grid-cols-2 gap-4">
          <div className="space-y-2">
            <Label htmlFor="first_name">First Name</Label>
            <Input id="first_name" placeholder="John" {...register("first_name")} />
            {errors.first_name && <p className="text-xs text-destructive">{errors.first_name.message}</p>}
          </div>
          <div className="space-y-2">
            <Label htmlFor="last_name">Last Name</Label>
            <Input id="last_name" placeholder="Doe" {...register("last_name")} />
            {errors.last_name && <p className="text-xs text-destructive">{errors.last_name.message}</p>}
          </div>
        </div>

        <div className="space-y-2">
          <Label htmlFor="role">Role</Label>
          <Select 
            value={watch("role")} 
            onValueChange={(val) => setValue("role", val, { shouldValidate: true })}
          >
            <SelectTrigger>
              <SelectValue placeholder="Select Role" />
            </SelectTrigger>
            <SelectContent>
              {AVAILABLE_ROLES.map((role) => (
                <SelectItem key={role.value} value={role.value}>
                  {role.label} ({role.description})
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          {errors.role && <p className="text-xs text-destructive">{errors.role.message}</p>}
        </div>

        <div className="flex items-center space-x-2 pt-2">
          <Checkbox 
            id="is_active" 
            checked={watch("is_active")} 
            onCheckedChange={(checked) => setValue("is_active", checked === true)} 
          />
          <Label htmlFor="is_active" className="text-sm font-normal cursor-pointer">
            User is active and can log in
          </Label>
        </div>
      </div>
    </div>
  )
}
