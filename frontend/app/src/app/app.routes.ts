import { Routes } from '@angular/router';

import {
  authGuard,
  createClientsGuard,
  createOpportunitiesGuard,
  inviteUsersGuard,
  platformAdminGuard,
  updateClientsGuard,
  updateOpportunitiesGuard,
  viewClientsGuard,
  viewOpportunitiesGuard,
  viewActivitiesGuard,
  createActivitiesGuard,
  updateActivitiesGuard,
  viewQuotesGuard,
  createQuotesGuard,
  updateQuotesGuard,
  viewProductsGuard,
  createProductsGuard,
  updateProductsGuard,
  viewRolesGuard,
  viewCompanySettingsGuard,
  viewUsersGuard,
} from './core/guards/auth.guard';

export const routes: Routes = [
  {
    path: '',
    redirectTo: 'iniciar-sesion',
    pathMatch: 'full',
  },
  {
    path: 'accept-invite',
    loadComponent: () =>
      import('./features/auth/register/register-page').then((component) => component.RegisterPage),
  },
  { path: 'registro', redirectTo: 'iniciar-sesion', pathMatch: 'full' },
  {
    path: 'iniciar-sesion',
    loadComponent: () =>
      import('./features/auth/login/login-page').then((component) => component.LoginPage),
  },
  {
    path: 'olvide-mi-contrasena',
    loadComponent: () =>
      import('./features/auth/forgot-password/forgot-password-page').then(
        (component) => component.ForgotPasswordPage,
      ),
  },
  {
    path: 'restablecer-contrasena',
    loadComponent: () =>
      import('./features/auth/reset-password/reset-password-page').then(
        (component) => component.ResetPasswordPage,
      ),
  },
  {
    path: 'reset-password',
    loadComponent: () =>
      import('./features/auth/reset-password/reset-password-page').then(
        (component) => component.ResetPasswordPage,
      ),
  },
  {
    path: 'panel',
    canActivate: [authGuard],
    loadComponent: () =>
      import('./layout/tenant-shell/tenant-shell').then((component) => component.TenantShell),
    children: [
      {
        path: '',
        pathMatch: 'full',
        loadComponent: () =>
          import('./features/dashboard/dashboard-page').then(
            (component) => component.DashboardPage,
          ),
      },
      {
        path: 'usuarios',
        canActivate: [viewUsersGuard],
        loadComponent: () =>
          import('./features/users/user-list-page').then((component) => component.UserListPage),
      },
      {
        path: 'usuarios/invitar',
        canActivate: [inviteUsersGuard],
        loadComponent: () =>
          import('./features/users/invite-user-page').then((component) => component.InviteUserPage),
      },
      {
        path: 'clientes',
        canActivate: [viewClientsGuard],
        loadComponent: () =>
          import('./features/clients/client-list-page').then(
            (component) => component.ClientListPage,
          ),
      },
      {
        path: 'clientes/nuevo',
        canActivate: [createClientsGuard],
        loadComponent: () =>
          import('./features/clients/client-form-page').then(
            (component) => component.ClientFormPage,
          ),
      },
      {
        path: 'clientes/:clientId/editar',
        canActivate: [updateClientsGuard],
        loadComponent: () =>
          import('./features/clients/client-form-page').then(
            (component) => component.ClientFormPage,
          ),
      },
      {
        path: 'oportunidades',
        canActivate: [viewOpportunitiesGuard],
        loadComponent: () =>
          import('./features/opportunities/opportunity-board-page').then(
            (c) => c.OpportunityBoardPage,
          ),
      },
      {
        path: 'oportunidades/nueva',
        canActivate: [createOpportunitiesGuard],
        loadComponent: () =>
          import('./features/opportunities/opportunity-form-page').then(
            (c) => c.OpportunityFormPage,
          ),
      },
      {
        path: 'oportunidades/:opportunityId/editar',
        canActivate: [updateOpportunitiesGuard],
        loadComponent: () =>
          import('./features/opportunities/opportunity-form-page').then(
            (c) => c.OpportunityFormPage,
          ),
      },
      {
        path: 'configuracion/etapas-oportunidad',
        canActivate: [updateOpportunitiesGuard],
        loadComponent: () =>
          import('./features/opportunity-stages/opportunity-stage-catalog-page').then(
            (c) => c.OpportunityStageCatalogPage,
          ),
      },
      {
        path: 'actividades',
        canActivate: [viewActivitiesGuard],
        loadComponent: () =>
          import('./features/activities/activity-list-page').then((c) => c.ActivityListPage),
      },
      {
        path: 'actividades/nueva',
        canActivate: [createActivitiesGuard],
        loadComponent: () =>
          import('./features/activities/activity-form-page').then((c) => c.ActivityFormPage),
      },
      {
        path: 'actividades/:activityId/editar',
        canActivate: [updateActivitiesGuard],
        loadComponent: () =>
          import('./features/activities/activity-form-page').then((c) => c.ActivityFormPage),
      },
      {
        path: 'cotizaciones',
        canActivate: [viewQuotesGuard],
        loadComponent: () =>
          import('./features/quotes/quote-list-page').then((c) => c.QuoteListPage),
      },
      {
        path: 'cotizaciones/nueva',
        canActivate: [createQuotesGuard],
        loadComponent: () =>
          import('./features/quotes/quote-form-page').then((c) => c.QuoteFormPage),
      },
      {
        path: 'cotizaciones/:quoteId/editar',
        canActivate: [updateQuotesGuard],
        loadComponent: () =>
          import('./features/quotes/quote-form-page').then((c) => c.QuoteFormPage),
      },
      {
        path: 'cotizaciones/:quoteId',
        canActivate: [viewQuotesGuard],
        loadComponent: () =>
          import('./features/quotes/quote-detail-page').then((c) => c.QuoteDetailPage),
      },
      {
        path: 'productos',
        canActivate: [viewProductsGuard],
        data: { itemType: 'product' },
        loadComponent: () =>
          import('./features/products/product-list-page').then((c) => c.ProductListPage),
      },
      {
        path: 'productos/nuevo',
        canActivate: [createProductsGuard],
        data: { itemType: 'product' },
        loadComponent: () =>
          import('./features/products/product-form-page').then((c) => c.ProductFormPage),
      },
      {
        path: 'productos/:productId/editar',
        canActivate: [updateProductsGuard],
        data: { itemType: 'product' },
        loadComponent: () =>
          import('./features/products/product-form-page').then((c) => c.ProductFormPage),
      },
      {
        path: 'servicios',
        canActivate: [viewProductsGuard],
        data: { itemType: 'service' },
        loadComponent: () =>
          import('./features/products/product-list-page').then((c) => c.ProductListPage),
      },
      {
        path: 'servicios/nuevo',
        canActivate: [createProductsGuard],
        data: { itemType: 'service' },
        loadComponent: () =>
          import('./features/products/product-form-page').then((c) => c.ProductFormPage),
      },
      {
        path: 'servicios/:productId/editar',
        canActivate: [updateProductsGuard],
        data: { itemType: 'service' },
        loadComponent: () =>
          import('./features/products/product-form-page').then((c) => c.ProductFormPage),
      },
      {
        path: 'configuracion/unidades',
        canActivate: [updateProductsGuard],
        data: { catalog: 'units' },
        loadComponent: () => import('./features/product-catalogs/product-catalog-settings-page').then((c) => c.ProductCatalogSettingsPage),
      },
      {
        path: 'configuracion/marcas',
        canActivate: [updateProductsGuard],
        data: { catalog: 'brands' },
        loadComponent: () => import('./features/product-catalogs/product-catalog-settings-page').then((c) => c.ProductCatalogSettingsPage),
      },
      {
        path: 'configuracion/categorias',
        canActivate: [updateProductsGuard],
        data: { catalog: 'categories' },
        loadComponent: () => import('./features/product-catalogs/product-catalog-settings-page').then((c) => c.ProductCatalogSettingsPage),
      },
      {
        path: 'configuracion/empresa',
        canActivate: [viewCompanySettingsGuard],
        loadComponent: () =>
          import('./features/company-settings/company-settings-page').then(
            (c) => c.CompanySettingsPage,
          ),
      },
      {
        path: 'configuracion/plan',
        canActivate: [viewCompanySettingsGuard],
        loadComponent: () =>
          import('./features/tenant-plan/tenant-plan-page').then(
            (c) => c.TenantPlanPage,
          ),
      },
      {
        path: 'roles',
        canActivate: [viewRolesGuard],
        loadComponent: () =>
          import('./features/roles/role-list-page').then((component) => component.RoleListPage),
      },
      {
        path: 'roles/nuevo',
        canActivate: [viewRolesGuard],
        loadComponent: () =>
          import('./features/roles/role-form-page').then((component) => component.RoleFormPage),
      },
      {
        path: 'roles/:roleId/editar',
        canActivate: [viewRolesGuard],
        loadComponent: () =>
          import('./features/roles/role-form-page').then((component) => component.RoleFormPage),
      },
      {
        path: 'perfil',
        loadComponent: () =>
          import('./features/profile/profile-page').then((component) => component.ProfilePage),
      },
      {
        path: 'sin-permiso',
        loadComponent: () =>
          import('./features/access-denied/access-denied-page').then(
            (component) => component.AccessDeniedPage,
          ),
      },
    ],
  },
  {
    path: 'administracion-flowdesk/iniciar-sesion',
    loadComponent: () =>
      import('./features/platform-admin/login/platform-admin-login-page').then(
        (component) => component.PlatformAdminLoginPage,
      ),
  },
  {
    // Mismas páginas de recuperación que las empresas, apuntando a las cuentas de plataforma.
    path: 'administracion-flowdesk/olvide-mi-contrasena',
    data: { audience: 'platform' },
    loadComponent: () =>
      import('./features/auth/forgot-password/forgot-password-page').then(
        (component) => component.ForgotPasswordPage,
      ),
  },
  {
    path: 'administracion-flowdesk/restablecer-contrasena',
    data: { audience: 'platform' },
    loadComponent: () =>
      import('./features/auth/reset-password/reset-password-page').then(
        (component) => component.ResetPasswordPage,
      ),
  },
  {
    path: 'administracion-flowdesk/aceptar-invitacion',
    loadComponent: () =>
      import('./features/platform-admin/accept-invite/platform-accept-invite-page').then(
        (component) => component.PlatformAcceptInvitePage,
      ),
  },
  {
    path: 'administracion-flowdesk',
    canActivate: [platformAdminGuard],
    loadComponent: () =>
      import('./features/platform-admin/shell/platform-admin-shell').then(
        (component) => component.PlatformAdminShell,
      ),
    children: [
      {
        path: '',
        pathMatch: 'full',
        loadComponent: () =>
          import('./features/platform-admin/overview/platform-overview-page').then(
            (component) => component.PlatformOverviewPage,
          ),
      },
      {
        path: 'empresas',
        loadComponent: () =>
          import('./features/platform-admin/dashboard/platform-admin-page').then(
            (component) => component.PlatformAdminPage,
          ),
      },
      {
        path: 'empresas/:tenantId',
        loadComponent: () =>
          import('./features/platform-admin/tenant-detail/platform-tenant-detail-page').then(
            (component) => component.PlatformTenantDetailPage,
          ),
      },
      {
        path: 'planes',
        loadComponent: () =>
          import('./features/platform-admin/plans/platform-plans-page').then(
            (component) => component.PlatformPlansPage,
          ),
      },
      {
        path: 'suscripciones',
        loadComponent: () =>
          import('./features/platform-admin/subscriptions/platform-subscriptions-page').then(
            (component) => component.PlatformSubscriptionsPage,
          ),
      },
      {
        path: 'auditoria',
        loadComponent: () =>
          import('./features/platform-admin/audit/platform-audit-page').then(
            (component) => component.PlatformAuditPage,
          ),
      },
      {
        path: 'equipo',
        loadComponent: () =>
          import('./features/platform-admin/team/platform-team-page').then(
            (component) => component.PlatformTeamPage,
          ),
      },
      {
        path: 'perfil',
        loadComponent: () =>
          import('./features/platform-admin/profile/platform-profile-page').then(
            (component) => component.PlatformProfilePage,
          ),
      },
    ],
  },
  { path: '**', redirectTo: '' },
];
