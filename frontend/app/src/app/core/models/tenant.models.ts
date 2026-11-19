import { SaaSPlanKey, SubscriptionStatus, TenantUsage } from './auth.models';

export interface TenantSummary {
  id: string;
  name: string;
  slug: string;
  is_active: boolean;
  created_at: string | null;
  admin_email: string | null;
  admin_full_name: string | null;
  users_count: number;
  active_users_count: number;
  // Plan y suscripción SaaS
  plan_key: SaaSPlanKey;
  plan_name: string;
  subscription_status: SubscriptionStatus;
  max_users: number;
  max_clients: number;
  max_products: number;
  usage: TenantUsage;
  subscription_started_at: string | null;
  subscription_renews_at: string | null;
}

export interface UpdateTenantRequest {
  name: string;
  slug: string;
}

export interface UpdateTenantSubscriptionRequest {
  plan_key: SaaSPlanKey;
  subscription_status: SubscriptionStatus;
  subscription_renews_at: string | null;
}
