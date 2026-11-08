import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';

import { Client } from '../models/client.models';
import { ClientService } from './client.service';

describe('ClientService', () => {
  let service: ClientService;
  let httpController: HttpTestingController;
  const client: Client = {
    id: 'client-1',
    company_name: 'Empresa Demo',
    contact_name: 'Paulina Alvarado',
    email: 'cliente@example.com',
    phone: null,
    status: 'active',
    notes: null,
    created_at: '2026-11-08T00:00:00Z',
    updated_at: '2026-11-08T00:00:00Z'
  };

  beforeEach(() => {
    TestBed.configureTestingModule({ providers: [provideHttpClient(), provideHttpClientTesting()] });
    service = TestBed.inject(ClientService);
    httpController = TestBed.inject(HttpTestingController);
  });

  afterEach(() => httpController.verify());

  it('lists tenant clients', () => {
    service.list().subscribe((clients) => expect(clients).toEqual([client]));
    const request = httpController.expectOne('/api/clients');
    expect(request.request.method).toBe('GET');
    request.flush([client]);
  });

  it('creates a client', () => {
    const body = {
      company_name: client.company_name,
      contact_name: client.contact_name,
      email: client.email,
      phone: null,
      notes: null
    };
    service.save(body).subscribe((response) => expect(response).toEqual(client));
    const request = httpController.expectOne('/api/clients');
    expect(request.request.method).toBe('POST');
    expect(request.request.body).toEqual(body);
    request.flush(client);
  });

  it('updates the client status', () => {
    service.updateStatus(client.id, 'inactive').subscribe();
    const request = httpController.expectOne('/api/clients/client-1/status');
    expect(request.request.method).toBe('PATCH');
    expect(request.request.body).toEqual({ status: 'inactive' });
    request.flush({ ...client, status: 'inactive' });
  });
});
