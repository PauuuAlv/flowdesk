import { Routes } from '@angular/router';

export const routes: Routes = [
  {
    path: '',
    loadComponent: () =>
      import('./features/welcome/welcome-page').then((component) => component.WelcomePage)
  },
  {
    path: 'registro',
    loadComponent: () =>
      import('./features/auth/register/register-page').then((component) => component.RegisterPage)
  },
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
  { path: '**', redirectTo: '' }
];
