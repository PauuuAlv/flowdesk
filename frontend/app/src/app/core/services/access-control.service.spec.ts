import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';

import { PERMISSIONS } from '../models/permission.models';
import { AccessControlService } from './access-control.service';

describe('AccessControlService', () => {
  let service: AccessControlService;
  let httpController: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [AccessControlService, provideHttpClient(), provideHttpClientTesting()]
    });
    service = TestBed.inject(AccessControlService);
    httpController = TestBed.inject(HttpTestingController);
  });

  afterEach(() => httpController.verify());

  it('should list the roles of the authenticated tenant', () => {
    service.listRoles().subscribe((roles) => expect(roles.length).toBe(1));
    const request = httpController.expectOne('/api/roles');
    expect(request.request.method).toBe('GET');
    request.flush([{ id: 'role-1', name: 'Miembro' }]);
  });

  it('should create a role with its permissions', () => {
    const body = {
      name: 'Contabilidad',
      description: 'Consulta información financiera de clientes.',
      permissions: [PERMISSIONS.dashboardView, PERMISSIONS.clientsView]
    };
    service.saveRole(body).subscribe();
    const request = httpController.expectOne('/api/roles');
    expect(request.request.method).toBe('POST');
    expect(request.request.body).toEqual(body);
    request.flush({ id: 'role-2', ...body });
  });

  it('should update an existing role', () => {
    const body = {
      name: 'Supervisor',
      description: 'Supervisa la operación de la empresa.',
      permissions: [PERMISSIONS.dashboardView]
    };
    service.saveRole(body, 'role-2').subscribe();
    const request = httpController.expectOne('/api/roles/role-2');
    expect(request.request.method).toBe('PATCH');
    request.flush({ id: 'role-2', ...body });
  });

  it('should list tenant members', () => {
    service.listMembers().subscribe();
    const request = httpController.expectOne('/api/users');
    expect(request.request.method).toBe('GET');
    request.flush([]);
  });

  it('should update a member role without sending a tenant id', () => {
    service.updateMemberRole('user-1', 'role-2').subscribe();
    const request = httpController.expectOne('/api/users/user-1/role');
    expect(request.request.method).toBe('PATCH');
    expect(request.request.body).toEqual({ role_id: 'role-2' });
    expect(request.request.body.tenant_id).toBeUndefined();
    request.flush({});
  });

  it('should deactivate a member', () => {
    service.deactivateMember('user-1').subscribe();
    const request = httpController.expectOne('/api/users/user-1/status');
    expect(request.request.method).toBe('PATCH');
    expect(request.request.body).toEqual({ status: 'inactive' });
    request.flush({});
  });

  it('should reactivate a member', () => {
    service.activateMember('user-1').subscribe();
    const request = httpController.expectOne('/api/users/user-1/status');
    expect(request.request.method).toBe('PATCH');
    expect(request.request.body).toEqual({ status: 'active' });
    request.flush({});
  });

  it('should request a new invitation for a pending member', () => {
    service.resendInvitation('user-1').subscribe();
    const request = httpController.expectOne('/api/users/user-1/resend-invitation');
    expect(request.request.method).toBe('POST');
    request.flush({ message: 'Invitation generated' });
  });
});
