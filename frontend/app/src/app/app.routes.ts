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
  viewQuotesGuard,createQuotesGuard,updateQuotesGuard,
  viewProductsGuard,createProductsGuard,updateProductsGuard,
  viewRolesGuard, viewCompanySettingsGuard,
  viewUsersGuard
} from './core/guards/auth.guard';

export const routes: Routes = [
  {
    path: '',
    redirectTo: 'iniciar-sesion',
    pathMatch: 'full'
  },
  {
    path: 'accept-invite',
    loadComponent: () =>
      import('./features/auth/register/register-page').then((component) => component.RegisterPage)
  },
  { path: 'registro', redirectTo: 'iniciar-sesion', pathMatch: 'full' },
  {
    path: 'iniciar-sesion',
    loadComponent: () =>
      import('./features/auth/login/login-page').then((component) => component.LoginPage)
  },
  {
    path: 'olvide-mi-contrasena',
    loadComponent: () =>
      import('./features/auth/forgot-password/forgot-password-page').then(
        (component) => component.ForgotPasswordPage
      )
  },
  {
    path: 'restablecer-contrasena',
    loadComponent: () =>
      import('./features/auth/reset-password/reset-password-page').then(
        (component) => component.ResetPasswordPage
      )
  },
  {
    path: 'reset-password',
    loadComponent: () =>
      import('./features/auth/reset-password/reset-password-page').then(
        (component) => component.ResetPasswordPage
      )
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
          import('./features/dashboard/dashboard-page').then((component) => component.DashboardPage)
      },
      {
        path: 'usuarios',
        canActivate: [viewUsersGuard],
        loadComponent: () =>
          import('./features/users/user-list-page').then((component) => component.UserListPage)
      },
      {
        path: 'usuarios/invitar',
        canActivate: [inviteUsersGuard],
        loadComponent: () =>
          import('./features/users/invite-user-page').then((component) => component.InviteUserPage)
      },
      {
        path: 'clientes',
        canActivate: [viewClientsGuard],
        loadComponent: () =>
          import('./features/clients/client-list-page').then((component) => component.ClientListPage)
      },
      {
        path: 'clientes/nuevo',
        canActivate: [createClientsGuard],
        loadComponent: () =>
          import('./features/clients/client-form-page').then((component) => component.ClientFormPage)
      },
      {
        path: 'clientes/:clientId/editar',
        canActivate: [updateClientsGuard],
        loadComponent: () =>
          import('./features/clients/client-form-page').then((component) => component.ClientFormPage)
      },
      {
        path: 'oportunidades', canActivate: [viewOpportunitiesGuard], loadComponent: () => import('./features/opportunities/opportunity-board-page').then(c => c.OpportunityBoardPage)
      },
      {
        path: 'oportunidades/nueva', canActivate: [createOpportunitiesGuard], loadComponent: () => import('./features/opportunities/opportunity-form-page').then(c => c.OpportunityFormPage)
      },
      {
        path: 'oportunidades/:opportunityId/editar', canActivate: [updateOpportunitiesGuard], loadComponent: () => import('./features/opportunities/opportunity-form-page').then(c => c.OpportunityFormPage)
      },
      {path:'actividades',canActivate:[viewActivitiesGuard],loadComponent:()=>import('./features/activities/activity-list-page').then(c=>c.ActivityListPage)},
      {path:'actividades/nueva',canActivate:[createActivitiesGuard],loadComponent:()=>import('./features/activities/activity-form-page').then(c=>c.ActivityFormPage)},
      {path:'actividades/:activityId/editar',canActivate:[updateActivitiesGuard],loadComponent:()=>import('./features/activities/activity-form-page').then(c=>c.ActivityFormPage)},
      {path:'cotizaciones',canActivate:[viewQuotesGuard],loadComponent:()=>import('./features/quotes/quote-list-page').then(c=>c.QuoteListPage)},
      {path:'cotizaciones/nueva',canActivate:[createQuotesGuard],loadComponent:()=>import('./features/quotes/quote-form-page').then(c=>c.QuoteFormPage)},
      {path:'cotizaciones/:quoteId/editar',canActivate:[updateQuotesGuard],loadComponent:()=>import('./features/quotes/quote-form-page').then(c=>c.QuoteFormPage)},
      {path:'cotizaciones/:quoteId',canActivate:[viewQuotesGuard],loadComponent:()=>import('./features/quotes/quote-detail-page').then(c=>c.QuoteDetailPage)},
      {path:'productos',canActivate:[viewProductsGuard],loadComponent:()=>import('./features/products/product-list-page').then(c=>c.ProductListPage)},
      {path:'productos/nuevo',canActivate:[createProductsGuard],loadComponent:()=>import('./features/products/product-form-page').then(c=>c.ProductFormPage)},
      {path:'productos/:productId/editar',canActivate:[updateProductsGuard],loadComponent:()=>import('./features/products/product-form-page').then(c=>c.ProductFormPage)},
      {path:'configuracion/empresa',canActivate:[viewCompanySettingsGuard],loadComponent:()=>import('./features/company-settings/company-settings-page').then(c=>c.CompanySettingsPage)},
      {
        path: 'roles',
        canActivate: [viewRolesGuard],
        loadComponent: () =>
          import('./features/roles/role-list-page').then((component) => component.RoleListPage)
      },
      {
        path: 'roles/nuevo',
        canActivate: [viewRolesGuard],
        loadComponent: () =>
          import('./features/roles/role-form-page').then((component) => component.RoleFormPage)
      },
      {
        path: 'roles/:roleId/editar',
        canActivate: [viewRolesGuard],
        loadComponent: () =>
          import('./features/roles/role-form-page').then((component) => component.RoleFormPage)
      },
      {
        path: 'perfil',
        loadComponent: () =>
          import('./features/profile/profile-page').then((component) => component.ProfilePage)
      },
      {
        path: 'sin-permiso',
        loadComponent: () =>
          import('./features/access-denied/access-denied-page').then(
            (component) => component.AccessDeniedPage
          )
      }
    ]
  },
  {
    path: 'administracion-flowdesk/iniciar-sesion',
    loadComponent: () =>
      import('./features/platform-admin/login/platform-admin-login-page').then(
        (component) => component.PlatformAdminLoginPage
      )
  },
  {
    path: 'administracion-flowdesk',
    canActivate: [platformAdminGuard],
    loadComponent: () =>
      import('./features/platform-admin/dashboard/platform-admin-page').then(
        (component) => component.PlatformAdminPage
      )
  },
  { path: '**', redirectTo: '' }
];
