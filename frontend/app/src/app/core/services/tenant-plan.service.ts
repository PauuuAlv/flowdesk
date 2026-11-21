import { HttpClient } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { Observable } from 'rxjs';

import { SaaSPlanKey } from '../models/auth.models';
import { PlanChangeRequest, TenantPlan } from '../models/tenant-plan.models';

@Injectable({ providedIn: 'root' })
export class TenantPlanService {
  private readonly http = inject(HttpClient);
  get(): Observable<TenantPlan> { return this.http.get<TenantPlan>('/api/tenant-plan'); }
  requestChange(requested_plan_key: SaaSPlanKey, note: string | null): Observable<PlanChangeRequest> {
    return this.http.post<PlanChangeRequest>('/api/tenant-plan/change-requests', { requested_plan_key, note });
  }
}
