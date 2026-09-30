import { Injectable } from '@angular/core';
import { delay, Observable, of, throwError } from 'rxjs';

import { SaveRoleRequest, TenantMember, TenantRole } from '../models/access-control.models';
import { PERMISSIONS } from '../models/permission.models';

@Injectable({ providedIn: 'root' })
export class AccessControlPreviewService {
  private roles: TenantRole[] = [
    {
      id: 'role-admin',
      name: 'Administrador',
      description: 'Control completo de la configuración y operación de la empresa.',
      origin: 'template',
      is_protected: true,
      user_count: 2,
      permissions: Object.values(PERMISSIONS)
    },
    {
      id: 'role-supervisor',
      name: 'Supervisor',
      description: 'Consulta la operación y administra clientes sin cambiar la configuración.',
      origin: 'template',
      is_protected: false,
      user_count: 3,
      permissions: [
        PERMISSIONS.dashboardView,
        PERMISSIONS.usersView,
        PERMISSIONS.clientsView,
        PERMISSIONS.clientsCreate,
        PERMISSIONS.clientsUpdate
      ]
    },
    {
      id: 'role-member',
      name: 'Miembro',
      description: 'Acceso básico a los módulos operativos asignados.',
      origin: 'template',
      is_protected: false,
      user_count: 5,
      permissions: [PERMISSIONS.dashboardView, PERMISSIONS.clientsView]
    }
  ];

  private members: TenantMember[] = [
    { id: 'member-1', full_name: 'Paulina Alvarado', email: 'paulina@empresa.com', role_id: 'role-admin', role_name: 'Administrador', status: 'active' },
    { id: 'member-2', full_name: 'Daniel Ramírez', email: 'daniel@empresa.com', role_id: 'role-supervisor', role_name: 'Supervisor', status: 'active' },
    { id: 'member-3', full_name: 'María López', email: 'maria@empresa.com', role_id: 'role-member', role_name: 'Miembro', status: 'pending' }
  ];

  listRoles(): Observable<TenantRole[]> {
    return of(this.cloneRoles()).pipe(delay(250));
  }

  getRole(roleId: string): Observable<TenantRole> {
    const role = this.roles.find((item) => item.id === roleId);
    return role
      ? of({ ...role, permissions: [...role.permissions] }).pipe(delay(200))
      : throwError(() => new Error('Role not found'));
  }

  saveRole(request: SaveRoleRequest, roleId?: string): Observable<TenantRole> {
    const duplicated = this.roles.some(
      (role) => role.id !== roleId && role.name.toLowerCase() === request.name.toLowerCase()
    );
    if (duplicated) return throwError(() => new Error('DUPLICATE_ROLE'));

    const current = roleId ? this.roles.find((role) => role.id === roleId) : undefined;
    const saved: TenantRole = {
      id: current?.id ?? `role-${Date.now()}`,
      name: request.name,
      description: request.description,
      permissions: [...request.permissions],
      origin: current?.origin ?? 'custom',
      is_protected: current?.is_protected ?? false,
      user_count: current?.user_count ?? 0
    };

    this.roles = current
      ? this.roles.map((role) => (role.id === current.id ? saved : role))
      : [...this.roles, saved];
    return of({ ...saved, permissions: [...saved.permissions] }).pipe(delay(300));
  }

  deleteRole(roleId: string): Observable<void> {
    const role = this.roles.find((item) => item.id === roleId);
    if (!role || role.is_protected || role.user_count > 0) {
      return throwError(() => new Error('ROLE_IN_USE'));
    }
    this.roles = this.roles.filter((item) => item.id !== roleId);
    return of(undefined).pipe(delay(250));
  }

  listMembers(): Observable<TenantMember[]> {
    return of(this.members.map((member) => ({ ...member }))).pipe(delay(250));
  }

  updateMemberRole(memberId: string, roleId: string): Observable<TenantMember> {
    const role = this.roles.find((item) => item.id === roleId);
    const member = this.members.find((item) => item.id === memberId);
    if (!role || !member) return throwError(() => new Error('MEMBER_NOT_FOUND'));
    const updated = { ...member, role_id: role.id, role_name: role.name };
    this.members = this.members.map((item) => (item.id === memberId ? updated : item));
    return of({ ...updated }).pipe(delay(250));
  }

  deactivateMember(memberId: string): Observable<TenantMember> {
    const member = this.members.find((item) => item.id === memberId);
    if (!member) return throwError(() => new Error('MEMBER_NOT_FOUND'));
    const updated: TenantMember = { ...member, status: 'inactive' };
    this.members = this.members.map((item) => (item.id === memberId ? updated : item));
    return of({ ...updated }).pipe(delay(250));
  }

  resendInvitation(memberId: string): Observable<void> {
    return this.members.some((member) => member.id === memberId && member.status === 'pending')
      ? of(undefined).pipe(delay(250))
      : throwError(() => new Error('INVITATION_NOT_AVAILABLE'));
  }

  private cloneRoles(): TenantRole[] {
    return this.roles.map((role) => ({ ...role, permissions: [...role.permissions] }));
  }
}
