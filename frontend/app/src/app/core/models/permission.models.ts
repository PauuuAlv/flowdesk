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
  opportunitiesView: 'opportunities.view', opportunitiesCreate: 'opportunities.create', opportunitiesUpdate: 'opportunities.update', opportunitiesClose: 'opportunities.close', opportunitiesArchive: 'opportunities.archive',
  activitiesView:'activities.view',activitiesCreate:'activities.create',activitiesUpdate:'activities.update',activitiesComplete:'activities.complete',quotesView:'quotes.view',quotesCreate:'quotes.create',quotesUpdate:'quotes.update',quotesStatus:'quotes.status',productsView:'products.view',productsCreate:'products.create',productsUpdate:'products.update',productsDelete:'products.delete'
} as const;

export type PermissionCode = (typeof PERMISSIONS)[keyof typeof PERMISSIONS];

export const PERMISSION_MODULES = [
  {key:'products',label:'Productos y servicios',description:'Catálogo comercial utilizado en cotizaciones.',permissions:[{code:PERMISSIONS.productsView,label:'Ver'},{code:PERMISSIONS.productsCreate,label:'Crear'},{code:PERMISSIONS.productsUpdate,label:'Editar'},{code:PERMISSIONS.productsDelete,label:'Desactivar'}]},
  {key:'quotes',label:'Cotizaciones',description:'Propuestas económicas y seguimiento de aceptación.',permissions:[{code:PERMISSIONS.quotesView,label:'Ver'},{code:PERMISSIONS.quotesCreate,label:'Crear'},{code:PERMISSIONS.quotesUpdate,label:'Editar'},{code:PERMISSIONS.quotesStatus,label:'Cambiar estado'}]},
  {key:'activities',label:'Actividades',description:'Llamadas, correos, reuniones y tareas de seguimiento.',permissions:[{code:PERMISSIONS.activitiesView,label:'Ver'},{code:PERMISSIONS.activitiesCreate,label:'Crear'},{code:PERMISSIONS.activitiesUpdate,label:'Editar'},{code:PERMISSIONS.activitiesComplete,label:'Completar'}]},
  {
    key: 'opportunities', label: 'Oportunidades', description: 'Pipeline y seguimiento de negociaciones.', permissions: [
      { code: PERMISSIONS.opportunitiesView, label: 'Ver' }, { code: PERMISSIONS.opportunitiesCreate, label: 'Crear' },
      { code: PERMISSIONS.opportunitiesUpdate, label: 'Editar' }, { code: PERMISSIONS.opportunitiesClose, label: 'Cerrar' }, { code: PERMISSIONS.opportunitiesArchive, label: 'Archivar' }
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
