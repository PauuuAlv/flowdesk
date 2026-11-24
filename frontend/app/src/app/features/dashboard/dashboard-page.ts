import { Component, computed, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { DashboardPipelineStage, DashboardSummary } from '../../core/models/dashboard.models';
import { PERMISSIONS } from '../../core/models/permission.models';
import { DashboardService } from '../../core/services/dashboard.service';
import { SessionService } from '../../core/services/session.service';
import { formatMoney, formatTotals, MoneyTotal } from '../../core/models/currency.models';

@Component({
  selector: 'app-dashboard-page',
  imports: [RouterLink],
  templateUrl: './dashboard-page.html',
  styleUrl: './dashboard-page.scss',
})
export class DashboardPage {
  private readonly service = inject(DashboardService);
  private readonly session = inject(SessionService);
  protected readonly user = this.session.getUser();
  protected readonly summary = signal<DashboardSummary | null>(null);
  protected readonly loading = signal(true);
  protected readonly error = signal('');
  /** Las etapas se agrupan por pipeline solo cuando la empresa usa más de uno. */
  protected readonly hasSeveralPipelines = computed(
    () => new Set(this.summary()?.pipeline.map((x) => x.pipeline_id) ?? []).size > 1,
  );
  protected readonly maxPipelineValue = computed(() =>
    Math.max(...(this.summary()?.pipeline.map((x) => this.primaryAmount(x)) ?? []), 1),
  );
  protected readonly canCreateClient = this.has(PERMISSIONS.clientsCreate);
  protected readonly canCreateOpportunity = this.has(PERMISSIONS.opportunitiesCreate);
  protected readonly canCreateActivity = this.has(PERMISSIONS.activitiesCreate);
  protected readonly canCreateQuote = this.has(PERMISSIONS.quotesCreate);
  constructor() {
    this.load();
  }
  protected load() {
    this.loading.set(true);
    this.error.set('');
    this.service.getSummary().subscribe({
      next: (x) => {
        this.summary.set(x);
        this.loading.set(false);
      },
      error: () => {
        this.error.set('No fue posible cargar el resumen de tu empresa.');
        this.loading.set(false);
      },
    });
  }
  protected money(value: number, currency: string) {
    return formatMoney(value, currency);
  }
  /** Totales por moneda: la de la empresa primero ("$100.00 MXN · $5.00 USD"). */
  protected totals(values: MoneyTotal[]) {
    return formatTotals(values);
  }
  protected date(value: string) {
    return new Intl.DateTimeFormat('es-MX', { dateStyle: 'medium', timeStyle: 'short' }).format(
      new Date(value),
    );
  }
  /** Importe en la moneda de la empresa (el primero de la lista); define el largo de la barra. */
  private primaryAmount(item: DashboardPipelineStage): number {
    return Number(item.value[0]?.amount ?? 0);
  }
  protected pipelineWidth(item: DashboardPipelineStage) {
    return Math.max((this.primaryAmount(item) / this.maxPipelineValue()) * 100, item.count ? 7 : 0);
  }
  protected activityType(type: string) {
    return { call: 'Llamada', email: 'Correo', meeting: 'Reunión', task: 'Tarea' }[type] ?? type;
  }
  protected quoteStatus(status: string) {
    return (
      {
        draft: 'Borrador',
        sent: 'Enviada',
        accepted: 'Aceptada',
        rejected: 'Rechazada',
        expired: 'Vencida',
      }[status] ?? status
    );
  }
  private has(permission: (typeof PERMISSIONS)[keyof typeof PERMISSIONS]) {
    return Boolean(this.user?.permissions?.includes(permission));
  }
}
