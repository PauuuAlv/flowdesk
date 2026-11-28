import { Component, computed, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { forkJoin } from 'rxjs';

import { MemberStatus, TenantMember, TenantRole } from '../../core/models/access-control.models';
import { AccessControlService } from '../../core/services/access-control.service';
import { PERMISSIONS } from '../../core/models/permission.models';
import { SessionService } from '../../core/services/session.service';
import { Combobox, ComboOption } from '../../shared/ui/combobox/combobox';
import { MultiSelect } from '../../shared/ui/multi-select/multi-select';

@Component({
  selector: 'app-user-list-page',
  imports: [RouterLink, Combobox, MultiSelect],
  templateUrl: './user-list-page.html',
  styleUrls: ['./user-list-page.scss', './user-list-page.states.scss'],
})
export class UserListPage {
  private readonly accessControl = inject(AccessControlService);
  private readonly sessionService = inject(SessionService);
  private readonly currentUser = this.sessionService.getUser();

  protected readonly users = signal<TenantMember[]>([]);
  protected readonly roles = signal<TenantRole[]>([]);
  protected readonly roleFilterOptions = computed<ComboOption[]>(() =>
    this.roles().map((role) => ({ value: role.id, label: role.name })),
  );
  protected readonly roleOptions = computed<ComboOption[]>(() =>
    this.roles().map((role) => ({ value: role.id, label: role.name })),
  );
  protected readonly loading = signal(true);
  protected readonly errorMessage = signal('');
  protected readonly successMessage = signal('');
  protected readonly search = signal('');
  // Cada filtro admite varios valores; vacío = todos.
  protected readonly statusFilter = signal<MemberStatus[]>([]);
  protected readonly roleFilter = signal<string[]>([]);
  protected readonly userToDeactivate = signal<TenantMember | null>(null);
  protected readonly processing = signal(false);

  protected readonly canInvite = this.hasPermission(PERMISSIONS.usersInvite);
  protected readonly canUpdate = this.hasPermission(PERMISSIONS.usersUpdate);
  protected readonly canDeactivate = this.hasPermission(PERMISSIONS.usersDelete);

  protected readonly filteredUsers = computed(() => {
    const term = this.search().trim().toLowerCase();
    return this.users().filter((user) => {
      const matchesTerm = !term || `${user.full_name} ${user.email}`.toLowerCase().includes(term);
      const matchesStatus = !this.statusFilter().length || this.statusFilter().includes(user.status);
      const matchesRole = !this.roleFilter().length || this.roleFilter().includes(user.role_id);
      return matchesTerm && matchesStatus && matchesRole;
    });
  });

  constructor() {
    this.loadData();
  }

  protected loadData(): void {
    this.loading.set(true);
    this.errorMessage.set('');
    forkJoin({
      users: this.accessControl.listMembers(),
      roles: this.accessControl.listRoles(),
    }).subscribe({
      next: ({ users, roles }) => {
        this.users.set(users);
        this.roles.set(roles);
        this.loading.set(false);
      },
      error: () => {
        this.loading.set(false);
        this.errorMessage.set('No fue posible consultar los usuarios. Intenta nuevamente.');
      },
    });
  }

  protected updateSearch(event: Event): void {
    this.search.set((event.target as HTMLInputElement).value);
  }

  protected updateStatus(values: string[]): void {
    this.statusFilter.set(values as MemberStatus[]);
  }

  protected updateRoleFilter(values: string[]): void {
    this.roleFilter.set(values);
  }

  protected changeRole(user: TenantMember, roleId: string, combo: Combobox): void {
    if (roleId === user.role_id) return;
    this.successMessage.set('');
    this.accessControl.updateMemberRole(user.id, roleId).subscribe({
      next: (updated) => {
        this.users.update((users) =>
          users.map((item) => (item.id === updated.id ? updated : item)),
        );
        this.successMessage.set(`El rol de ${updated.full_name} se actualizó correctamente.`);
      },
      error: (error: { status?: number }) => {
        this.errorMessage.set(
          error?.status === 409
            ? 'No es posible cambiar ese rol: la empresa debe conservar al menos un Administrador activo y no puedes cambiar tu propio rol.'
            : 'No fue posible actualizar el rol del usuario.',
        );
        combo.writeValue(user.role_id); // vuelve a mostrar el rol que conserva
        this.loadData();
      },
    });
  }

  protected isSelf(user: TenantMember): boolean {
    return user.id === this.currentUser?.id;
  }

  protected resendInvitation(user: TenantMember): void {
    this.successMessage.set('');
    this.accessControl.resendInvitation(user.id).subscribe({
      next: () => this.successMessage.set(`La invitación para ${user.email} se generó nuevamente.`),
      error: () => this.errorMessage.set('No fue posible reenviar la invitación.'),
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
        this.users.update((users) =>
          users.map((item) => (item.id === updated.id ? updated : item)),
        );
        this.successMessage.set(`${updated.full_name} quedó inactivo.`);
      },
      error: () => {
        this.processing.set(false);
        this.userToDeactivate.set(null);
        this.errorMessage.set('No fue posible desactivar al usuario.');
      },
    });
  }

  protected reactivate(user: TenantMember): void {
    this.processing.set(true);
    this.errorMessage.set('');
    this.accessControl.activateMember(user.id).subscribe({
      next: (updated) => {
        this.processing.set(false);
        this.users.update((users) =>
          users.map((item) => (item.id === updated.id ? updated : item)),
        );
        this.successMessage.set(`${updated.full_name} puede ingresar nuevamente.`);
      },
      error: () => {
        this.processing.set(false);
        this.errorMessage.set('No fue posible reactivar al usuario.');
      },
    });
  }

  protected statusLabel(status: MemberStatus): string {
    return { active: 'Activo', pending: 'Invitación pendiente', inactive: 'Inactivo' }[status];
  }

  private hasPermission(permission: (typeof PERMISSIONS)[keyof typeof PERMISSIONS]): boolean {
    return Boolean(this.currentUser?.permissions?.includes(permission));
  }
}
