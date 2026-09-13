import { TestBed } from '@angular/core/testing';

import { SessionService } from './session.service';

describe('SessionService', () => {
  let service: SessionService;

  beforeEach(() => {
    localStorage.clear();
    TestBed.configureTestingModule({ providers: [SessionService] });
    service = TestBed.inject(SessionService);
  });

  afterEach(() => localStorage.clear());

  it('should store and clear a tenant user session', () => {
    service.saveTokens({
      access_token: 'access-token',
      refresh_token: 'refresh-token',
      token_type: 'bearer'
    });
    service.saveUser({
      id: 'user-id',
      tenant_id: 'tenant-id',
      email: 'user@example.com',
      full_name: 'Test User',
      role: 'admin',
      status: 'active'
    });

    expect(service.getAccessToken()).toBe('access-token');
    expect(service.getRefreshToken()).toBe('refresh-token');
    expect(service.getUser()?.tenant_id).toBe('tenant-id');

    service.clear();
    expect(service.getAccessToken()).toBeNull();
    expect(service.getRefreshToken()).toBeNull();
    expect(service.getUser()).toBeNull();
  });

  it('should keep the platform administrator token separate', () => {
    service.savePlatformAdminToken({
      access_token: 'platform-token',
      token_type: 'bearer'
    });

    expect(service.getPlatformAdminToken()).toBe('platform-token');
    expect(service.getAccessToken()).toBeNull();

    service.clearPlatformAdmin();
    expect(service.getPlatformAdminToken()).toBeNull();
  });
});
