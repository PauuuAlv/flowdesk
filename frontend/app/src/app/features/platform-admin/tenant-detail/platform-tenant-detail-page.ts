import { Component, computed, inject, signal } from '@angular/core';
import { ActivatedRoute, RouterLink } from '@angular/router';

import { SaaSPlanKey, SubscriptionStatus, TenantSaaS } from '../../../core/models/auth.models';
import { AuthService } from '../../../core/services/auth.service';
import { PlatformAccessService } from '../../../core/services/platform-access.service';

@Component({
  selector: 'app-platform-tenant-detail-page',
  imports: [RouterLink],
  templateUrl: './platform-tenant-detail-page.html',
  styleUrl: './platform-tenant-detail-page.scss',
})
export class PlatformTenantDetailPage {
  private readonly service = inject(AuthService);
  protected readonly access = inject(PlatformAccessService);
  private readonly id = inject(ActivatedRoute).snapshot.paramMap.get('tenantId');
  protected readonly tenant = signal<TenantSaaS | null>(null);
  protected readonly loading = signal(true);
  protected readonly saving = signal(false);
  protected readonly error = signal('');
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
  private load(): void {
    this.service.listTenants().subscribe({
      next: (items) => {
        this.tenant.set(items.find((x) => x.id === this.id) ?? null);
        if (!this.tenant()) this.error.set('No encontramos la empresa solicitada.');
        this.loading.set(false);
      },
      error: () => {
        this.error.set('No fue posible consultar la empresa.');
        this.loading.set(false);
      },
    });
  }
}
