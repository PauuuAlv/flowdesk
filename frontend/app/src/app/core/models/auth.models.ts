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
  tenant_logo_url?: string | null;
  /** Moneda predeterminada de la empresa (Configuración). */
  tenant_currency?: string;
  email: string;
  full_name: string | null;
  role: string;
  role_id?: string | null;
  role_name?: string | null;
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
/** 'superadmin' | 'operator' | 'viewer' para roles por defecto, 'custom' si no. */
export type PlatformRoleKey = 'superadmin' | 'operator' | 'viewer' | 'custom';
export interface PlatformAdminMe {
  id: string;
  email: string;
  full_name: string | null;
  role: PlatformRoleKey;
  role_id: string;
  role_name: string;
  permissions: string[];
  is_owner: boolean;
}
export interface PlatformMember {
  id: string;
  email: string;
  full_name: string | null;
  role: PlatformRoleKey;
  role_id: string;
  role_name: string;
  is_active: boolean;
  /** Cuenta principal (SUPERADMIN_EMAIL del .env): no se le cambia el rol ni se desactiva. */
  is_owner: boolean;
  invitation_pending: boolean;
  created_at: string;
  invitation_link?: string | null;
}
export interface InvitePlatformMemberRequest {
  email: string;
  full_name: string;
  role_id: string;
}

export interface CreateTenantRequest {
  name: string;
  slug: string;
  admin_email: string;
  admin_full_name: string;
  plan_key: SaaSPlanKey;
}

export type SaaSPlanKey = 'basic' | 'professional' | 'enterprise';
export type SubscriptionStatus = 'trial' | 'active' | 'suspended' | 'cancelled';
export interface TenantUsage {
  users: number;
  active_users: number;
  invited_users: number;
  clients: number;
  opportunities: number;
  activities: number;
  quotes: number;
  products: number;
}
export interface TenantSaaS {
  id: string;
  name: string;
  slug: string;
  plan_key: SaaSPlanKey;
  plan_name: string;
  subscription_status: SubscriptionStatus;
  is_active: boolean;
  max_users: number;
  max_clients: number;
  max_products: number;
  usage: TenantUsage;
  admin_name: string | null;
  admin_email: string | null;
  billing_email: string | null;
  subscription_started_at: string;
  subscription_renews_at: string | null;
  created_at: string;
}
export interface UpdateTenantSubscriptionRequest {
  plan_key: SaaSPlanKey;
  subscription_status: SubscriptionStatus;
  subscription_renews_at: string | null;
  billing_email?: string | null;
}

export interface SaaSPlan {
  key: SaaSPlanKey;
  name: string;
  max_users: number;
  max_clients: number;
  max_products: number;
  tenant_count: number;
  features: string[];
}

export interface CreateTenantResponse {
  tenant_id: string;
  tenant_name: string;
  tenant_slug: string;
  admin_user_id: string;
  admin_email: string;
  invitation_link: string;
}

export type TenantUserRole = 'admin' | 'member' | 'viewer' | 'custom';

export interface InviteUserRequest {
  email: string;
  full_name: string;
  role_id: string;
}

export interface InviteUserResponse {
  user_id: string;
  email: string;
  role: TenantUserRole;
  role_id?: string | null;
  role_name?: string | null;
  invitation_link: string;
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
