import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';

import { RegisterRequest } from '../models/auth.models';
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
});
