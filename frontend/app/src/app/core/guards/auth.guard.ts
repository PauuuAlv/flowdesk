import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';
import { catchError, map, of, tap } from 'rxjs';

import { AuthService } from '../services/auth.service';
import { SessionService } from '../services/session.service';
import { PERMISSIONS } from '../models/permission.models';

export const authGuard: CanActivateFn = (_route, state) => {
  const authService = inject(AuthService);
  const sessionService = inject(SessionService);
  const router = inject(Router);

  if (!sessionService.getAccessToken() && !sessionService.getRefreshToken()) {
    return router.createUrlTree(['/iniciar-sesion'], { queryParams: { returnUrl: state.url } });
  }

  return authService.me().pipe(
    tap((user) => sessionService.saveUser(user)),
    map(() => true),
    catchError(() => {
      sessionService.clear();
      return of(
        router.createUrlTree(['/iniciar-sesion'], {
          queryParams: { returnUrl: state.url, sesion: 'expirada' }
        })
      );
    })
  );
};

export const platformAdminGuard: CanActivateFn = () => {
  const sessionService = inject(SessionService);
  const router = inject(Router);

  return sessionService.getPlatformAdminToken()
    ? true
    : router.createUrlTree(['/administracion-flowdesk/iniciar-sesion']);
};

export const inviteUsersGuard: CanActivateFn = () => {
  const sessionService = inject(SessionService);
  const router = inject(Router);
  const user = sessionService.getUser();

  return user?.role === 'admin' || user?.permissions?.includes(PERMISSIONS.usersInvite)
    ? true
    : router.createUrlTree(['/panel/sin-permiso']);
};

export const viewUsersGuard: CanActivateFn = () => permissionGuard(PERMISSIONS.usersView);
export const viewRolesGuard: CanActivateFn = () => permissionGuard(PERMISSIONS.rolesView);
export const viewClientsGuard: CanActivateFn = () => permissionGuard(PERMISSIONS.clientsView);
export const createClientsGuard: CanActivateFn = () => permissionGuard(PERMISSIONS.clientsCreate);
export const updateClientsGuard: CanActivateFn = () => permissionGuard(PERMISSIONS.clientsUpdate);
export const viewOpportunitiesGuard: CanActivateFn = () => permissionGuard(PERMISSIONS.opportunitiesView);
export const createOpportunitiesGuard: CanActivateFn = () => permissionGuard(PERMISSIONS.opportunitiesCreate);
export const updateOpportunitiesGuard: CanActivateFn = () => permissionGuard(PERMISSIONS.opportunitiesUpdate);
export const viewActivitiesGuard: CanActivateFn = () => permissionGuard(PERMISSIONS.activitiesView);
export const createActivitiesGuard: CanActivateFn = () => permissionGuard(PERMISSIONS.activitiesCreate);
export const updateActivitiesGuard: CanActivateFn = () => permissionGuard(PERMISSIONS.activitiesUpdate);
export const viewQuotesGuard:CanActivateFn=()=>permissionGuard(PERMISSIONS.quotesView);export const createQuotesGuard:CanActivateFn=()=>permissionGuard(PERMISSIONS.quotesCreate);export const updateQuotesGuard:CanActivateFn=()=>permissionGuard(PERMISSIONS.quotesUpdate);

function permissionGuard(permission: (typeof PERMISSIONS)[keyof typeof PERMISSIONS]) {
  const sessionService = inject(SessionService);
  const router = inject(Router);
  const user = sessionService.getUser();
  return user?.role === 'admin' || user?.permissions?.includes(permission)
    ? true
    : router.createUrlTree(['/panel/sin-permiso']);
}
