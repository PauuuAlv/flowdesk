import { HttpErrorResponse } from '@angular/common/http';
import { Component, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute, RouterLink } from '@angular/router';

import { AuthService } from '../../../core/services/auth.service';

@Component({
  selector: 'app-forgot-password-page',
  imports: [ReactiveFormsModule, RouterLink],
  templateUrl: './forgot-password-page.html',
  styleUrl: './forgot-password-page.scss',
})
export class ForgotPasswordPage {
  private readonly formBuilder = inject(FormBuilder);
  private readonly authService = inject(AuthService);
  /** true en /administracion-flowdesk/olvide-mi-contrasena (cuentas de plataforma). */
  protected readonly isPlatform = inject(ActivatedRoute).snapshot.data['audience'] === 'platform';
  protected readonly loginLink = this.isPlatform ? '/administracion-flowdesk/iniciar-sesion' : '/iniciar-sesion';
  protected readonly submitting = signal(false);
  protected readonly errorMessage = signal('');
  protected readonly successMessage = signal('');
  protected readonly forgotPasswordForm = this.formBuilder.nonNullable.group({
    email: ['', [Validators.required, Validators.email]],
  });

  protected submit(): void {
    this.errorMessage.set('');
    this.successMessage.set('');
    if (this.forgotPasswordForm.invalid) {
      this.forgotPasswordForm.markAllAsTouched();
      return;
    }

    this.submitting.set(true);
    const request = this.forgotPasswordForm.getRawValue();
    const call = this.isPlatform
      ? this.authService.platformForgotPassword(request)
      : this.authService.forgotPassword(request);
    call.subscribe({
      next: () => {
        this.submitting.set(false);
        this.successMessage.set(
          'Si el correo está registrado, recibirás instrucciones para continuar.',
        );
      },
      error: (error: HttpErrorResponse) => {
        this.submitting.set(false);
        this.errorMessage.set(this.getErrorMessage(error));
      },
    });
  }

  private getErrorMessage(error: HttpErrorResponse): string {
    if (error.status === 0)
      return 'No fue posible conectar con el servidor. Intenta nuevamente más tarde.';
    return 'No fue posible procesar la solicitud. Intenta nuevamente.';
  }
}
