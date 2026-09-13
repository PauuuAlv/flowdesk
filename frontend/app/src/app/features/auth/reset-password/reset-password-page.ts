import { HttpErrorResponse } from '@angular/common/http';
import { Component, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute, RouterLink } from '@angular/router';

import { AuthService } from '../../../core/services/auth.service';
import {
  getPasswordChecks,
  strongPasswordValidator
} from '../../../core/validators/password.validator';

@Component({
  selector: 'app-reset-password-page',
  imports: [ReactiveFormsModule, RouterLink],
  templateUrl: './reset-password-page.html',
  styleUrl: './reset-password-page.scss'
})
export class ResetPasswordPage {
  private readonly formBuilder = inject(FormBuilder);
  private readonly authService = inject(AuthService);
  private readonly route = inject(ActivatedRoute);
  protected readonly submitting = signal(false);
  protected readonly errorMessage = signal('');
  protected readonly successMessage = signal('');
  protected readonly showPassword = signal(false);
  protected readonly showPasswordConfirmation = signal(false);
  protected readonly token = this.route.snapshot.queryParamMap.get('token') ?? '';
  protected readonly resetPasswordForm = this.formBuilder.nonNullable.group({
    new_password: ['', [Validators.required, strongPasswordValidator]],
    password_confirmation: ['', Validators.required]
  });

  protected passwordsDoNotMatch(): boolean {
    const { new_password, password_confirmation } = this.resetPasswordForm.getRawValue();
    return password_confirmation.length > 0 && new_password !== password_confirmation;
  }

  protected passwordChecks() {
    return getPasswordChecks(this.resetPasswordForm.controls.new_password.value);
  }

  protected togglePasswordVisibility(): void {
    this.showPassword.update((visible) => !visible);
  }

  protected togglePasswordConfirmationVisibility(): void {
    this.showPasswordConfirmation.update((visible) => !visible);
  }

  protected submit(): void {
    this.errorMessage.set('');
    this.successMessage.set('');
    if (!this.token) {
      this.errorMessage.set('El enlace de recuperación no contiene un token válido.');
      return;
    }
    if (this.resetPasswordForm.invalid) {
      this.resetPasswordForm.markAllAsTouched();
      return;
    }

    const { new_password, password_confirmation } = this.resetPasswordForm.getRawValue();
    if (new_password !== password_confirmation) {
      this.errorMessage.set('Las contraseñas no coinciden.');
      return;
    }

    this.submitting.set(true);
    this.authService.resetPassword({ token: this.token, new_password }).subscribe({
      next: () => {
        this.submitting.set(false);
        this.successMessage.set('La contraseña fue actualizada correctamente.');
        this.resetPasswordForm.reset();
      },
      error: (error: HttpErrorResponse) => {
        this.submitting.set(false);
        this.errorMessage.set(this.getErrorMessage(error));
      }
    });
  }

  private getErrorMessage(error: HttpErrorResponse): string {
    if (error.status === 0) return 'No fue posible conectar con el servidor. Intenta nuevamente más tarde.';
    return 'El enlace es inválido o venció. Solicita uno nuevo e intenta nuevamente.';
  }
}
