import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { ContactService } from './contact.service';

describe('ContactService', () => {
  let service: ContactService;
  let http: HttpTestingController;
  const request = { full_name: 'Ana López', job_title: null, email: null, phone: null, is_primary: false };

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting()],
    });
    service = TestBed.inject(ContactService);
    http = TestBed.inject(HttpTestingController);
  });
  afterEach(() => http.verify());

  it('lists the contacts of a client', () => {
    service.list('c1').subscribe();
    const r = http.expectOne('/api/clients/c1/contacts');
    expect(r.request.method).toBe('GET');
    r.flush([]);
  });

  it('creates a contact with POST and updates with PATCH', () => {
    service.save('c1', request).subscribe();
    const created = http.expectOne('/api/clients/c1/contacts');
    expect(created.request.method).toBe('POST');
    expect(created.request.body).toEqual(request);
    created.flush({});

    service.save('c1', request, 'k1').subscribe();
    const updated = http.expectOne('/api/clients/c1/contacts/k1');
    expect(updated.request.method).toBe('PATCH');
    updated.flush({});
  });

  it('marks a contact as primary and deletes it', () => {
    service.setPrimary('c1', 'k1').subscribe();
    const primary = http.expectOne('/api/clients/c1/contacts/k1/primary');
    expect(primary.request.method).toBe('POST');
    primary.flush({});

    service.delete('c1', 'k1').subscribe();
    const removed = http.expectOne('/api/clients/c1/contacts/k1');
    expect(removed.request.method).toBe('DELETE');
    removed.flush(null);
  });
});
