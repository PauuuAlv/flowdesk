import { SaaSPlanKey, SubscriptionStatus } from './auth.models';

export interface TenantPlanOption {
  key: SaaSPlanKey;
  name: string;
  max_users: number;
  max_clients: number;
  max_products: number;
  features: string[];
}
export interface PlanChangeRequest {
  id: string;
  tenant_id: string;
  tenant_name: string;
  requested_by_name: string;
  requested_by_email: string;
  current_plan_key: SaaSPlanKey;
  requested_plan_key: SaaSPlanKey;
  status: 'pending' | 'approved' | 'rejected';
  note: string | null;
  created_at: string;
}
export interface TenantPlan {
  plan_key: SaaSPlanKey;
  plan_name: string;
  subscription_status: SubscriptionStatus;
  subscription_started_at: string;
  subscription_renews_at: string | null;
  billing_email: string | null;
  max_users: number;
  max_clients: number;
  max_products: number;
  usage: { users: number; clients: number; products: number };
  plans: TenantPlanOption[];
  current_request: PlanChangeRequest | null;
}
