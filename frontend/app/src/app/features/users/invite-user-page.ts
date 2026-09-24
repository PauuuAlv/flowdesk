import { HttpErrorResponse } from '@angular/common/http';
import { Component, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';

import { InviteUserResponse } from '../../core/models/auth.models';
import { AuthService } from '../../core/services/auth.service';

@Component({
  selector: 'app-invite-user-page',
  imports: [ReactiveFormsModule],
  templateUrl: './invite-user-page.html',
  styleUrl: './invite-user-page.scss'
})
export class InviteUserPage {
  private readonly formBuilder = inject(FormBuilder);
  private readonly authService = inject(AuthService);

  protected readonly submitting = signal(false);
  protected readonly errorMessage = signal('');
  protected readonly invitedUser = signal<InviteUserResponse | null>(null);
  protected readonly copied = signal(false);
  protected readonly inviteForm = this.formBuilder.nonNullable.group({
    full_name: ['', [Validators.required, Validators.minLength(3)]],
    email: ['', [Validators.required, Validators.email]]
  });

  protected submit(): void {
    this.errorMessage.set('');
    this.invitedUser.set(null);
    this.copied.set(false);

    if (this.inviteForm.invalid) {
      this.inviteForm.markAllAsTouched();
      return;
    }

    this.submitting.set(true);
    this.authService
      .inviteUser({ ...this.inviteForm.getRawValue(), role: 'member' })
      .subscribe({
      next: (user) => {
        this.submitting.set(false);
        this.invitedUser.set(user);
        this.inviteForm.reset();
      },
      error: (error: HttpErrorResponse) => {
        this.submitting.set(false);
        this.errorMessage.set(this.getErrorMessage(error));
      }
    });
  }

  protected async copyInvitation(): Promise<void> {
    const invitationLink = this.invitedUser()?.dev_invitation_link;
    if (!invitationLink) return;

    try {
      await navigator.clipboard.writeText(invitationLink);
      this.copied.set(true);
    } catch {
      this.errorMessage.set('No fue posible copiar el enlace. Selecciónalo y cópialo manualmente.');
    }
  }

  private getErrorMessage(error: HttpErrorResponse): string {
    if (error.status === 0) return 'No fue posible conectar con el servidor.';
    if (error.status === 409) return 'Ya existe un usuario con ese correo dentro de tu empresa.';
    if (error.status === 403) return 'Tu cuenta no tiene permiso para invitar usuarios.';
    if (error.status === 401) return 'Tu sesión expiró. Inicia sesión nuevamente.';
    return 'No fue posible generar la invitación. Revisa los datos e intenta nuevamente.';
  }
}
