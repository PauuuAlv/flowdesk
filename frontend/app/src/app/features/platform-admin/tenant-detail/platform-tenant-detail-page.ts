import { HttpErrorResponse } from '@angular/common/http';
import { Component, computed, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';

import { SaaSPlanKey, SubscriptionStatus, TenantSaaS } from '../../../core/models/auth.models';
import { AuthService } from '../../../core/services/auth.service';
import { PlatformAccessService } from '../../../core/services/platform-access.service';
import { TenantAdminService } from '../../../core/services/tenant-admin.service';

type TenantDialog = 'edit' | 'toggle' | 'delete' | null;

@Component({
  selector: 'app-platform-tenant-detail-page',
  imports: [ReactiveFormsModule, RouterLink],
  templateUrl: './platform-tenant-detail-page.html',
  styleUrl: './platform-tenant-detail-page.scss',
})
export class PlatformTenantDetailPage {
  private readonly service = inject(AuthService);
  private readonly tenantAdmin = inject(TenantAdminService);
  private readonly router = inject(Router);
  private readonly formBuilder = inject(FormBuilder);
  protected readonly access = inject(PlatformAccessService);
  private readonly id = inject(ActivatedRoute).snapshot.paramMap.get('tenantId');
  protected readonly tenant = signal<TenantSaaS | null>(null);
  protected readonly loading = signal(true);
  protected readonly saving = signal(false);
  protected readonly error = signal('');
  protected readonly success = signal('');

  // Gestión de la empresa (editar, inhabilitar, eliminar): solo superadministrador.
  protected readonly dialog = signal<TenantDialog>(null);
  protected readonly dialogError = signal('');
  protected readonly processing = signal(false);
  protected readonly deleteConfirmation = signal('');
  protected readonly editForm = this.formBuilder.nonNullable.group({
    name: ['', [Validators.required, Validators.minLength(2)]],
    slug: ['', [Validators.required, Validators.pattern(/^[a-z0-9]+(?:-[a-z0-9]+)*$/)]],
  });
  protected readonly modules = computed(() => {
    const usage = this.tenant()?.usage;
    if (!usage) return [];
    return [
      { name: 'Usuarios', count: usage.users, enabled: true },
      { name: 'Clientes', count: usage.clients, enabled: true },
      { name: 'Oportunidades', count: usage.opportunities, enabled: true },
      { name: 'Actividades', count: usage.activities, enabled: true },
      { name: 'Cotizaciones', count: usage.quotes, enabled: true },
      { name: 'Productos y servicios', count: usage.products, enabled: true },
      { name: 'Roles y permisos', count: null, enabled: true },
    ];
  });

  constructor() {
    this.load();
  }

  protected update(plan: SaaSPlanKey, status: SubscriptionStatus): void {
    if (!this.access.canManage()) return;
    const tenant = this.tenant();
    if (!tenant) return;
    this.saving.set(true);
    this.error.set('');
    this.service
      .updateTenantSubscription(tenant.id, {
        plan_key: plan,
        subscription_status: status,
        subscription_renews_at: tenant.subscription_renews_at,
      })
      .subscribe({
        next: (updated) => {
          this.tenant.set(updated);
          this.saving.set(false);
        },
        error: () => {
          this.error.set('No fue posible actualizar la suscripción.');
          this.saving.set(false);
        },
      });
  }
  protected changePlan(event: Event): void {
    const tenant = this.tenant();
    if (tenant)
      this.update((event.target as HTMLSelectElement).value as SaaSPlanKey, tenant.subscription_status);
  }
  protected changeStatus(event: Event): void {
    const tenant = this.tenant();
    if (tenant)
      this.update(tenant.plan_key, (event.target as HTMLSelectElement).value as SubscriptionStatus);
  }
  protected percent(value: number, max: number): number {
    return Math.min(100, Math.round((value / Math.max(1, max)) * 100));
  }
  protected date(value: string | null): string {
    return value
      ? new Intl.DateTimeFormat('es-MX', { dateStyle: 'long' }).format(new Date(value))
      : 'Sin fecha definida';
  }
  protected status(value: string): string {
    return { trial: 'Prueba', active: 'Activo', suspended: 'Suspendido', cancelled: 'Cancelado' }[
      value
    ] ?? value;
  }
  // --- Gestión de la empresa ---

  protected openDialog(kind: Exclude<TenantDialog, null>): void {
    const tenant = this.tenant();
    if (!tenant || !this.access.canManage()) return;
    this.success.set('');
    this.dialogError.set('');
    this.deleteConfirmation.set('');
    if (kind === 'edit') this.editForm.reset({ name: tenant.name, slug: tenant.slug });
    this.dialog.set(kind);
  }

  protected closeDialog(): void {
    this.dialog.set(null);
    this.processing.set(false);
    this.dialogError.set('');
  }

  protected saveEdit(): void {
    const tenant = this.tenant();
    if (!tenant) return;
    if (this.editForm.invalid) {
      this.editForm.markAllAsTouched();
      return;
    }
    this.processing.set(true);
    this.tenantAdmin.update(tenant.id, this.editForm.getRawValue()).subscribe({
      next: (updated) => {
        this.tenant.set(updated);
        this.closeDialog();
        this.success.set(`Se actualizaron los datos de ${updated.name}.`);
      },
      error: (error: HttpErrorResponse) => {
        this.processing.set(false);
        this.dialogError.set(
          error.status === 409
            ? 'Ese identificador ya lo usa otra empresa. Elige otro.'
            : 'No fue posible guardar los cambios. Revisa los datos e intenta nuevamente.',
        );
      },
    });
  }

  protected confirmToggle(): void {
    const tenant = this.tenant();
    if (!tenant) return;
    this.processing.set(true);
    this.tenantAdmin.updateStatus(tenant.id, !tenant.is_active).subscribe({
      next: (updated) => {
        this.tenant.set(updated);
        this.closeDialog();
        this.success.set(`${updated.name} quedó ${updated.is_active ? 'habilitada' : 'inhabilitada'}.`);
      },
      error: () => {
        this.processing.set(false);
        this.dialogError.set('No fue posible cambiar el estado de la empresa.');
      },
    });
  }

  protected updateDeleteConfirmation(event: Event): void {
    this.deleteConfirmation.set((event.target as HTMLInputElement).value);
  }

  protected canConfirmDelete(tenant: TenantSaaS): boolean {
    return this.deleteConfirmation().trim().toLowerCase() === tenant.slug;
  }

  protected confirmDelete(): void {
    const tenant = this.tenant();
    if (!tenant || !this.canConfirmDelete(tenant)) return;
    this.processing.set(true);
    this.tenantAdmin.delete(tenant.id, tenant.slug).subscribe({
      next: () => {
        this.closeDialog();
        void this.router.navigate(['/administracion-flowdesk/empresas']);
      },
      error: () => {
        this.processing.set(false);
        this.dialogError.set('No fue posible eliminar la empresa. Intenta nuevamente.');
      },
    });
  }

  private load(): void {
    if (!this.id) {
      this.error.set('No encontramos la empresa solicitada.');
      this.loading.set(false);
      return;
    }
    this.tenantAdmin.get(this.id).subscribe({
      next: (tenant) => {
        this.tenant.set(tenant);
        this.loading.set(false);
      },
      error: (error: HttpErrorResponse) => {
        this.error.set(
          error.status === 404
            ? 'No encontramos la empresa solicitada.'
            : 'No fue posible consultar la empresa.',
        );
        this.loading.set(false);
      },
    });
  }
}
