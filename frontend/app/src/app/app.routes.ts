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
  { path: '**', redirectTo: '' }
];
