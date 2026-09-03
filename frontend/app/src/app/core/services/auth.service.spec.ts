import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';

import {
  ForgotPasswordRequest,
  LoginRequest,
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
      name: 'Paulina Alvarado',
      company_name: 'ArmSystem',
      email: 'palvaradocamacho@gmail.com',
      password: 'Contraseña123!'
    };

    service.register(requestBody).subscribe((response) => {
      expect(response.message).toBe('Usuario creado correctamente');
    });

    const request = httpController.expectOne('/api/auth/register');
    expect(request.request.method).toBe('POST');
    expect(request.request.body).toEqual(requestBody);
    request.flush({
      message: 'Usuario creado correctamente',
      user: {
        id: 1,
        name: requestBody.name,
        email: requestBody.email,
        is_active: true,
        roles: ['owner']
      },
      tenant: { id: 1, name: requestBody.company_name }
    });
  });

  it('should send the login contract to the API', () => {
    const requestBody: LoginRequest = {
      email: 'palvaradocamacho@gmail.com',
      password: 'Contraseña123!'
    };

    service.login(requestBody).subscribe((response) => {
      expect(response.token_type).toBe('bearer');
      expect(response.expires_in).toBe(1800);
      expect(response.user.tenant_id).toBe(1);
    });

    const request = httpController.expectOne('/api/auth/login');
    expect(request.request.method).toBe('POST');
    expect(request.request.body).toEqual(requestBody);
    request.flush({
      access_token: 'access-token',
      refresh_token: 'refresh-token',
      token_type: 'bearer',
      expires_in: 1800,
      user: {
        id: 1,
        name: 'Paulina Alvarado',
        email: requestBody.email,
        tenant_id: 1,
        roles: ['owner'],
        permissions: []
      }
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
