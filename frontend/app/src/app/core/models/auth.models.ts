export interface RegisterRequest {
  token: string;
  password: string;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface RefreshRequest {
  refresh_token: string;
}

export interface UserMeResponse {
  id: string;
  tenant_id: string;
  tenant_name?: string;
  email: string;
  full_name: string | null;
  role: string;
  roles?: string[];
  permissions?: PermissionCode[];
  status: string;
}

export interface PlatformAdminLoginRequest {
  email: string;
  password: string;
}

export interface PlatformAdminTokenResponse {
  access_token: string;
  token_type: string;
}

export interface CreateTenantRequest {
  name: string;
  slug: string;
  admin_email: string;
  admin_full_name: string;
}

export interface CreateTenantResponse {
  tenant_id: string;
  tenant_name: string;
  tenant_slug: string;
  admin_user_id: string;
  admin_email: string;
  dev_invitation_link: string;
}

export type TenantUserRole = 'admin' | 'member';

export interface InviteUserRequest {
  email: string;
  full_name: string;
  role: TenantUserRole;
}

export interface InviteUserResponse {
  user_id: string;
  email: string;
  role: TenantUserRole;
  dev_invitation_link: string;
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
import { PermissionCode } from './permission.models';
