import { apiClient } from "./api-client"
import { AuthResponse, MeResponse } from "@/types/auth.types"

// The login endpoint expects a JSON body based on what we built in Phase 0
// Specifically: class LoginUserCommand(Command): email, password 
// Wait - FastAPI OAuth2PasswordRequestForm expects form-data `username` and `password`.
// Let's check how we wrote backend/app/interfaces/api/v1/routes/auth.py
// In Phase 0, we created a custom LoginRequest schema: json mapping {"email", "password", "tenant_id"}

interface LoginRequest {
  email: string
  password: string
  tenant_id?: string
}

interface RegisterTenantRequest {
  name: string
  slug: string
  plan: string
  admin_email: string
  admin_password: string
  admin_first_name: string
  admin_last_name: string
}

interface RegisterResponse {
  tenant_id: string
  admin_user_id: string
  access_token?: string | null
}

export const authService = {
  async login(data: LoginRequest): Promise<AuthResponse> {
    const response = await apiClient.post<AuthResponse>("/auth/login", data)
    return response.data
  },

  async registerTenant(data: RegisterTenantRequest): Promise<RegisterResponse> {
    const response = await apiClient.post<RegisterResponse>("/auth/register-tenant", data)
    return response.data
  },

  async getMe(): Promise<MeResponse> {
    const response = await apiClient.get<MeResponse>("/auth/me")
    return response.data
  },
}
