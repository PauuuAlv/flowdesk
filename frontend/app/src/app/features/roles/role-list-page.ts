import { Component, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';

import { TenantRole } from '../../core/models/access-control.models';
import { AccessControlPreviewService } from '../../core/services/access-control-preview.service';

@Component({
  selector: 'app-role-list-page',
  imports: [RouterLink],
  templateUrl: './role-list-page.html',
  styleUrl: './role-list-page.scss'
})
export class RoleListPage {
  private readonly accessControl = inject(AccessControlPreviewService);

  protected readonly roles = signal<TenantRole[]>([]);
  protected readonly loading = signal(true);
  protected readonly errorMessage = signal('');
  protected readonly successMessage = signal('');
  protected readonly roleToDelete = signal<TenantRole | null>(null);
  protected readonly deleting = signal(false);

  constructor() {
    this.loadRoles();
  }

  protected loadRoles(): void {
    this.loading.set(true);
    this.errorMessage.set('');
    this.accessControl.listRoles().subscribe({
      next: (roles) => {
        this.roles.set(roles);
        this.loading.set(false);
      },
      error: () => {
        this.loading.set(false);
        this.errorMessage.set('No fue posible consultar los roles. Intenta nuevamente.');
      }
    });
  }

  protected requestDelete(role: TenantRole): void {
    this.successMessage.set('');
    this.roleToDelete.set(role);
  }

  protected cancelDelete(): void {
    this.roleToDelete.set(null);
  }

  protected confirmDelete(): void {
    const role = this.roleToDelete();
    if (!role) return;
    this.deleting.set(true);
    this.accessControl.deleteRole(role.id).subscribe({
      next: () => {
        this.deleting.set(false);
        this.roleToDelete.set(null);
        this.roles.update((roles) => roles.filter((item) => item.id !== role.id));
        this.successMessage.set(`El rol ${role.name} se eliminó correctamente.`);
      },
      error: () => {
        this.deleting.set(false);
        this.roleToDelete.set(null);
        this.errorMessage.set('No se puede eliminar un rol protegido o asignado a usuarios.');
      }
    });
  }
}
