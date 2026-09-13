import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';

import {
  ForgotPasswordRequest,
  LoginRequest,
  RefreshRequest,
  RegisterRequest,
  ResetPasswordRequest
} from '../models/auth.models';
import { AuthService } from './auth.service';

describe('AuthService', () => {
  let service: AuthService;
  let httpController: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [AuthService, provideHttpClient(), provideHttpClientTesting()]
    });

    service = TestBed.inject(AuthService);
    httpController = TestBed.inject(HttpTestingController);
  });

  afterEach(() => httpController.verify());

  it('should send the register contract to the API', () => {
    const requestBody: RegisterRequest = {
      token: 'invitation-token',
      password: 'Contraseña123!'
    };

    service.register(requestBody).subscribe((response) => {
      expect(response.token_type).toBe('bearer');
    });

    const request = httpController.expectOne('/api/auth/register');
    expect(request.request.method).toBe('POST');
    expect(request.request.body).toEqual(requestBody);
    request.flush({
      access_token: 'access-token',
      refresh_token: 'refresh-token',
      token_type: 'bearer'
    });
  });

  it('should send the login contract to the API', () => {
    const requestBody: LoginRequest = {
      email: 'palvaradocamacho@gmail.com',
      password: 'Contraseña123!'
    };

    service.login(requestBody).subscribe((response) => {
      expect(response.token_type).toBe('bearer');
    });

    const request = httpController.expectOne('/api/auth/login');
    expect(request.request.method).toBe('POST');
    expect(request.request.body).toEqual(requestBody);
    request.flush({
      access_token: 'access-token',
      refresh_token: 'refresh-token',
      token_type: 'bearer'
    });
  });

  it('should request a new access token with the refresh token', () => {
    const requestBody: RefreshRequest = { refresh_token: 'refresh-token' };

    service.refresh(requestBody).subscribe((response) => {
      expect(response.access_token).toBe('new-access-token');
    });

    const request = httpController.expectOne('/api/auth/refresh');
    expect(request.request.method).toBe('POST');
    expect(request.request.body).toEqual(requestBody);
    request.flush({
      access_token: 'new-access-token',
      refresh_token: 'refresh-token',
      token_type: 'bearer'
    });
  });

  it('should request the current user profile', () => {
    service.me().subscribe((response) => {
      expect(response.tenant_id).toBe('tenant-uuid');
      expect(response.role).toBe('admin');
    });

    const request = httpController.expectOne('/api/auth/me');
    expect(request.request.method).toBe('GET');
    request.flush({
      id: 'user-uuid',
      tenant_id: 'tenant-uuid',
      email: 'paulina@empresa.com',
      full_name: 'Paulina Alvarado',
      role: 'admin',
      status: 'active'
    });
  });

  it('should use the separate platform administrator login endpoint', () => {
    const requestBody = {
      email: 'superadmin@flowdesk.com',
      password: 'secure-password'
    };

    service.platformAdminLogin(requestBody).subscribe((response) => {
      expect(response.token_type).toBe('bearer');
    });

    const request = httpController.expectOne('/api/platform-admin/auth/login');
    expect(request.request.method).toBe('POST');
    expect(request.request.body).toEqual(requestBody);
    request.flush({ access_token: 'platform-access-token', token_type: 'bearer' });
  });

  it('should create a tenant with its first invited administrator', () => {
    const requestBody = {
      name: 'Empresa de prueba',
      slug: 'empresa-prueba',
      admin_email: 'admin@example.com',
      admin_full_name: 'Admin de prueba'
    };

    service.createTenant(requestBody).subscribe((response) => {
      expect(response.tenant_slug).toBe(requestBody.slug);
      expect(response.dev_invitation_link).toContain('token=');
    });

    const request = httpController.expectOne('/api/platform-admin/tenants');
    expect(request.request.method).toBe('POST');
    expect(request.request.body).toEqual(requestBody);
    request.flush({
      tenant_id: 'tenant-id',
      tenant_name: requestBody.name,
      tenant_slug: requestBody.slug,
      admin_user_id: 'user-id',
      admin_email: requestBody.admin_email,
      dev_invitation_link: 'http://localhost/accept-invite?token=test-token'
    });
  });

  it('should invite a user without sending a tenant id', () => {
    const requestBody = {
      full_name: 'Daniel Ramírez',
      email: 'daniel@example.com',
      role: 'member' as const
    };

    service.inviteUser(requestBody).subscribe((response) => {
      expect(response.role).toBe('member');
      expect(response.dev_invitation_link).toContain('token=');
    });

    const request = httpController.expectOne('/api/users/invite');
    expect(request.request.method).toBe('POST');
    expect(request.request.body).toEqual(requestBody);
    expect(request.request.body.tenant_id).toBeUndefined();
    request.flush({
      user_id: 'user-id',
      email: requestBody.email,
      role: requestBody.role,
      dev_invitation_link: 'http://localhost/accept-invite?token=user-token'
    });
  });

  it('should request a password recovery link', () => {
    const requestBody: ForgotPasswordRequest = { email: 'palvaradocamacho@gmail.com' };
    service.forgotPassword(requestBody).subscribe((response) => {
      expect(response.message).toBeTruthy();
    });

    const request = httpController.expectOne('/api/auth/forgot-password');
    expect(request.request.method).toBe('POST');
    expect(request.request.body).toEqual(requestBody);
    request.flush({ message: 'Si el correo existe, se enviaron instrucciones.' });
  });

  it('should send the reset password contract without the confirmation field', () => {
    const requestBody: ResetPasswordRequest = { token: 'temporary-token', new_password: 'NuevaContraseña123!' };
    service.resetPassword(requestBody).subscribe((response) => {
      expect(response.message).toBeTruthy();
    });

    const request = httpController.expectOne('/api/auth/reset-password');
    expect(request.request.method).toBe('POST');
    expect(request.request.body).toEqual(requestBody);
    expect(request.request.body.password_confirmation).toBeUndefined();
    request.flush({ message: 'Contraseña actualizada correctamente.' });
  });
});
