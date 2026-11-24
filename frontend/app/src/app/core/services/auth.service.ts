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
  UserMeResponse,
  TenantSaaS,
  SaaSPlan,
  PlatformAudit,
  PlatformAdminMe,
  UpdateTenantSubscriptionRequest,
} from '../models/auth.models';
import { PlanChangeRequest } from '../models/tenant-plan.models';

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

  updateProfile(fullName: string): Observable<UserMeResponse> {
    return this.http.patch<UserMeResponse>(`${this.baseUrl}/me`, { full_name: fullName });
  }

  changePassword(currentPassword: string, newPassword: string): Observable<void> {
    return this.http.post<void>(`${this.baseUrl}/change-password`, {
      current_password: currentPassword,
      new_password: newPassword,
    });
  }

  platformAdminLogin(request: PlatformAdminLoginRequest): Observable<PlatformAdminTokenResponse> {
    return this.http.post<PlatformAdminTokenResponse>('/api/platform-admin/auth/login', request);
  }

  platformAdminMe(): Observable<PlatformAdminMe> {
    return this.http.get<PlatformAdminMe>('/api/platform-admin/auth/me');
  }

  updatePlatformProfile(fullName: string): Observable<PlatformAdminMe> {
    return this.http.patch<PlatformAdminMe>('/api/platform-admin/auth/me', { full_name: fullName });
  }

  changePlatformPassword(currentPassword: string, newPassword: string): Observable<void> {
    return this.http.post<void>('/api/platform-admin/auth/change-password', {
      current_password: currentPassword,
      new_password: newPassword,
    });
  }

  acceptPlatformInvitation(token: string, password: string): Observable<PlatformAdminTokenResponse> {
    return this.http.post<PlatformAdminTokenResponse>('/api/platform-admin/auth/accept-invite', {
      token,
      password,
    });
  }

  createTenant(request: CreateTenantRequest): Observable<CreateTenantResponse> {
    return this.http.post<CreateTenantResponse>('/api/platform-admin/tenants', request);
  }

  listTenants(): Observable<TenantSaaS[]> {
    return this.http.get<TenantSaaS[]>('/api/platform-admin/tenants');
  }

  listSaaSPlans(): Observable<SaaSPlan[]> {
    return this.http.get<SaaSPlan[]>('/api/platform-admin/plans');
  }

  listPlatformAudit(): Observable<PlatformAudit[]> {
    return this.http.get<PlatformAudit[]>('/api/platform-admin/audit');
  }

  listSubscriptionRequests(): Observable<PlanChangeRequest[]> {
    return this.http.get<PlanChangeRequest[]>('/api/platform-admin/subscription-requests');
  }

  resolveSubscriptionRequest(
    id: string,
    status: 'approved' | 'rejected',
  ): Observable<PlanChangeRequest> {
    return this.http.patch<PlanChangeRequest>(
      `/api/platform-admin/subscription-requests/${id}`,
      { status },
    );
  }

  updateTenantSubscription(
    id: string,
    request: UpdateTenantSubscriptionRequest,
  ): Observable<TenantSaaS> {
    return this.http.patch<TenantSaaS>(`/api/platform-admin/tenants/${id}/subscription`, request);
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

  platformForgotPassword(request: ForgotPasswordRequest): Observable<ForgotPasswordResponse> {
    return this.http.post<ForgotPasswordResponse>('/api/platform-admin/auth/forgot-password', request);
  }

  platformResetPassword(request: ResetPasswordRequest): Observable<ResetPasswordResponse> {
    return this.http.post<ResetPasswordResponse>('/api/platform-admin/auth/reset-password', request);
  }
}
