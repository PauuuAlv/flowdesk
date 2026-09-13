import { HttpErrorResponse } from '@angular/common/http';
import { Component, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { Router } from '@angular/router';

import { CreateTenantResponse } from '../../../core/models/auth.models';
import { AuthService } from '../../../core/services/auth.service';
import { SessionService } from '../../../core/services/session.service';

@Component({
  selector: 'app-platform-admin-page',
  imports: [ReactiveFormsModule],
  templateUrl: './platform-admin-page.html',
  styleUrl: './platform-admin-page.scss'
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
  protected readonly tenantForm = this.formBuilder.nonNullable.group({
    name: ['', [Validators.required, Validators.minLength(2)]],
    slug: ['', [Validators.required, Validators.pattern(/^[a-z0-9]+(?:-[a-z0-9]+)*$/)]],
    admin_full_name: ['', [Validators.required, Validators.minLength(3)]],
    admin_email: ['', [Validators.required, Validators.email]]
  });

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
      },
      error: (error: HttpErrorResponse) => {
        this.submitting.set(false);
        this.errorMessage.set(this.getErrorMessage(error));
      }
    });
  }

  protected async copyInvitation(): Promise<void> {
    const invitationLink = this.createdTenant()?.dev_invitation_link;
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

  private getErrorMessage(error: HttpErrorResponse): string {
    if (error.status === 0) return 'No fue posible conectar con el servidor.';
    if (error.status === 409) return 'Ese identificador de empresa ya está en uso. Elige otro.';
    if (error.status === 401) return 'La sesión del superadministrador expiró.';
    return 'No fue posible crear la empresa. Revisa los datos e intenta nuevamente.';
  }
}
