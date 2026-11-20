import { HttpClient } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import {
  LossReason,
  Opportunity,
  OpportunityAssignee,
  OpportunityStageCatalog,
  OpportunityStageHistory,
  SaveOpportunityStageRequest,
  OpportunityStage,
  SaveOpportunityRequest,
} from '../models/opportunity.models';

@Injectable({ providedIn: 'root' })
export class OpportunityService {
  private readonly http = inject(HttpClient);
  list(includeArchived = false): Observable<Opportunity[]> {
    return this.http.get<Opportunity[]>(`/api/opportunities?include_archived=${includeArchived}`);
  }
  get(id: string): Observable<Opportunity> {
    return this.http.get<Opportunity>(`/api/opportunities/${id}`);
  }
  assignees(): Observable<OpportunityAssignee[]> {
    return this.http.get<OpportunityAssignee[]>('/api/opportunities/assignees');
  }
  stages(includeInactive = false, search = ''): Observable<OpportunityStageCatalog[]> {
    return this.http.get<OpportunityStageCatalog[]>('/api/opportunity-stages', {
      params: { include_inactive: includeInactive, search },
    });
  }
  createStage(body: SaveOpportunityStageRequest): Observable<OpportunityStageCatalog> {
    return this.http.post<OpportunityStageCatalog>('/api/opportunity-stages', body);
  }
  updateCatalogStage(
    id: string,
    body: SaveOpportunityStageRequest & { is_active: boolean },
  ): Observable<OpportunityStageCatalog> {
    return this.http.patch<OpportunityStageCatalog>(`/api/opportunity-stages/${id}`, body);
  }
  save(body: SaveOpportunityRequest, id?: string): Observable<Opportunity> {
    return id
      ? this.http.patch<Opportunity>(`/api/opportunities/${id}`, body)
      : this.http.post<Opportunity>('/api/opportunities', body);
  }
  updateStage(
    id: string,
    body: {
      stage: OpportunityStage;
      probability: number;
      expected_close_date: string | null;
      note: string | null;
    },
  ): Observable<Opportunity> {
    return this.http.patch<Opportunity>(`/api/opportunities/${id}/stage`, body);
  }
  close(
    id: string,
    stage: OpportunityStage,
    loss_reason: LossReason | null = null,
    loss_detail: string | null = null,
    note: string | null = null,
  ): Observable<Opportunity> {
    return this.http.post<Opportunity>(`/api/opportunities/${id}/close`, {
      stage,
      loss_reason,
      loss_detail,
      note,
    });
  }
  history(id: string): Observable<OpportunityStageHistory[]> {
    return this.http.get<OpportunityStageHistory[]>(`/api/opportunities/${id}/history`);
  }
  archive(id: string): Observable<Opportunity> {
    return this.http.post<Opportunity>(`/api/opportunities/${id}/archive`, {});
  }
  restore(id: string): Observable<Opportunity> {
    return this.http.post<Opportunity>(`/api/opportunities/${id}/restore`, {});
  }
}
