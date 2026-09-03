import { HttpErrorResponse } from '@angular/common/http';
import { Component, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { RouterLink } from '@angular/router';

import { AuthService } from '../../../core/services/auth.service';

@Component({
  selector: 'app-forgot-password-page',
  imports: [ReactiveFormsModule, RouterLink],
  templateUrl: './forgot-password-page.html',
  styleUrl: './forgot-password-page.scss'
})
export class ForgotPasswordPage {
  private readonly formBuilder = inject(FormBuilder);
  private readonly authService = inject(AuthService);
  protected readonly submitting = signal(false);
  protected readonly errorMessage = signal('');
  protected readonly successMessage = signal('');
  protected readonly forgotPasswordForm = this.formBuilder.nonNullable.group({
    email: ['', [Validators.required, Validators.email]]
  });

  protected submit(): void {
    this.errorMessage.set('');
    this.successMessage.set('');
    if (this.forgotPasswordForm.invalid) {
      this.forgotPasswordForm.markAllAsTouched();
      return;
    }

    this.submitting.set(true);
    this.authService.forgotPassword(this.forgotPasswordForm.getRawValue()).subscribe({
      next: (response) => {
        this.submitting.set(false);
        this.successMessage.set(response.message || 'Si el correo está registrado, recibirás instrucciones para continuar.');
      },
      error: (error: HttpErrorResponse) => {
        this.submitting.set(false);
        this.errorMessage.set(this.getErrorMessage(error));
      }
    });
  }

  private getErrorMessage(error: HttpErrorResponse): string {
    if (typeof error.error?.detail === 'string') return error.error.detail;
    if (error.status === 0) return 'No fue posible conectar con el servidor. Intenta nuevamente más tarde.';
    return 'No fue posible procesar la solicitud. Intenta nuevamente.';
  }
}
