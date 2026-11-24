import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { catchError, Observable, throwError } from 'rxjs';

import { SaveRoleRequest, TenantMember, TenantRole } from '../models/access-control.models';

@Injectable({ providedIn: 'root' })
export class AccessControlService {
  private readonly http = inject(HttpClient);

  listRoles(): Observable<TenantRole[]> {
    return this.http.get<TenantRole[]>('/api/roles');
  }

  getRole(roleId: string): Observable<TenantRole> {
    return this.http.get<TenantRole>(`/api/roles/${roleId}`);
  }

  saveRole(request: SaveRoleRequest, roleId?: string): Observable<TenantRole> {
    const response = roleId
      ? this.http.patch<TenantRole>(`/api/roles/${roleId}`, request)
      : this.http.post<TenantRole>('/api/roles', request);
    return response.pipe(
      catchError((error: HttpErrorResponse) =>
        throwError(() => {
          const detail = error.error?.detail;
          if (error.status !== 409) return new Error('SAVE_ROLE_FAILED');
          // Ya existe otro rol con exactamente los mismos permisos.
          if (detail?.code === 'duplicate_permissions') {
            return new Error('DUPLICATE_PERMISSIONS', { cause: detail.role_name });
          }
          return new Error(String(detail ?? '').includes('own role') ? 'OWN_ROLE' : 'DUPLICATE_ROLE');
        }),
      ),
    );
  }

  deleteRole(roleId: string): Observable<void> {
    return this.http
      .delete<void>(`/api/roles/${roleId}`)
      .pipe(
        catchError((error: HttpErrorResponse) =>
          throwError(() => new Error(error.status === 409 ? 'ROLE_IN_USE' : 'DELETE_ROLE_FAILED')),
        ),
      );
  }

  listMembers(): Observable<TenantMember[]> {
    return this.http.get<TenantMember[]>('/api/users');
  }

  updateMemberRole(memberId: string, roleId: string): Observable<TenantMember> {
    return this.http.patch<TenantMember>(`/api/users/${memberId}/role`, { role_id: roleId });
  }

  deactivateMember(memberId: string): Observable<TenantMember> {
    return this.http.patch<TenantMember>(`/api/users/${memberId}/status`, { status: 'inactive' });
  }

  activateMember(memberId: string): Observable<TenantMember> {
    return this.http.patch<TenantMember>(`/api/users/${memberId}/status`, { status: 'active' });
  }

  resendInvitation(memberId: string): Observable<{ message: string }> {
    return this.http.post<{ message: string }>(`/api/users/${memberId}/resend-invitation`, {});
  }
}
