import { HttpErrorResponse, HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';
import { Router } from '@angular/router';
import { catchError, finalize, Observable, shareReplay, switchMap, tap, throwError } from 'rxjs';

import { TokenResponse } from '../models/auth.models';
import { AuthService } from '../services/auth.service';
import { SessionService } from '../services/session.service';

let refreshRequest$: Observable<TokenResponse> | null = null;

const publicUserEndpoints = [
  '/api/auth/login',
  '/api/auth/register',
  '/api/auth/refresh',
  '/api/auth/forgot-password',
  '/api/auth/reset-password'
];

export const authInterceptor: HttpInterceptorFn = (request, next) => {
  const sessionService = inject(SessionService);
  const authService = inject(AuthService);
  const router = inject(Router);
  const isPlatformAdminRequest = request.url.startsWith('/api/platform-admin/');
  const isPlatformAdminLogin = request.url.startsWith('/api/platform-admin/auth/login');
  const isPublicUserRequest = publicUserEndpoints.some((url) => request.url.startsWith(url));
  const isProtectedUserRequest = request.url.startsWith('/api/') && !isPlatformAdminRequest && !isPublicUserRequest;
  const accessToken = sessionService.getAccessToken();

  if (isPlatformAdminRequest && !isPlatformAdminLogin) {
    const platformAdminToken = sessionService.getPlatformAdminToken();
    const platformRequest = platformAdminToken
      ? request.clone({ setHeaders: { Authorization: `Bearer ${platformAdminToken}` } })
      : request;

    return next(platformRequest).pipe(
      catchError((error: HttpErrorResponse) => {
        if (error.status === 401) {
          sessionService.clearPlatformAdmin();
          void router.navigate(['/administracion-flowdesk/iniciar-sesion']);
        }
        return throwError(() => error);
      })
    );
  }

  if (!isProtectedUserRequest) {
    return next(request);
  }

  const authenticatedRequest = accessToken
    ? request.clone({ setHeaders: { Authorization: `Bearer ${accessToken}` } })
    : request;

  return next(authenticatedRequest).pipe(
    catchError((error: HttpErrorResponse) => {
      const refreshToken = sessionService.getRefreshToken();
      if (error.status !== 401 || !refreshToken) return throwError(() => error);

      if (!refreshRequest$) {
        refreshRequest$ = authService.refresh({ refresh_token: refreshToken }).pipe(
          tap((tokens) => sessionService.saveTokens(tokens)),
          catchError((refreshError) => {
            sessionService.clear();
            void router.navigate(['/iniciar-sesion'], {
              queryParams: { sesion: 'expirada' }
            });
            return throwError(() => refreshError);
          }),
          finalize(() => (refreshRequest$ = null)),
          shareReplay(1)
        );
      }

      return refreshRequest$.pipe(
        switchMap((tokens) =>
          next(
            request.clone({
              setHeaders: { Authorization: `Bearer ${tokens.access_token}` }
            })
          )
        )
      );
    })
  );
};
