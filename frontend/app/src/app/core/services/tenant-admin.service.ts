import { HttpClient, HttpParams } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { Observable } from 'rxjs';

import { TenantSummary, UpdateTenantRequest } from '../models/tenant.models';

/** Gestión de empresas desde la administración de plataforma (superadmin). */
@Injectable({ providedIn: 'root' })
export class TenantAdminService {
  private readonly http = inject(HttpClient);
  private readonly baseUrl = '/api/platform-admin/tenants';

  list(): Observable<TenantSummary[]> {
    return this.http.get<TenantSummary[]>(this.baseUrl);
  }

  update(id: string, request: UpdateTenantRequest): Observable<TenantSummary> {
    return this.http.patch<TenantSummary>(`${this.baseUrl}/${id}`, request);
  }

  updateStatus(id: string, isActive: boolean): Observable<TenantSummary> {
    return this.http.patch<TenantSummary>(`${this.baseUrl}/${id}/status`, { is_active: isActive });
  }

  delete(id: string, confirmSlug: string): Observable<void> {
    const params = new HttpParams().set('confirm_slug', confirmSlug);
    return this.http.delete<void>(`${this.baseUrl}/${id}`, { params });
  }
}
