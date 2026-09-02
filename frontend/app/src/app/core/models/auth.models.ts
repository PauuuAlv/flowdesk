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
