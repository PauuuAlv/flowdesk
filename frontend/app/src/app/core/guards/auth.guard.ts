import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';
import { catchError, map, of, tap } from 'rxjs';

import { AuthService } from '../services/auth.service';
import { SessionService } from '../services/session.service';

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

export const adminGuard: CanActivateFn = () => {
  const sessionService = inject(SessionService);
  const router = inject(Router);

  return sessionService.getUser()?.role === 'admin'
    ? true
    : router.createUrlTree(['/panel']);
};
