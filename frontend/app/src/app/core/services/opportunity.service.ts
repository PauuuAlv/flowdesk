import { HttpClient } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { Opportunity, OpportunityAssignee, OpportunityStage, SaveOpportunityRequest } from '../models/opportunity.models';

@Injectable({providedIn:'root'})
export class OpportunityService {
  private readonly http=inject(HttpClient);
  list():Observable<Opportunity[]>{return this.http.get<Opportunity[]>('/api/opportunities');}
  get(id:string):Observable<Opportunity>{return this.http.get<Opportunity>(`/api/opportunities/${id}`);}
  assignees():Observable<OpportunityAssignee[]>{return this.http.get<OpportunityAssignee[]>('/api/opportunities/assignees');}
  save(body:SaveOpportunityRequest,id?:string):Observable<Opportunity>{return id?this.http.patch<Opportunity>(`/api/opportunities/${id}`,body):this.http.post<Opportunity>('/api/opportunities',body);}
  updateStage(id:string,stage:OpportunityStage):Observable<Opportunity>{return this.http.patch<Opportunity>(`/api/opportunities/${id}/stage`,{stage});}
}
