import { HttpClient } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { Observable } from 'rxjs';

import { InvitePlatformMemberRequest, PlatformMember } from '../models/auth.models';
import { PlatformRole, SavePlatformRoleRequest } from '../models/platform-access.models';

/** Equipo de plataforma: integrantes y roles con sus permisos. */
@Injectable({ providedIn: 'root' })
export class PlatformTeamService {
  private readonly http = inject(HttpClient);
  private readonly teamUrl = '/api/platform-admin/team';
  private readonly rolesUrl = '/api/platform-admin/roles';

  listMembers(): Observable<PlatformMember[]> {
    return this.http.get<PlatformMember[]>(this.teamUrl);
  }

  invite(request: InvitePlatformMemberRequest): Observable<PlatformMember> {
    return this.http.post<PlatformMember>(`${this.teamUrl}/invite`, request);
  }

  updateRole(memberId: string, roleId: string): Observable<PlatformMember> {
    return this.http.patch<PlatformMember>(`${this.teamUrl}/${memberId}/role`, { role_id: roleId });
  }

  updateStatus(memberId: string, isActive: boolean): Observable<PlatformMember> {
    return this.http.patch<PlatformMember>(`${this.teamUrl}/${memberId}/status`, { is_active: isActive });
  }

  resendInvitation(memberId: string): Observable<PlatformMember> {
    return this.http.post<PlatformMember>(`${this.teamUrl}/${memberId}/resend-invitation`, {});
  }

  listRoles(): Observable<PlatformRole[]> {
    return this.http.get<PlatformRole[]>(this.rolesUrl);
  }

  saveRole(request: SavePlatformRoleRequest, roleId?: string): Observable<PlatformRole> {
    return roleId
      ? this.http.patch<PlatformRole>(`${this.rolesUrl}/${roleId}`, request)
      : this.http.post<PlatformRole>(this.rolesUrl, request);
  }

  deleteRole(roleId: string): Observable<void> {
    return this.http.delete<void>(`${this.rolesUrl}/${roleId}`);
  }
}
