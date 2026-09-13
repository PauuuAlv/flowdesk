import { HttpClient } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { Observable } from 'rxjs';

import {
  CreateTenantRequest,
  CreateTenantResponse,
  ForgotPasswordRequest,
  ForgotPasswordResponse,
  InviteUserRequest,
  InviteUserResponse,
  LoginRequest,
  PlatformAdminLoginRequest,
  PlatformAdminTokenResponse,
  RefreshRequest,
  RegisterRequest,
  ResetPasswordRequest,
  ResetPasswordResponse,
  TokenResponse,
  UserMeResponse
} from '../models/auth.models';

@Injectable({ providedIn: 'root' })
export class AuthService {
  private readonly http = inject(HttpClient);
  private readonly baseUrl = '/api/auth';

  register(request: RegisterRequest): Observable<TokenResponse> {
    return this.http.post<TokenResponse>(`${this.baseUrl}/register`, request);
  }

  login(request: LoginRequest): Observable<TokenResponse> {
    return this.http.post<TokenResponse>(`${this.baseUrl}/login`, request);
  }

  refresh(request: RefreshRequest): Observable<TokenResponse> {
    return this.http.post<TokenResponse>(`${this.baseUrl}/refresh`, request);
  }

  me(): Observable<UserMeResponse> {
    return this.http.get<UserMeResponse>(`${this.baseUrl}/me`);
  }

  platformAdminLogin(request: PlatformAdminLoginRequest): Observable<PlatformAdminTokenResponse> {
    return this.http.post<PlatformAdminTokenResponse>('/api/platform-admin/auth/login', request);
  }

  createTenant(request: CreateTenantRequest): Observable<CreateTenantResponse> {
    return this.http.post<CreateTenantResponse>('/api/platform-admin/tenants', request);
  }

  inviteUser(request: InviteUserRequest): Observable<InviteUserResponse> {
    return this.http.post<InviteUserResponse>('/api/users/invite', request);
  }

  forgotPassword(request: ForgotPasswordRequest): Observable<ForgotPasswordResponse> {
    return this.http.post<ForgotPasswordResponse>(`${this.baseUrl}/forgot-password`, request);
  }

  resetPassword(request: ResetPasswordRequest): Observable<ResetPasswordResponse> {
    return this.http.post<ResetPasswordResponse>(`${this.baseUrl}/reset-password`, request);
  }
}
