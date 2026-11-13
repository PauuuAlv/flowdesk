export const PERMISSIONS = {
  dashboardView: 'dashboard.view',
  usersView: 'users.view',
  usersInvite: 'users.invite',
  usersUpdate: 'users.update',
  usersDelete: 'users.delete',
  rolesView: 'roles.view',
  rolesCreate: 'roles.create',
  rolesUpdate: 'roles.update',
  rolesDelete: 'roles.delete',
  clientsView: 'clients.view',
  clientsCreate: 'clients.create',
  clientsUpdate: 'clients.update',
  clientsDelete: 'clients.delete',
  opportunitiesView: 'opportunities.view', opportunitiesCreate: 'opportunities.create', opportunitiesUpdate: 'opportunities.update', opportunitiesClose: 'opportunities.close'
} as const;

export type PermissionCode = (typeof PERMISSIONS)[keyof typeof PERMISSIONS];

export const PERMISSION_MODULES = [
  {
    key: 'opportunities', label: 'Oportunidades', description: 'Pipeline y seguimiento de negociaciones.', permissions: [
      { code: PERMISSIONS.opportunitiesView, label: 'Ver' }, { code: PERMISSIONS.opportunitiesCreate, label: 'Crear' },
      { code: PERMISSIONS.opportunitiesUpdate, label: 'Editar' }, { code: PERMISSIONS.opportunitiesClose, label: 'Cerrar' }
    ]
  },
  {
    key: 'dashboard',
    label: 'Inicio',
    description: 'Resumen general del espacio de trabajo.',
    permissions: [{ code: PERMISSIONS.dashboardView, label: 'Ver' }]
  },
  {
    key: 'users',
    label: 'Usuarios',
    description: 'Integrantes, invitaciones y acceso a la empresa.',
    permissions: [
      { code: PERMISSIONS.usersView, label: 'Ver' },
      { code: PERMISSIONS.usersInvite, label: 'Invitar' },
      { code: PERMISSIONS.usersUpdate, label: 'Editar' },
      { code: PERMISSIONS.usersDelete, label: 'Desactivar' }
    ]
  },
  {
    key: 'roles',
    label: 'Roles y permisos',
    description: 'Creación y administración de los accesos.',
    permissions: [
      { code: PERMISSIONS.rolesView, label: 'Ver' },
      { code: PERMISSIONS.rolesCreate, label: 'Crear' },
      { code: PERMISSIONS.rolesUpdate, label: 'Editar' },
      { code: PERMISSIONS.rolesDelete, label: 'Eliminar' }
    ]
  },
  {
    key: 'clients',
    label: 'Clientes',
    description: 'Información comercial de los clientes.',
    permissions: [
      { code: PERMISSIONS.clientsView, label: 'Ver' },
      { code: PERMISSIONS.clientsCreate, label: 'Crear' },
      { code: PERMISSIONS.clientsUpdate, label: 'Editar' },
      { code: PERMISSIONS.clientsDelete, label: 'Eliminar' }
    ]
  }
] as const;
