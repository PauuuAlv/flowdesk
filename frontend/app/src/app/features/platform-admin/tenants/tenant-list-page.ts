import { DatePipe } from '@angular/common';
import { HttpErrorResponse } from '@angular/common/http';
import { Component, computed, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { RouterLink } from '@angular/router';

import { SaaSPlanKey, SubscriptionStatus } from '../../../core/models/auth.models';
import { TenantSummary } from '../../../core/models/tenant.models';
import { TenantAdminService } from '../../../core/services/tenant-admin.service';

type StatusFilter = SubscriptionStatus | 'all';

@Component({
  selector: 'app-tenant-list-page',
  imports: [DatePipe, ReactiveFormsModule, RouterLink],
  templateUrl: './tenant-list-page.html',
  styleUrl: './tenant-list-page.scss'
})
export class TenantListPage {
  private readonly tenantService = inject(TenantAdminService);
  private readonly formBuilder = inject(FormBuilder);

  protected readonly tenants = signal<TenantSummary[]>([]);
  protected readonly loading = signal(true);
  protected readonly processing = signal(false);
  protected readonly errorMessage = signal('');
  protected readonly successMessage = signal('');
  protected readonly dialogError = signal('');
  protected readonly search = signal('');
  protected readonly statusFilter = signal<StatusFilter>('all');

  protected readonly updatingTenant = signal<string | null>(null);

  protected readonly tenantToEdit = signal<TenantSummary | null>(null);
  protected readonly tenantToToggle = signal<TenantSummary | null>(null);
  protected readonly tenantToDelete = signal<TenantSummary | null>(null);
  protected readonly deleteConfirmation = signal('');

  protected readonly editForm = this.formBuilder.nonNullable.group({
    name: ['', [Validators.required, Validators.minLength(2)]],
    slug: ['', [Validators.required, Validators.pattern(/^[a-z0-9]+(?:-[a-z0-9]+)*$/)]]
  });

  protected readonly filteredTenants = computed(() => {
    const term = this.search().trim().toLowerCase();
    const status = this.statusFilter();
    return this.tenants().filter((tenant) => {
      const content = `${tenant.name} ${tenant.slug} ${tenant.admin_email ?? ''} ${tenant.plan_name}`.toLowerCase();
      const matchesStatus = status === 'all' || tenant.subscription_status === status;
      return (!term || content.includes(term)) && matchesStatus;
    });
  });

  protected readonly metrics = computed(() => {
    const tenants = this.tenants();
    return {
      total: tenants.length,
      active: tenants.filter((t) => t.is_active).length,
      trial: tenants.filter((t) => t.subscription_status === 'trial').length,
      blocked: tenants.filter((t) => !t.is_active).length
    };
  });

  constructor() {
    this.load();
  }

  protected load(): void {
    this.loading.set(true);
    this.errorMessage.set('');
    this.tenantService.list().subscribe({
      next: (tenants) => {
        this.tenants.set(tenants);
        this.loading.set(false);
      },
      error: () => {
        this.loading.set(false);
        this.errorMessage.set('No fue posible consultar las empresas. Intenta nuevamente.');
      }
    });
  }

  protected updateSearch(event: Event): void {
    this.search.set((event.target as HTMLInputElement).value);
  }

  protected updateStatusFilter(event: Event): void {
    this.statusFilter.set((event.target as HTMLSelectElement).value as StatusFilter);
  }

  // --- Editar ---

  protected openEdit(tenant: TenantSummary): void {
    this.clearMessages();
    this.editForm.reset({ name: tenant.name, slug: tenant.slug });
    this.tenantToEdit.set(tenant);
  }

  protected saveEdit(): void {
    const tenant = this.tenantToEdit();
    if (!tenant) return;
    if (this.editForm.invalid) {
      this.editForm.markAllAsTouched();
      return;
    }

    this.processing.set(true);
    this.dialogError.set('');
    this.tenantService.update(tenant.id, this.editForm.getRawValue()).subscribe({
      next: (updated) => {
        this.replace(updated);
        this.closeDialogs();
        this.successMessage.set(`Se actualizaron los datos de ${updated.name}.`);
      },
      error: (error: HttpErrorResponse) => {
        this.processing.set(false);
        this.dialogError.set(
          error.status === 409
            ? 'Ese identificador ya lo usa otra empresa. Elige otro.'
            : 'No fue posible guardar los cambios. Revisa los datos e intenta nuevamente.'
        );
      }
    });
  }

  // --- Inhabilitar / reactivar ---

  protected openToggle(tenant: TenantSummary): void {
    this.clearMessages();
    this.tenantToToggle.set(tenant);
  }

  protected confirmToggle(): void {
    const tenant = this.tenantToToggle();
    if (!tenant) return;

    this.processing.set(true);
    this.dialogError.set('');
    this.tenantService.updateStatus(tenant.id, !tenant.is_active).subscribe({
      next: (updated) => {
        this.replace(updated);
        this.closeDialogs();
        this.successMessage.set(
          `${updated.name} quedó ${updated.is_active ? 'habilitada' : 'inhabilitada'}.`
        );
      },
      error: () => {
        this.processing.set(false);
        this.dialogError.set('No fue posible cambiar el estado de la empresa.');
      }
    });
  }

  // --- Plan y suscripción ---

  protected changePlan(tenant: TenantSummary, event: Event): void {
    this.updateSubscription(tenant, (event.target as HTMLSelectElement).value as SaaSPlanKey, tenant.subscription_status);
  }

  protected changeSubscriptionStatus(tenant: TenantSummary, event: Event): void {
    this.updateSubscription(tenant, tenant.plan_key, (event.target as HTMLSelectElement).value as SubscriptionStatus);
  }

  protected percent(value: number, limit: number): number {
    return Math.min(100, Math.round((value / Math.max(1, limit)) * 100));
  }

  protected statusLabel(status: SubscriptionStatus): string {
    return { trial: 'Prueba', active: 'Activo', suspended: 'Suspendido', cancelled: 'Cancelado' }[status];
  }

  private updateSubscription(tenant: TenantSummary, plan_key: SaaSPlanKey, subscription_status: SubscriptionStatus): void {
    this.clearMessages();
    this.updatingTenant.set(tenant.id);
    this.tenantService
      .updateSubscription(tenant.id, { plan_key, subscription_status, subscription_renews_at: tenant.subscription_renews_at })
      .subscribe({
        next: (updated) => {
          this.replace(updated);
          this.updatingTenant.set(null);
          this.successMessage.set(`Se actualizó la suscripción de ${updated.name}: plan ${updated.plan_name}, ${this.statusLabel(updated.subscription_status).toLowerCase()}.`);
        },
        error: () => {
          this.updatingTenant.set(null);
          this.errorMessage.set('No fue posible actualizar la suscripción de la empresa.');
          this.load();
        }
      });
  }

  // --- Eliminar ---

  protected openDelete(tenant: TenantSummary): void {
    this.clearMessages();
    this.deleteConfirmation.set('');
    this.tenantToDelete.set(tenant);
  }

  protected updateDeleteConfirmation(event: Event): void {
    this.deleteConfirmation.set((event.target as HTMLInputElement).value);
  }

  protected canConfirmDelete(tenant: TenantSummary): boolean {
    return this.deleteConfirmation().trim().toLowerCase() === tenant.slug;
  }

  protected confirmDelete(): void {
    const tenant = this.tenantToDelete();
    if (!tenant || !this.canConfirmDelete(tenant)) return;

    this.processing.set(true);
    this.dialogError.set('');
    this.tenantService.delete(tenant.id, tenant.slug).subscribe({
      next: () => {
        this.tenants.update((tenants) => tenants.filter((item) => item.id !== tenant.id));
        this.closeDialogs();
        this.successMessage.set(`${tenant.name} y todos sus datos fueron eliminados.`);
      },
      error: () => {
        this.processing.set(false);
        this.dialogError.set('No fue posible eliminar la empresa. Intenta nuevamente.');
      }
    });
  }

  protected closeDialogs(): void {
    this.processing.set(false);
    this.dialogError.set('');
    this.tenantToEdit.set(null);
    this.tenantToToggle.set(null);
    this.tenantToDelete.set(null);
  }

  protected initials(tenant: TenantSummary): string {
    return tenant.name
      .split(/\s+/)
      .slice(0, 2)
      .map((part) => part.charAt(0).toUpperCase())
      .join('');
  }

  private replace(updated: TenantSummary): void {
    this.tenants.update((tenants) =>
      tenants.map((item) => (item.id === updated.id ? updated : item))
    );
  }

  private clearMessages(): void {
    this.successMessage.set('');
    this.errorMessage.set('');
  }
}
