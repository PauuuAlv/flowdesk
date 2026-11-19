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
}

export interface UpdateTenantRequest {
  name: string;
  slug: string;
}
