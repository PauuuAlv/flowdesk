import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { OpportunityService } from './opportunity.service';

describe('OpportunityService',()=>{let service:OpportunityService;let http:HttpTestingController;beforeEach(()=>{TestBed.configureTestingModule({providers:[provideHttpClient(),provideHttpClientTesting()]});service=TestBed.inject(OpportunityService);http=TestBed.inject(HttpTestingController)});afterEach(()=>http.verify());
it('lists opportunities',()=>{service.list().subscribe();const r=http.expectOne('/api/opportunities');expect(r.request.method).toBe('GET');r.flush([])});
it('changes a stage',()=>{service.updateStage('1','proposal').subscribe();const r=http.expectOne('/api/opportunities/1/stage');expect(r.request.body).toEqual({stage:'proposal'});r.flush({})});});
