import { HttpErrorResponse } from '@angular/common/http';
import { Component, computed, ElementRef, inject, signal, viewChild } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { switchMap, tap } from 'rxjs';

import { AuthService } from '../../../core/services/auth.service';
import { KnownAccount, KnownAccountsService } from '../../../core/services/known-accounts.service';
import { SessionService } from '../../../core/services/session.service';

@Component({
  selector: 'app-login-page',
  imports: [ReactiveFormsModule, RouterLink],
  templateUrl: './login-page.html',
  styleUrl: './login-page.scss',
})
export class LoginPage {
  private readonly formBuilder = inject(FormBuilder);
  private readonly authService = inject(AuthService);
  private readonly sessionService = inject(SessionService);
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly knownAccounts = inject(KnownAccountsService);
  private readonly passwordInput = viewChild<ElementRef<HTMLInputElement>>('passwordInput');

  // --- Selector de cuentas de este navegador (como el de Google) ---
  protected readonly accounts = this.knownAccounts.accounts;
  /** Cuenta elegida en el selector; el correo queda fijo y solo se pide la contraseña. */
  protected readonly selected = signal<KnownAccount | null>(null);
  /** "Usar otra cuenta": formulario completo aunque haya cuentas recordadas. */
  protected readonly otherAccount = signal(false);
  /** Modo "Quitar una cuenta". */
  protected readonly removing = signal(false);
  protected readonly showChooser = computed(
    () => this.accounts().length > 0 && !this.selected() && !this.otherAccount(),
  );

  protected readonly submitting = signal(false);
  protected readonly errorMessage = signal(
    this.route.snapshot.queryParamMap.get('sesion') === 'expirada'
      ? 'Tu sesión expiró. Inicia sesión nuevamente.'
      : '',
  );
  protected readonly successMessage = signal('');
  protected readonly showPassword = signal(false);
  protected readonly loginForm = this.formBuilder.nonNullable.group({
    email: ['', [Validators.required, Validators.email]],
    password: ['', Validators.required],
  });

  protected chooseAccount(account: KnownAccount): void {
    if (this.removing()) {
      this.removeAccount(account);
      return;
    }
    this.selected.set(account);
    this.errorMessage.set('');
    this.loginForm.reset({ email: account.email, password: '' });
    setTimeout(() => this.passwordInput()?.nativeElement.focus());
  }

  protected useOtherAccount(): void {
    this.selected.set(null);
    this.removing.set(false);
    this.otherAccount.set(true);
    this.errorMessage.set('');
    this.loginForm.reset({ email: '', password: '' });
  }

  /** Regresa a la lista de cuentas de este navegador. */
  protected backToChooser(): void {
    this.selected.set(null);
    this.otherAccount.set(false);
    this.errorMessage.set('');
    this.loginForm.reset({ email: '', password: '' });
  }

  protected toggleRemoving(): void {
    this.removing.update((value) => !value);
  }

  protected removeAccount(account: KnownAccount): void {
    const name = account.full_name || account.email;
    if (!confirm(`¿Quitar a ${name} de este navegador? Podrás volver a iniciar sesión con esa cuenta cuando quieras.`)) return;
    this.knownAccounts.forget(account.id);
    if (!this.accounts().length) this.removing.set(false);
  }

  protected initials(account: KnownAccount): string {
    const source = account.full_name || account.email;
    const parts = source.split(/[\s@._-]+/).filter(Boolean);
    return ((parts[0]?.[0] ?? '') + (parts[1]?.[0] ?? '')).toUpperCase() || '?';
  }

  /** Color estable por cuenta para el avatar. */
  protected avatarColor(account: KnownAccount): string {
    const palette = ['#275d78', '#8a5b00', '#2f7d5b', '#7a4fa0', '#b54035', '#3b6fb6', '#a5481f'];
    let hash = 0;
    for (const char of account.id) hash = (hash * 31 + char.charCodeAt(0)) >>> 0;
    return palette[hash % palette.length];
  }

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
        switchMap(() => this.authService.me()),
      )
      .subscribe({
        next: (user) => {
          this.submitting.set(false);
          this.sessionService.saveUser(user);
          this.successMessage.set(
            `Sesión iniciada correctamente${user.full_name ? `, ${user.full_name}` : ''}.`,
          );
          const returnUrl = this.route.snapshot.queryParamMap.get('returnUrl');
          void this.router.navigateByUrl(returnUrl?.startsWith('/') ? returnUrl : '/panel');
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
    if (error.status === 403 && error.error?.detail === 'Company disabled')
      return 'Tu empresa está inhabilitada. Contacta al administrador de Flowdesk.';
    if (error.status === 401)
      return 'Correo o contraseña incorrectos. Verifica tus datos e intenta de nuevo.';
    return 'No fue posible iniciar sesión. Intenta nuevamente.';
  }
}
