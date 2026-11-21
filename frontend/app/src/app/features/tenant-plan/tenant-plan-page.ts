import { Component, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';

import { SaaSPlanKey } from '../../core/models/auth.models';
import { TenantPlan } from '../../core/models/tenant-plan.models';
import { SessionService } from '../../core/services/session.service';
import { TenantPlanService } from '../../core/services/tenant-plan.service';

@Component({
  selector: 'app-tenant-plan-page',
  imports: [ReactiveFormsModule],
  templateUrl: './tenant-plan-page.html',
  styleUrl: './tenant-plan-page.scss',
})
export class TenantPlanPage {
  private readonly service = inject(TenantPlanService);
  private readonly session = inject(SessionService);
  private readonly fb = inject(FormBuilder);
  protected readonly data = signal<TenantPlan | null>(null);
  protected readonly loading = signal(true);
  protected readonly sending = signal(false);
  protected readonly error = signal('');
  protected readonly success = signal('');
  protected readonly canRequest = this.session.getUser()?.role === 'admin';
  protected readonly form = this.fb.nonNullable.group({
    requested_plan_key: ['' as SaaSPlanKey, Validators.required],
    note: ['', Validators.maxLength(500)],
  });

  constructor() { this.load(); }
  protected percent(value: number, limit: number): number { return Math.min(100, Math.round(value / Math.max(1, limit) * 100)); }
  protected number(value: number): string { return new Intl.NumberFormat('es-MX').format(value); }
  protected date(value: string | null): string { return value ? new Intl.DateTimeFormat('es-MX',{dateStyle:'long'}).format(new Date(value)) : 'Sin fecha definida'; }
  protected status(value: string): string { return {trial:'Prueba',active:'Activo',suspended:'Suspendido',cancelled:'Cancelado'}[value] ?? value; }
  protected planName(key: string): string { return this.data()?.plans.find((x) => x.key === key)?.name ?? key; }
  protected selectPlan(key: SaaSPlanKey): void { this.form.controls.requested_plan_key.setValue(key); document.getElementById('solicitar-plan')?.scrollIntoView({behavior:'smooth'}); }
  protected submit(): void {
    const data = this.data(); if (!data || this.form.invalid || data.current_request) return;
    this.sending.set(true); this.error.set(''); this.success.set('');
    const value = this.form.getRawValue();
    this.service.requestChange(value.requested_plan_key, value.note.trim() || null).subscribe({
      next: (request) => { this.data.update((current) => current ? {...current,current_request:request} : current); this.success.set('La solicitud fue enviada al administrador de Flowdesk.'); this.sending.set(false); },
      error: (response) => { this.error.set(response.status===409?'Ya existe una solicitud pendiente o seleccionaste tu plan actual.':'No fue posible enviar la solicitud.'); this.sending.set(false); },
    });
  }
  private load(): void { this.service.get().subscribe({next:(x)=>{this.data.set(x);this.loading.set(false)},error:()=>{this.error.set('No fue posible consultar el plan de tu empresa.');this.loading.set(false)}}); }
}
