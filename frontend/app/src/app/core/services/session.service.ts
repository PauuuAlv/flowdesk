import { Injectable } from '@angular/core';

import { PlatformAdminTokenResponse, TokenResponse, UserMeResponse } from '../models/auth.models';

@Injectable({ providedIn: 'root' })
export class SessionService {
  private readonly accessTokenKey = 'flowdesk.access_token';
  private readonly refreshTokenKey = 'flowdesk.refresh_token';
  private readonly userKey = 'flowdesk.user';
  private readonly platformAdminTokenKey = 'flowdesk.platform_admin.access_token';

  saveTokens(tokens: TokenResponse): void {
    localStorage.setItem(this.accessTokenKey, tokens.access_token);
    localStorage.setItem(this.refreshTokenKey, tokens.refresh_token);
  }

  saveUser(user: UserMeResponse): void {
    localStorage.setItem(this.userKey, JSON.stringify(user));
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

  clearPlatformAdmin(): void {
    localStorage.removeItem(this.platformAdminTokenKey);
  }

  clear(): void {
    localStorage.removeItem(this.accessTokenKey);
    localStorage.removeItem(this.refreshTokenKey);
    localStorage.removeItem(this.userKey);
  }
}
