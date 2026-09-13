import { HttpClient, provideHttpClient, withInterceptors } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';

import { SessionService } from '../services/session.service';
import { authInterceptor } from './auth.interceptor';

describe('authInterceptor', () => {
  let http: HttpClient;
  let httpController: HttpTestingController;
  let sessionService: SessionService;

  beforeEach(() => {
    localStorage.clear();
    TestBed.configureTestingModule({
      providers: [
        provideRouter([]),
        provideHttpClient(withInterceptors([authInterceptor])),
        provideHttpClientTesting()
      ]
    });

    http = TestBed.inject(HttpClient);
    httpController = TestBed.inject(HttpTestingController);
    sessionService = TestBed.inject(SessionService);
    sessionService.saveTokens({
      access_token: 'expired-access-token',
      refresh_token: 'valid-refresh-token',
      token_type: 'bearer'
    });
  });

  afterEach(() => {
    httpController.verify();
    localStorage.clear();
  });

  it('should refresh an expired access token and retry the protected request', () => {
    let receivedRole = '';
    http.get<{ role: string }>('/api/auth/me').subscribe((response) => {
      receivedRole = response.role;
    });

    const firstRequest = httpController.expectOne('/api/auth/me');
    expect(firstRequest.request.headers.get('Authorization')).toBe('Bearer expired-access-token');
    firstRequest.flush({}, { status: 401, statusText: 'Unauthorized' });

    const refreshRequest = httpController.expectOne('/api/auth/refresh');
    expect(refreshRequest.request.headers.has('Authorization')).toBeFalse();
    expect(refreshRequest.request.body).toEqual({ refresh_token: 'valid-refresh-token' });
    refreshRequest.flush({
      access_token: 'new-access-token',
      refresh_token: 'valid-refresh-token',
      token_type: 'bearer'
    });

    const retriedRequest = httpController.expectOne('/api/auth/me');
    expect(retriedRequest.request.headers.get('Authorization')).toBe('Bearer new-access-token');
    retriedRequest.flush({ role: 'admin' });

    expect(receivedRole).toBe('admin');
    expect(sessionService.getAccessToken()).toBe('new-access-token');
  });

  it('should use only the platform token for platform administrator requests', () => {
    sessionService.savePlatformAdminToken({
      access_token: 'platform-token',
      token_type: 'bearer'
    });

    http.post('/api/platform-admin/tenants', {}).subscribe();

    const request = httpController.expectOne('/api/platform-admin/tenants');
    expect(request.request.headers.get('Authorization')).toBe('Bearer platform-token');
    request.flush({});
  });
});
