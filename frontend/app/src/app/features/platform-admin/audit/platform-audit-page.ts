import { Component, computed, inject, signal } from '@angular/core';

import { PlatformAudit } from '../../../core/models/auth.models';
import { AuthService } from '../../../core/services/auth.service';

@Component({
  selector: 'app-platform-audit-page',
  templateUrl: './platform-audit-page.html',
  styleUrl: './platform-audit-page.scss',
})
export class PlatformAuditPage {
  private readonly service = inject(AuthService);
  protected readonly entries = signal<PlatformAudit[]>([]);
  protected readonly loading = signal(true);
  protected readonly error = signal('');
  protected readonly filter = signal('all');
  protected readonly visible = computed(() => this.entries().filter((x) => this.filter() === 'all' || x.action === this.filter()));

  constructor() { this.service.listPlatformAudit().subscribe({next:(x)=>{this.entries.set(x);this.loading.set(false)},error:()=>{this.error.set('No fue posible consultar la auditoría.');this.loading.set(false)}}); }
  protected setFilter(event: Event): void { this.filter.set((event.target as HTMLSelectElement).value); }
  protected date(value: string): string { return new Intl.DateTimeFormat('es-MX',{dateStyle:'medium',timeStyle:'short'}).format(new Date(value)); }
  protected action(value: string): string { return {'tenant.created':'Empresa creada','subscription.updated':'Suscripción actualizada','plan_change.requested':'Cambio de plan solicitado','plan_change.approved':'Cambio de plan aprobado','plan_change.rejected':'Cambio de plan rechazado'}[value] ?? value; }
}
