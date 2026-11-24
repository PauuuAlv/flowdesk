import { HttpErrorResponse } from '@angular/common/http';
import { Component, HostListener, computed, effect, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute, RouterLink } from '@angular/router';

import {
  CreateTenantResponse,
  SaaSPlanKey,
  SubscriptionStatus,
  TenantSaaS,
} from '../../../core/models/auth.models';
import { AuthService } from '../../../core/services/auth.service';
import { PlatformAccessService } from '../../../core/services/platform-access.service';
import { Combobox, ComboOption } from '../../../shared/ui/combobox/combobox';
import { PLAN_OPTIONS, SUBSCRIPTION_STATUS_OPTIONS } from '../platform-options';

@Component({
  selector: 'app-platform-admin-page',
  imports: [ReactiveFormsModule, RouterLink, Combobox],
  templateUrl: './platform-admin-page.html',
  styleUrl: './platform-admin-page.scss',
})
export class PlatformAdminPage {
  protected readonly planOptions: ComboOption[] = [
    { value: 'basic', label: 'Básico', hint: '5 usuarios' },
    { value: 'professional', label: 'Profesional', hint: '20 usuarios' },
    { value: 'enterprise', label: 'Empresarial', hint: '500 usuarios' },
  ];
  // Combos de cada tarjeta de empresa.
  protected readonly planChoices = PLAN_OPTIONS;
  protected readonly statusChoices = SUBSCRIPTION_STATUS_OPTIONS;
  private readonly formBuilder = inject(FormBuilder);
  private readonly authService = inject(AuthService);
  protected readonly access = inject(PlatformAccessService);

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
  protected readonly tenantForm = this.formBuilder.nonNullable.group({
    name: ['', [Validators.required, Validators.minLength(2)]],
    slug: ['', [Validators.required, Validators.pattern(/^[a-z0-9]+(?:-[a-z0-9]+)*$/)]],
    admin_full_name: ['', [Validators.required, Validators.minLength(3)]],
    admin_email: ['', [Validators.required, Validators.email]],
    plan_key: ['basic' as SaaSPlanKey, Validators.required],
  });

  protected readonly createModalOpen = signal(false);
  protected readonly createError = signal('');
  private createModalOpenedFromRoute = false;

  constructor() {
    this.loadTenants();

    const route = inject(ActivatedRoute);
    const shouldOpenCreateModal =
      route.snapshot.data['focusCreateTenant'] === true ||
      route.snapshot.fragment === 'seccion-crear-empresa';
    if (shouldOpenCreateModal) {
      effect(() => {
        if (this.access.canManage() && !this.createModalOpenedFromRoute) {
          this.createModalOpenedFromRoute = true;
          this.openCreateModal();
        }
      });
    }
  }

  protected openCreateModal(): void {
    if (!this.access.canManage()) return;
    this.resetCreateForm();
    this.createModalOpen.set(true);
  }

  protected closeCreateModal(): void {
    if (this.submitting()) return;
    this.createModalOpen.set(false);
    this.resetCreateForm();
  }

  protected startAnotherTenant(): void {
    this.resetCreateForm();
  }

  protected onBackdropClick(event: MouseEvent): void {
    if (event.target === event.currentTarget) this.closeCreateModal();
  }

  @HostListener('document:keydown.escape')
  protected onEscape(): void {
    if (this.createModalOpen()) this.closeCreateModal();
  }

  private resetCreateForm(): void {
    this.createError.set('');
    this.createdTenant.set(null);
    this.copied.set(false);
    this.tenantForm.reset();
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
    if (!this.access.canManage()) return;
    this.createError.set('');
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
        this.createError.set(this.getErrorMessage(error));
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
      this.createError.set('No fue posible copiar el enlace. Selecciónalo y cópialo manualmente.');
    }
  }

  protected setSearch(event: Event) {
    this.search.set((event.target as HTMLInputElement).value);
  }
  protected setStatusFilter(value: string) {
    this.statusFilter.set(value as SubscriptionStatus | 'all');
  }
  protected updateTenant(
    tenant: TenantSaaS,
    plan_key: SaaSPlanKey,
    subscription_status: SubscriptionStatus,
    revert?: () => void,
  ): void {
    if (!this.access.canManage()) return;
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
          revert?.(); // el combo vuelve a mostrar el valor que se conserva
        },
      });
  }
  protected changePlan(tenant: TenantSaaS, plan: string, combo: Combobox) {
    this.updateTenant(tenant, plan as SaaSPlanKey, tenant.subscription_status, () =>
      combo.writeValue(tenant.plan_key),
    );
  }
  protected changeStatus(tenant: TenantSaaS, status: string, combo: Combobox) {
    this.updateTenant(tenant, tenant.plan_key, status as SubscriptionStatus, () =>
      combo.writeValue(tenant.subscription_status),
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
