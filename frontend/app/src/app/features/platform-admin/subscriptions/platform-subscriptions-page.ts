import { Component, inject, signal } from '@angular/core';

import { SaaSPlanKey, SubscriptionStatus, TenantSaaS } from '../../../core/models/auth.models';
import { AuthService } from '../../../core/services/auth.service';
import { PlanChangeRequest } from '../../../core/models/tenant-plan.models';
import { PlatformAccessService } from '../../../core/services/platform-access.service';

@Component({
  selector: 'app-platform-subscriptions-page',
  templateUrl: './platform-subscriptions-page.html',
  styleUrl: './platform-subscriptions-page.scss',
})
export class PlatformSubscriptionsPage {
  private readonly service = inject(AuthService);
  protected readonly access = inject(PlatformAccessService);
  protected readonly tenants = signal<TenantSaaS[]>([]);
  protected readonly loading = signal(true);
  protected readonly saving = signal<string | null>(null);
  protected readonly error = signal('');
  protected readonly success = signal('');
  protected readonly requests = signal<PlanChangeRequest[]>([]);
  protected readonly resolving = signal<string | null>(null);

  constructor() { this.load(); this.loadRequests(); }

  protected save(tenant: TenantSaaS, plan: string, status: string, renewal: string, email: string): void {
    if (!this.access.canManage()) return;
    this.error.set(''); this.success.set('');
    if (!email.trim() || !email.includes('@')) { this.error.set('Ingresa un correo de facturación válido.'); return; }
    this.saving.set(tenant.id);
    this.service.updateTenantSubscription(tenant.id, {
      plan_key: plan as SaaSPlanKey,
      subscription_status: status as SubscriptionStatus,
      subscription_renews_at: renewal ? `${renewal}T12:00:00Z` : null,
      billing_email: email.trim(),
    }).subscribe({
      next: (updated) => { this.tenants.update((all) => all.map((x) => x.id === updated.id ? updated : x)); this.saving.set(null); this.success.set(`Suscripción de ${updated.name} actualizada.`); },
      error: () => { this.error.set('No fue posible actualizar la suscripción.'); this.saving.set(null); },
    });
  }
  protected inputDate(value: string | null): string { return value?.slice(0, 10) ?? ''; }
  protected status(value: string): string { return {trial:'Prueba',active:'Activo',suspended:'Suspendido',cancelled:'Cancelado'}[value] ?? value; }
  protected planName(value: string): string { return {basic:'Básico',professional:'Profesional',enterprise:'Empresarial'}[value] ?? value; }
  protected resolve(request: PlanChangeRequest, status: 'approved'|'rejected'): void {
    if (!this.access.canManage()) return;
    this.resolving.set(request.id); this.error.set(''); this.success.set('');
    this.service.resolveSubscriptionRequest(request.id,status).subscribe({
      next:(updated)=>{this.requests.update((all)=>all.map((x)=>x.id===updated.id?updated:x));this.resolving.set(null);this.success.set(`Solicitud de ${updated.tenant_name} ${status==='approved'?'aprobada':'rechazada'}.`);this.load()},
      error:()=>{this.error.set('No fue posible resolver la solicitud.');this.resolving.set(null)},
    });
  }
  private load(): void { this.service.listTenants().subscribe({next:(x)=>{this.tenants.set(x);this.loading.set(false)},error:()=>{this.error.set('No fue posible consultar las suscripciones.');this.loading.set(false)}}); }
  private loadRequests(): void { this.service.listSubscriptionRequests().subscribe({next:(x)=>this.requests.set(x),error:()=>this.error.set('No fue posible consultar las solicitudes de cambio.')}); }
}
