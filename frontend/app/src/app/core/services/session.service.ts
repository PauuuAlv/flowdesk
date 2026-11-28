import { inject, Injectable } from '@angular/core';
import { Subject } from 'rxjs';

import { PlatformAdminTokenResponse, TokenResponse, UserMeResponse } from '../models/auth.models';
import { KnownAccountsService } from './known-accounts.service';

@Injectable({ providedIn: 'root' })
export class SessionService {
  private readonly knownAccounts = inject(KnownAccountsService);
  private readonly userUpdates = new Subject<UserMeResponse | null>();
  readonly userUpdates$ = this.userUpdates.asObservable();
  private readonly accessTokenKey = 'flowdesk.access_token';
  private readonly refreshTokenKey = 'flowdesk.refresh_token';
  private readonly userKey = 'flowdesk.user';
  private readonly platformAdminTokenKey = 'flowdesk.platform_admin.access_token';
  private readonly platformAdminEmailKey = 'flowdesk.platform_admin.email';

  saveTokens(tokens: TokenResponse): void {
    localStorage.setItem(this.accessTokenKey, tokens.access_token);
    localStorage.setItem(this.refreshTokenKey, tokens.refresh_token);
  }

  saveUser(user: UserMeResponse): void {
    localStorage.setItem(this.userKey, JSON.stringify(user));
    // Se recuerda en el selector de cuentas de este navegador.
    this.knownAccounts.remember(user);
    this.userUpdates.next(user);
  }

  getAccessToken(): string | null {
    return localStorage.getItem(this.accessTokenKey);
  }

  getRefreshToken(): string | null {
    return localStorage.getItem(this.refreshTokenKey);
  }

  getUser(): UserMeResponse | null {
    const storedUser = localStorage.getItem(this.userKey);
    if (!storedUser) return null;

    try {
      return JSON.parse(storedUser) as UserMeResponse;
    } catch {
      localStorage.removeItem(this.userKey);
      return null;
    }
  }

  savePlatformAdminToken(tokens: PlatformAdminTokenResponse): void {
    localStorage.setItem(this.platformAdminTokenKey, tokens.access_token);
  }

  getPlatformAdminToken(): string | null {
    return localStorage.getItem(this.platformAdminTokenKey);
  }

  savePlatformAdminEmail(email: string): void {
    localStorage.setItem(this.platformAdminEmailKey, email);
  }

  getPlatformAdminEmail(): string | null {
    return localStorage.getItem(this.platformAdminEmailKey);
  }

  clearPlatformAdmin(): void {
    localStorage.removeItem(this.platformAdminTokenKey);
    localStorage.removeItem(this.platformAdminEmailKey);
  }

  clear(): void {
    localStorage.removeItem(this.accessTokenKey);
    localStorage.removeItem(this.refreshTokenKey);
    localStorage.removeItem(this.userKey);
    this.userUpdates.next(null);
  }
}
