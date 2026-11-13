import { HttpClient } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { LossReason, Opportunity, OpportunityAssignee, OpportunityStage, SaveOpportunityRequest } from '../models/opportunity.models';

@Injectable({providedIn:'root'})
export class OpportunityService {
  private readonly http=inject(HttpClient);
  list(includeArchived=false):Observable<Opportunity[]>{return this.http.get<Opportunity[]>(`/api/opportunities?include_archived=${includeArchived}`);}
  get(id:string):Observable<Opportunity>{return this.http.get<Opportunity>(`/api/opportunities/${id}`);}
  assignees():Observable<OpportunityAssignee[]>{return this.http.get<OpportunityAssignee[]>('/api/opportunities/assignees');}
  save(body:SaveOpportunityRequest,id?:string):Observable<Opportunity>{return id?this.http.patch<Opportunity>(`/api/opportunities/${id}`,body):this.http.post<Opportunity>('/api/opportunities',body);}
  updateStage(id:string,stage:OpportunityStage):Observable<Opportunity>{return this.http.patch<Opportunity>(`/api/opportunities/${id}/stage`,{stage});}
  close(id:string,stage:'won'|'lost',loss_reason:LossReason|null=null,loss_detail:string|null=null):Observable<Opportunity>{return this.http.post<Opportunity>(`/api/opportunities/${id}/close`,{stage,loss_reason,loss_detail});}
  archive(id:string):Observable<Opportunity>{return this.http.post<Opportunity>(`/api/opportunities/${id}/archive`,{});}
  restore(id:string):Observable<Opportunity>{return this.http.post<Opportunity>(`/api/opportunities/${id}/restore`,{});}
}
