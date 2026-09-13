import { HttpErrorResponse } from '@angular/common/http';
import { Component, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { switchMap, tap } from 'rxjs';

import { AuthService } from '../../../core/services/auth.service';
import { SessionService } from '../../../core/services/session.service';

@Component({
  selector: 'app-login-page',
  imports: [ReactiveFormsModule, RouterLink],
  templateUrl: './login-page.html',
  styleUrl: './login-page.scss'
})
export class LoginPage {
  private readonly formBuilder = inject(FormBuilder);
  private readonly authService = inject(AuthService);
  private readonly sessionService = inject(SessionService);
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);

  protected readonly submitting = signal(false);
  protected readonly errorMessage = signal(
    this.route.snapshot.queryParamMap.get('sesion') === 'expirada'
      ? 'Tu sesión expiró. Inicia sesión nuevamente.'
      : ''
  );
  protected readonly successMessage = signal('');
  protected readonly showPassword = signal(false);
  protected readonly loginForm = this.formBuilder.nonNullable.group({
    email: ['', [Validators.required, Validators.email]],
    password: ['', Validators.required]
  });

  protected togglePasswordVisibility(): void {
    this.showPassword.update((visible) => !visible);
  }

  protected submit(): void {
    this.errorMessage.set('');
    this.successMessage.set('');
    if (this.loginForm.invalid) {
      this.loginForm.markAllAsTouched();
      return;
    }

    this.submitting.set(true);
    this.authService
      .login(this.loginForm.getRawValue())
      .pipe(
        tap((tokens) => this.sessionService.saveTokens(tokens)),
        switchMap(() => this.authService.me())
      )
      .subscribe({
      next: (user) => {
        this.submitting.set(false);
        this.sessionService.saveUser(user);
        this.successMessage.set(
          `Sesión iniciada correctamente${user.full_name ? `, ${user.full_name}` : ''}.`
        );
        const returnUrl = this.route.snapshot.queryParamMap.get('returnUrl');
        void this.router.navigateByUrl(returnUrl?.startsWith('/') ? returnUrl : '/panel');
      },
      error: (error: HttpErrorResponse) => {
        this.submitting.set(false);
        this.errorMessage.set(this.getErrorMessage(error));
      }
    });
  }

  private getErrorMessage(error: HttpErrorResponse): string {
    if (error.status === 0) return 'No fue posible conectar con el servidor. Intenta nuevamente más tarde.';
    if (error.status === 401) return 'Correo o contraseña incorrectos. Verifica tus datos e intenta de nuevo.';
    return 'No fue posible iniciar sesión. Intenta nuevamente.';
  }
}
