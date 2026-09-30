import { PermissionCode } from './permission.models';

export type RoleOrigin = 'template' | 'custom';
export type MemberStatus = 'active' | 'pending' | 'inactive';

export interface TenantRole {
  id: string;
  name: string;
  description: string;
  origin: RoleOrigin;
  is_protected: boolean;
  user_count: number;
  permissions: PermissionCode[];
}

export interface SaveRoleRequest {
  name: string;
  description: string;
  permissions: PermissionCode[];
}

export interface PermissionModule {
  key: string;
  label: string;
  description: string;
  permissions: Array<{ code: PermissionCode; label: string }>;
}

export interface TenantMember {
  id: string;
  full_name: string;
  email: string;
  role_id: string;
  role_name: string;
  status: MemberStatus;
}
