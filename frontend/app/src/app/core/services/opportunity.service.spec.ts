import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { OpportunityService } from './opportunity.service';

describe('OpportunityService', () => {
  let service: OpportunityService;
  let http: HttpTestingController;
  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting()],
    });
    service = TestBed.inject(OpportunityService);
    http = TestBed.inject(HttpTestingController);
  });
  afterEach(() => http.verify());
  it('lists active opportunities', () => {
    service.list().subscribe();
    const r = http.expectOne('/api/opportunities?include_archived=false');
    expect(r.request.method).toBe('GET');
    r.flush([]);
  });
  it('changes a stage', () => {
    service.updateStage('1', { stage: 'proposal', probability: 60, expected_close_date: null, note: 'Avance' }).subscribe();
    const r = http.expectOne('/api/opportunities/1/stage');
    expect(r.request.body).toEqual({ stage: 'proposal', probability: 60, expected_close_date: null, note: 'Avance' });
    r.flush({});
  });
  it('lists the tenant stage catalog', () => {
    service.stages(true, 'demo').subscribe();
    const r = http.expectOne(
      (request) =>
        request.url === '/api/opportunity-stages' &&
        request.params.get('include_inactive') === 'true' &&
        request.params.get('search') === 'demo',
    );
    expect(r.request.method).toBe('GET');
    r.flush([]);
  });
  it('creates a tenant stage', () => {
    service
      .createStage({
        pipeline_id: 'pipeline-1',
        name: 'Demostración',
        stage_type: 'normal',
        default_probability: 50,
        position: 3,
      })
      .subscribe();
    const r = http.expectOne('/api/opportunity-stages');
    expect(r.request.method).toBe('POST');
    expect(r.request.body.name).toBe('Demostración');
    r.flush({});
  });
  it('closes a lost opportunity with its reason', () => {
    service.close('1', 'lost', 'price', 'Fuera de presupuesto').subscribe();
    const r = http.expectOne('/api/opportunities/1/close');
    expect(r.request.body).toEqual({
      stage: 'lost',
      loss_reason: 'price',
      loss_detail: 'Fuera de presupuesto',
      note: null,
    });
    r.flush({});
  });
  it('archives and restores an opportunity', () => {
    service.archive('1').subscribe();
    const archive = http.expectOne('/api/opportunities/1/archive');
    expect(archive.request.method).toBe('POST');
    archive.flush({});
    service.restore('1').subscribe();
    const restore = http.expectOne('/api/opportunities/1/restore');
    expect(restore.request.method).toBe('POST');
    restore.flush({});
  });
});
