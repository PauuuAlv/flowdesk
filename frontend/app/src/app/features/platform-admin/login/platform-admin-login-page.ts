import { HttpErrorResponse } from '@angular/common/http';
import { Component, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';

import { AuthService } from '../../../core/services/auth.service';
import { SessionService } from '../../../core/services/session.service';

@Component({
  selector: 'app-platform-admin-login-page',
  imports: [ReactiveFormsModule, RouterLink],
  templateUrl: './platform-admin-login-page.html',
  styleUrl: './platform-admin-login-page.scss'
})
export class PlatformAdminLoginPage {
  private readonly formBuilder = inject(FormBuilder);
  private readonly authService = inject(AuthService);
  private readonly sessionService = inject(SessionService);
  private readonly router = inject(Router);

  protected readonly submitting = signal(false);
  protected readonly errorMessage = signal('');
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
    if (this.loginForm.invalid) {
      this.loginForm.markAllAsTouched();
      return;
    }

    this.submitting.set(true);
    this.authService.platformAdminLogin(this.loginForm.getRawValue()).subscribe({
      next: (tokens) => {
        this.sessionService.savePlatformAdminToken(tokens);
        this.submitting.set(false);
        void this.router.navigate(['/administracion-flowdesk']);
      },
      error: (error: HttpErrorResponse) => {
        this.submitting.set(false);
        this.errorMessage.set(
          error.status === 0
            ? 'No fue posible conectar con el servidor.'
            : 'Correo o contraseña incorrectos.'
        );
      }
    });
  }
}
