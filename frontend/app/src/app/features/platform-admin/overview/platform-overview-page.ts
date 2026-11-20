import { Component, computed, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';

import { SaaSPlanKey, TenantSaaS } from '../../../core/models/auth.models';
import { AuthService } from '../../../core/services/auth.service';
import { PlatformAccessService } from '../../../core/services/platform-access.service';

@Component({
  selector: 'app-platform-overview-page',
  imports: [RouterLink],
  templateUrl: './platform-overview-page.html',
  styleUrl: './platform-overview-page.scss',
})
export class PlatformOverviewPage {
  private readonly service = inject(AuthService);
  protected readonly access = inject(PlatformAccessService);
  protected readonly tenants = signal<TenantSaaS[]>([]);
  protected readonly loading = signal(true);
  protected readonly error = signal('');
  protected readonly metrics = computed(() => ({
    companies: this.tenants().length,
    active: this.tenants().filter((x) => x.subscription_status === 'active').length,
    trial: this.tenants().filter((x) => x.subscription_status === 'trial').length,
    suspended: this.tenants().filter((x) => !x.is_active).length,
    users: this.tenants().reduce((sum, x) => sum + x.usage.users, 0),
  }));
  protected readonly plans = computed(() => {
    const values: Array<{ key: SaaSPlanKey; name: string }> = [
      { key: 'basic', name: 'Básico' },
      { key: 'professional', name: 'Profesional' },
      { key: 'enterprise', name: 'Empresarial' },
    ];
    return values.map((plan) => ({
      ...plan,
      count: this.tenants().filter((x) => x.plan_key === plan.key).length,
    }));
  });
  protected readonly recent = computed(() => this.tenants().slice(0, 5));

  constructor() {
    this.load();
  }

  protected planWidth(count: number): number {
    return this.tenants().length ? Math.max(4, (count / this.tenants().length) * 100) : 0;
  }
  protected date(value: string): string {
    return new Intl.DateTimeFormat('es-MX', { dateStyle: 'medium' }).format(new Date(value));
  }
  protected status(value: string): string {
    return { trial: 'Prueba', active: 'Activo', suspended: 'Suspendido', cancelled: 'Cancelado' }[
      value
    ] ?? value;
  }
  protected load(): void {
    this.loading.set(true);
    this.error.set('');
    this.service.listTenants().subscribe({
      next: (items) => {
        this.tenants.set(items);
        this.loading.set(false);
      },
      error: () => {
        this.error.set('No fue posible cargar el resumen de la plataforma.');
        this.loading.set(false);
      },
    });
  }
}
