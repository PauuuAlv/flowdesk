import { HttpClient, HttpParams } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { Observable } from 'rxjs';

import { TenantSaaS } from '../models/auth.models';
import { UpdateTenantRequest } from '../models/tenant.models';

/**
 * Acciones de gestión de una empresa (superadministrador): editar sus datos,
 * habilitarla/inhabilitarla y eliminarla. El listado, el plan y la suscripción
 * se manejan desde AuthService.
 */
@Injectable({ providedIn: 'root' })
export class TenantAdminService {
  private readonly http = inject(HttpClient);
  private readonly baseUrl = '/api/platform-admin/tenants';

  get(id: string): Observable<TenantSaaS> {
    return this.http.get<TenantSaaS>(`${this.baseUrl}/${id}`);
  }

  update(id: string, request: UpdateTenantRequest): Observable<TenantSaaS> {
    return this.http.patch<TenantSaaS>(`${this.baseUrl}/${id}`, request);
  }

  updateStatus(id: string, isActive: boolean): Observable<TenantSaaS> {
    return this.http.patch<TenantSaaS>(`${this.baseUrl}/${id}/status`, { is_active: isActive });
  }

  delete(id: string, confirmSlug: string): Observable<void> {
    const params = new HttpParams().set('confirm_slug', confirmSlug);
    return this.http.delete<void>(`${this.baseUrl}/${id}`, { params });
  }
}
