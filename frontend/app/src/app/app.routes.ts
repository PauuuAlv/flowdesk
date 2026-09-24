import { Routes } from '@angular/router';

import { authGuard, inviteUsersGuard, platformAdminGuard } from './core/guards/auth.guard';

export const routes: Routes = [
  {
    path: '',
    loadComponent: () =>
      import('./features/welcome/welcome-page').then((component) => component.WelcomePage)
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
        path: 'usuarios/invitar',
        canActivate: [inviteUsersGuard],
        loadComponent: () =>
          import('./features/users/invite-user-page').then((component) => component.InviteUserPage)
      },
      {
        path: 'perfil',
        loadComponent: () =>
          import('./features/profile/profile-page').then((component) => component.ProfilePage)
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
