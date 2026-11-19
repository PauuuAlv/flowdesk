import { HttpErrorResponse } from '@angular/common/http';
import { Component, computed, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { Router } from '@angular/router';

import {
  CreateTenantResponse,
  SaaSPlanKey,
  SubscriptionStatus,
  TenantSaaS,
} from '../../../core/models/auth.models';
import { AuthService } from '../../../core/services/auth.service';
import { SessionService } from '../../../core/services/session.service';

@Component({
  selector: 'app-platform-admin-page',
  imports: [ReactiveFormsModule],
  templateUrl: './platform-admin-page.html',
  styleUrl: './platform-admin-page.scss',
})
export class PlatformAdminPage {
  private readonly formBuilder = inject(FormBuilder);
  private readonly authService = inject(AuthService);
  private readonly sessionService = inject(SessionService);
  private readonly router = inject(Router);

  protected readonly submitting = signal(false);
  protected readonly errorMessage = signal('');
  protected readonly createdTenant = signal<CreateTenantResponse | null>(null);
  protected readonly copied = signal(false);
  protected readonly tenants = signal<TenantSaaS[]>([]);
  protected readonly loadingTenants = signal(true);
  protected readonly updatingTenant = signal<string | null>(null);
  protected readonly search = signal('');
  protected readonly statusFilter = signal<SubscriptionStatus | 'all'>('all');
  protected readonly visibleTenants = computed(() => {
    const q = this.search().trim().toLowerCase();
    return this.tenants().filter(
      (t) =>
        (this.statusFilter() === 'all' || t.subscription_status === this.statusFilter()) &&
        (!q || `${t.name} ${t.slug} ${t.plan_name}`.toLowerCase().includes(q)),
    );
  });
  protected readonly metrics = computed(() => ({
    total: this.tenants().length,
    active: this.tenants().filter((t) => t.is_active).length,
    trial: this.tenants().filter((t) => t.subscription_status === 'trial').length,
    suspended: this.tenants().filter((t) => !t.is_active).length,
  }));
  protected readonly tenantForm = this.formBuilder.nonNullable.group({
    name: ['', [Validators.required, Validators.minLength(2)]],
    slug: ['', [Validators.required, Validators.pattern(/^[a-z0-9]+(?:-[a-z0-9]+)*$/)]],
    admin_full_name: ['', [Validators.required, Validators.minLength(3)]],
    admin_email: ['', [Validators.required, Validators.email]],
    plan_key: ['basic' as SaaSPlanKey, Validators.required],
  });

  constructor() {
    this.loadTenants();
  }

  protected generateSlug(): void {
    if (this.tenantForm.controls.slug.dirty) return;

    const slug = this.tenantForm.controls.name.value
      .normalize('NFD')
      .replace(/[\u0300-\u036f]/g, '')
      .toLowerCase()
      .trim()
      .replace(/[^a-z0-9]+/g, '-')
      .replace(/^-|-$/g, '');
    this.tenantForm.controls.slug.setValue(slug);
  }

  protected submit(): void {
    this.errorMessage.set('');
    this.createdTenant.set(null);
    this.copied.set(false);

    if (this.tenantForm.invalid) {
      this.tenantForm.markAllAsTouched();
      return;
    }

    this.submitting.set(true);
    this.authService.createTenant(this.tenantForm.getRawValue()).subscribe({
      next: (tenant) => {
        this.submitting.set(false);
        this.createdTenant.set(tenant);
        this.tenantForm.reset();
        this.tenantForm.controls.plan_key.setValue('basic');
        this.loadTenants();
      },
      error: (error: HttpErrorResponse) => {
        this.submitting.set(false);
        this.errorMessage.set(this.getErrorMessage(error));
      },
    });
  }

  protected async copyInvitation(): Promise<void> {
    const invitationLink = this.createdTenant()?.invitation_link;
    if (!invitationLink) return;

    try {
      await navigator.clipboard.writeText(invitationLink);
      this.copied.set(true);
    } catch {
      this.errorMessage.set('No fue posible copiar el enlace. Selecciónalo y cópialo manualmente.');
    }
  }

  protected logout(): void {
    this.sessionService.clearPlatformAdmin();
    void this.router.navigate(['/administracion-flowdesk/iniciar-sesion']);
  }

  protected setSearch(event: Event) {
    this.search.set((event.target as HTMLInputElement).value);
  }
  protected setStatusFilter(event: Event) {
    this.statusFilter.set((event.target as HTMLSelectElement).value as SubscriptionStatus | 'all');
  }
  protected updateTenant(
    tenant: TenantSaaS,
    plan_key: SaaSPlanKey,
    subscription_status: SubscriptionStatus,
  ): void {
    this.updatingTenant.set(tenant.id);
    this.errorMessage.set('');
    this.authService
      .updateTenantSubscription(tenant.id, {
        plan_key,
        subscription_status,
        subscription_renews_at: tenant.subscription_renews_at,
      })
      .subscribe({
        next: (updated) => {
          this.tenants.update((all) =>
            all.map((item) => (item.id === updated.id ? updated : item)),
          );
          this.updatingTenant.set(null);
        },
        error: () => {
          this.errorMessage.set('No fue posible actualizar la suscripción de la empresa.');
          this.updatingTenant.set(null);
        },
      });
  }
  protected changePlan(tenant: TenantSaaS, event: Event) {
    this.updateTenant(
      tenant,
      (event.target as HTMLSelectElement).value as SaaSPlanKey,
      tenant.subscription_status,
    );
  }
  protected changeStatus(tenant: TenantSaaS, event: Event) {
    this.updateTenant(
      tenant,
      tenant.plan_key,
      (event.target as HTMLSelectElement).value as SubscriptionStatus,
    );
  }

  protected percent(value: number, limit: number) {
    return Math.min(100, Math.round((value / Math.max(1, limit)) * 100));
  }
  protected statusLabel(status: SubscriptionStatus) {
    return { trial: 'Prueba', active: 'Activo', suspended: 'Suspendido', cancelled: 'Cancelado' }[
      status
    ];
  }
  protected date(value: string | null) {
    return value
      ? new Intl.DateTimeFormat('es-MX', { dateStyle: 'medium' }).format(new Date(value))
      : 'Sin renovación';
  }

  private loadTenants() {
    this.loadingTenants.set(true);
    this.authService.listTenants().subscribe({
      next: (items) => {
        this.tenants.set(items);
        this.loadingTenants.set(false);
      },
      error: () => {
        this.errorMessage.set('No fue posible consultar las empresas registradas.');
        this.loadingTenants.set(false);
      },
    });
  }

  private getErrorMessage(error: HttpErrorResponse): string {
    if (error.status === 0) return 'No fue posible conectar con el servidor.';
    if (error.status === 409) return 'Ese identificador de empresa ya está en uso. Elige otro.';
    if (error.status === 401) return 'La sesión del superadministrador expiró.';
    return 'No fue posible crear la empresa. Revisa los datos e intenta nuevamente.';
  }
}
