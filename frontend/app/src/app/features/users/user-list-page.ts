import { Component, computed, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { forkJoin } from 'rxjs';

import { MemberStatus, TenantMember, TenantRole } from '../../core/models/access-control.models';
import { AccessControlPreviewService } from '../../core/services/access-control-preview.service';

@Component({
  selector: 'app-user-list-page',
  imports: [RouterLink],
  templateUrl: './user-list-page.html',
  styleUrls: ['./user-list-page.scss', './user-list-page.states.scss']
})
export class UserListPage {
  private readonly accessControl = inject(AccessControlPreviewService);

  protected readonly users = signal<TenantMember[]>([]);
  protected readonly roles = signal<TenantRole[]>([]);
  protected readonly loading = signal(true);
  protected readonly errorMessage = signal('');
  protected readonly successMessage = signal('');
  protected readonly search = signal('');
  protected readonly statusFilter = signal<MemberStatus | 'all'>('all');
  protected readonly roleFilter = signal('all');
  protected readonly userToDeactivate = signal<TenantMember | null>(null);
  protected readonly processing = signal(false);

  protected readonly filteredUsers = computed(() => {
    const term = this.search().trim().toLowerCase();
    return this.users().filter((user) => {
      const matchesTerm = !term || `${user.full_name} ${user.email}`.toLowerCase().includes(term);
      const matchesStatus = this.statusFilter() === 'all' || user.status === this.statusFilter();
      const matchesRole = this.roleFilter() === 'all' || user.role_id === this.roleFilter();
      return matchesTerm && matchesStatus && matchesRole;
    });
  });

  constructor() {
    this.loadData();
  }

  protected loadData(): void {
    this.loading.set(true);
    this.errorMessage.set('');
    forkJoin({ users: this.accessControl.listMembers(), roles: this.accessControl.listRoles() }).subscribe({
      next: ({ users, roles }) => {
        this.users.set(users);
        this.roles.set(roles);
        this.loading.set(false);
      },
      error: () => {
        this.loading.set(false);
        this.errorMessage.set('No fue posible consultar los usuarios. Intenta nuevamente.');
      }
    });
  }

  protected updateSearch(event: Event): void {
    this.search.set((event.target as HTMLInputElement).value);
  }

  protected updateStatus(event: Event): void {
    this.statusFilter.set((event.target as HTMLSelectElement).value as MemberStatus | 'all');
  }

  protected updateRoleFilter(event: Event): void {
    this.roleFilter.set((event.target as HTMLSelectElement).value);
  }

  protected changeRole(user: TenantMember, event: Event): void {
    const roleId = (event.target as HTMLSelectElement).value;
    this.successMessage.set('');
    this.accessControl.updateMemberRole(user.id, roleId).subscribe({
      next: (updated) => {
        this.users.update((users) => users.map((item) => (item.id === updated.id ? updated : item)));
        this.successMessage.set(`El rol de ${updated.full_name} se actualizó correctamente.`);
      },
      error: () => this.errorMessage.set('No fue posible actualizar el rol del usuario.')
    });
  }

  protected resendInvitation(user: TenantMember): void {
    this.successMessage.set('');
    this.accessControl.resendInvitation(user.id).subscribe({
      next: () => this.successMessage.set(`La invitación para ${user.email} se generó nuevamente.`),
      error: () => this.errorMessage.set('No fue posible reenviar la invitación.')
    });
  }

  protected requestDeactivate(user: TenantMember): void {
    this.userToDeactivate.set(user);
  }

  protected cancelDeactivate(): void {
    this.userToDeactivate.set(null);
  }

  protected confirmDeactivate(): void {
    const user = this.userToDeactivate();
    if (!user) return;
    this.processing.set(true);
    this.accessControl.deactivateMember(user.id).subscribe({
      next: (updated) => {
        this.processing.set(false);
        this.userToDeactivate.set(null);
        this.users.update((users) => users.map((item) => (item.id === updated.id ? updated : item)));
        this.successMessage.set(`${updated.full_name} quedó inactivo.`);
      },
      error: () => {
        this.processing.set(false);
        this.userToDeactivate.set(null);
        this.errorMessage.set('No fue posible desactivar al usuario.');
      }
    });
  }

  protected statusLabel(status: MemberStatus): string {
    return { active: 'Activo', pending: 'Invitación pendiente', inactive: 'Inactivo' }[status];
  }
}
