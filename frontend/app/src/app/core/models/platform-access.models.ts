/** Permisos del equipo de administración de plataforma (independientes de los de los tenants). */
export const PLATFORM_PERMISSIONS = {
  overviewView: 'platform.overview.view',
  tenantsView: 'platform.tenants.view',
  tenantsCreate: 'platform.tenants.create',
  tenantsUpdate: 'platform.tenants.update',
  tenantsDelete: 'platform.tenants.delete',
  plansView: 'platform.plans.view',
  subscriptionsView: 'platform.subscriptions.view',
  subscriptionsResolve: 'platform.subscriptions.resolve',
  auditView: 'platform.audit.view',
  auditExport: 'platform.audit.export',
  teamView: 'platform.team.view',
  teamInvite: 'platform.team.invite',
  teamUpdate: 'platform.team.update',
  rolesView: 'platform.roles.view',
  rolesCreate: 'platform.roles.create',
  rolesUpdate: 'platform.roles.update',
  rolesDelete: 'platform.roles.delete',
} as const;

export type PlatformPermissionCode = (typeof PLATFORM_PERMISSIONS)[keyof typeof PLATFORM_PERMISSIONS];

export interface PlatformPermissionModule {
  key: string;
  label: string;
  description: string;
  permissions: ReadonlyArray<{ code: PlatformPermissionCode; label: string }>;
}

const P = PLATFORM_PERMISSIONS;

export const PLATFORM_PERMISSION_MODULES: ReadonlyArray<PlatformPermissionModule> = [
  {
    key: 'overview', label: 'Panel', description: 'Resumen general de la plataforma.',
    permissions: [{ code: P.overviewView, label: 'Ver' }],
  },
  {
    key: 'tenants', label: 'Empresas', description: 'Alta, datos, plan, suscripción y estado de cada empresa.',
    permissions: [
      { code: P.tenantsView, label: 'Ver' },
      { code: P.tenantsCreate, label: 'Crear' },
      { code: P.tenantsUpdate, label: 'Editar' },
      { code: P.tenantsDelete, label: 'Eliminar' },
    ],
  },
  {
    key: 'plans', label: 'Planes', description: 'Catálogo de planes y empresas por plan.',
    permissions: [{ code: P.plansView, label: 'Ver' }],
  },
  {
    key: 'subscriptions', label: 'Suscripciones', description: 'Solicitudes de cambio de plan de las empresas.',
    permissions: [
      { code: P.subscriptionsView, label: 'Ver' },
      { code: P.subscriptionsResolve, label: 'Aprobar o rechazar' },
    ],
  },
  {
    key: 'audit', label: 'Auditoría', description: 'Bitácora de acciones del equipo de plataforma.',
    permissions: [
      { code: P.auditView, label: 'Ver' },
      { code: P.auditExport, label: 'Descargar PDF' },
    ],
  },
  {
    key: 'team', label: 'Equipo de plataforma', description: 'Integrantes con acceso a la administración.',
    permissions: [
      { code: P.teamView, label: 'Ver' },
      { code: P.teamInvite, label: 'Invitar' },
      { code: P.teamUpdate, label: 'Cambiar rol y estado' },
    ],
  },
  {
    key: 'roles', label: 'Roles de plataforma', description: 'Roles y permisos del equipo.',
    permissions: [
      { code: P.rolesView, label: 'Ver' },
      { code: P.rolesCreate, label: 'Crear' },
      { code: P.rolesUpdate, label: 'Editar' },
      { code: P.rolesDelete, label: 'Eliminar' },
    ],
  },
];

export interface PlatformRole {
  id: string;
  name: string;
  description: string;
  origin: 'template' | 'custom';
  template_key: 'superadmin' | 'operator' | 'viewer' | null;
  is_protected: boolean;
  member_count: number;
  permissions: PlatformPermissionCode[];
}

export interface SavePlatformRoleRequest {
  name: string;
  description: string;
  permissions: PlatformPermissionCode[];
}
