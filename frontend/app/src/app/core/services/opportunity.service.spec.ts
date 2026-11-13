import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { OpportunityService } from './opportunity.service';

describe('OpportunityService',()=>{let service:OpportunityService;let http:HttpTestingController;beforeEach(()=>{TestBed.configureTestingModule({providers:[provideHttpClient(),provideHttpClientTesting()]});service=TestBed.inject(OpportunityService);http=TestBed.inject(HttpTestingController)});afterEach(()=>http.verify());
it('lists active opportunities',()=>{service.list().subscribe();const r=http.expectOne('/api/opportunities?include_archived=false');expect(r.request.method).toBe('GET');r.flush([])});
it('changes a stage',()=>{service.updateStage('1','proposal').subscribe();const r=http.expectOne('/api/opportunities/1/stage');expect(r.request.body).toEqual({stage:'proposal'});r.flush({})});
it('closes a lost opportunity with its reason',()=>{service.close('1','lost','price','Fuera de presupuesto').subscribe();const r=http.expectOne('/api/opportunities/1/close');expect(r.request.body).toEqual({stage:'lost',loss_reason:'price',loss_detail:'Fuera de presupuesto'});r.flush({})});
it('archives and restores an opportunity',()=>{service.archive('1').subscribe();const archive=http.expectOne('/api/opportunities/1/archive');expect(archive.request.method).toBe('POST');archive.flush({});service.restore('1').subscribe();const restore=http.expectOne('/api/opportunities/1/restore');expect(restore.request.method).toBe('POST');restore.flush({})});});
