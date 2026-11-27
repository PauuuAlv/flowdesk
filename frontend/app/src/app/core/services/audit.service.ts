import { HttpClient, HttpParams } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { Observable } from 'rxjs';

import { AuditFilters, AuditPage, AuditQuery, AuditScope } from '../models/audit.models';

const BASE_URL: Record<AuditScope, string> = {
  tenant: '/api/audit',
  platform: '/api/platform-admin/audit',
};

/** Parámetro del actor según la bitácora. */
const ACTOR_PARAM: Record<AuditScope, string> = { tenant: 'user_id', platform: 'admin_id' };

@Injectable({ providedIn: 'root' })
export class AuditService {
  private readonly http = inject(HttpClient);

  list(scope: AuditScope, query: AuditQuery): Observable<AuditPage> {
    const params = this.filterParams(scope, query)
      .set('page', query.page)
      .set('page_size', query.page_size);
    return this.http.get<AuditPage>(BASE_URL[scope], { params });
  }

  filters(scope: AuditScope): Observable<AuditFilters> {
    return this.http.get<AuditFilters>(`${BASE_URL[scope]}/filters`);
  }

  /** Reporte PDF con los mismos filtros de la pantalla (fechas en la zona horaria del navegador). */
  report(scope: AuditScope, query: Omit<AuditQuery, 'page' | 'page_size'>): Observable<Blob> {
    const timeZone = Intl.DateTimeFormat().resolvedOptions().timeZone;
    const params = this.filterParams(scope, query).set('tz', timeZone);
    return this.http.get(`${BASE_URL[scope]}/report.pdf`, { params, responseType: 'blob' });
  }

  private filterParams(scope: AuditScope, query: Partial<AuditQuery>): HttpParams {
    let params = new HttpParams();
    // Valores repetidos: ?operation=CREATE&operation=DELETE
    for (const operation of query.operations ?? []) params = params.append('operation', operation);
    for (const entity of query.entities ?? []) params = params.append('entity', entity);
    for (const actor of query.actor_ids ?? []) params = params.append(ACTOR_PARAM[scope], actor);
    if (query.search?.trim()) params = params.set('search', query.search.trim());
    if (query.date_from) params = params.set('date_from', query.date_from);
    if (query.date_to) params = params.set('date_to', query.date_to);
    return params;
  }
}
