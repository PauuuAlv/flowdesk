import { HttpErrorResponse } from '@angular/common/http';
import { Component, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { switchMap, tap } from 'rxjs';

import { AuthService } from '../../../core/services/auth.service';
import { SessionService } from '../../../core/services/session.service';
import {
  getPasswordChecks,
  strongPasswordValidator
} from '../../../core/validators/password.validator';

@Component({
  selector: 'app-register-page',
  imports: [ReactiveFormsModule, RouterLink],
  templateUrl: './register-page.html',
  styleUrl: './register-page.scss'
})
export class RegisterPage {
  private readonly formBuilder = inject(FormBuilder);
  private readonly authService = inject(AuthService);
  private readonly sessionService = inject(SessionService);
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);

  protected readonly submitting = signal(false);
  protected readonly errorMessage = signal('');
  protected readonly successMessage = signal('');
  protected readonly showPassword = signal(false);
  protected readonly showPasswordConfirmation = signal(false);
  protected readonly token = this.route.snapshot.queryParamMap.get('token') ?? '';

  protected readonly registerForm = this.formBuilder.nonNullable.group({
    password: ['', [Validators.required, strongPasswordValidator]],
    password_confirmation: ['', Validators.required]
  });

  protected passwordsDoNotMatch(): boolean {
    const { password, password_confirmation } = this.registerForm.getRawValue();
    return password_confirmation.length > 0 && password !== password_confirmation;
  }

  protected passwordChecks() {
    return getPasswordChecks(this.registerForm.controls.password.value);
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
      this.errorMessage.set('El enlace de invitación no contiene un token válido.');
      return;
    }

    if (this.registerForm.invalid) {
      this.registerForm.markAllAsTouched();
      return;
    }

    const { password, password_confirmation } = this.registerForm.getRawValue();

    if (password !== password_confirmation) {
      this.errorMessage.set('Las contraseñas no coinciden.');
      return;
    }

    this.submitting.set(true);

    this.authService
      .register({ token: this.token, password })
      .pipe(
        tap((tokens) => this.sessionService.saveTokens(tokens)),
        switchMap(() => this.authService.me())
      )
      .subscribe({
      next: (user) => {
        this.submitting.set(false);
        this.sessionService.saveUser(user);
        this.successMessage.set('Invitación aceptada. Tu cuenta ya está activa.');
        this.registerForm.reset();
        void this.router.navigate(['/panel']);
      },
      error: (error: HttpErrorResponse) => {
        this.submitting.set(false);
        this.errorMessage.set(this.getErrorMessage(error));
      }
    });
  }

  private getErrorMessage(error: HttpErrorResponse): string {
    if (error.status === 0) {
      return 'No fue posible conectar con el servidor. Intenta nuevamente más tarde.';
    }

    if (error.status === 400) {
      return 'La invitación es inválida, venció o ya fue utilizada.';
    }

    return 'No fue posible aceptar la invitación. Verifica los datos e intenta nuevamente.';
  }
}
