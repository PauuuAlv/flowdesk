export interface RegisterRequest {
  name: string;
  company_name: string;
  email: string;
  password: string;
}

export interface AuthUser {
  id: number;
  name: string;
  email: string;
  is_active: boolean;
  roles: string[];
}

export interface TenantSummary {
  id: number;
  name: string;
}

export interface RegisterResponse {
  message: string;
  user: AuthUser;
  tenant: TenantSummary;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface AuthenticatedUser {
  id: number;
  name: string;
  email: string;
  tenant_id: number;
  roles: string[];
  permissions: string[];
}

export interface LoginResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
  user: AuthenticatedUser;
}

export interface ForgotPasswordRequest {
  email: string;
}

export interface ForgotPasswordResponse {
  message: string;
}

export interface ResetPasswordRequest {
  token: string;
  new_password: string;
}

export interface ResetPasswordResponse {
  message: string;
}
