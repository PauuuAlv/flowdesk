import { HttpErrorResponse } from '@angular/common/http';
import { Component, effect, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute } from '@angular/router';

import { AuthService } from '../../../core/services/auth.service';
import { PlatformAccessService } from '../../../core/services/platform-access.service';
import { getPasswordChecks, strongPasswordValidator } from '../../../core/validators/password.validator';

/** Mi perfil del equipo de plataforma: nombre y cambio de contraseña. */
@Component({
  selector: 'app-platform-profile-page',
  imports: [ReactiveFormsModule],
  templateUrl: './platform-profile-page.html',
  styleUrl: './platform-profile-page.scss',
})
export class PlatformProfilePage {
  private readonly fb = inject(FormBuilder);
  private readonly auth = inject(AuthService);
  protected readonly access = inject(PlatformAccessService);

  protected readonly savingProfile = signal(false);
  protected readonly profileMessage = signal<{ type: 'success' | 'error'; text: string } | null>(null);
  protected readonly savingPassword = signal(false);
  protected readonly passwordMessage = signal<{ type: 'success' | 'error'; text: string } | null>(null);
  protected readonly showPasswords = signal(false);

  protected readonly profileForm = this.fb.nonNullable.group({
    full_name: ['', [Validators.required, Validators.minLength(2), Validators.maxLength(120)]],
  });
  protected readonly passwordForm = this.fb.nonNullable.group({
    current_password: ['', Validators.required],
    new_password: ['', [Validators.required, strongPasswordValidator]],
    confirmation: ['', Validators.required],
  });

  constructor() {
    // "Cambiar contraseña" del menú lleva a #seguridad: se desplaza hasta esa sección.
    inject(ActivatedRoute)
      .fragment.pipe(takeUntilDestroyed())
      .subscribe((fragment) => {
        setTimeout(() => {
          if (!fragment) {
            window.scrollTo({ top: 0 });
            return;
          }
          const section = document.getElementById(fragment);
          section?.scrollIntoView({ block: 'start' });
          section?.querySelector<HTMLInputElement>('input')?.focus({ preventScroll: true });
        });
      });
    // Rellena el nombre cuando llega la identidad de la sesión.
    effect(() => {
      const member = this.access.member();
      if (member && !this.profileForm.dirty) {
        this.profileForm.reset({ full_name: member.full_name ?? '' });
      }
    });
  }

  protected checks() {
    return getPasswordChecks(this.passwordForm.controls.new_password.value);
  }

  protected mismatch(): boolean {
    const value = this.passwordForm.getRawValue();
    return !!value.confirmation && value.new_password !== value.confirmation;
  }

  protected saveProfile(): void {
    this.profileMessage.set(null);
    if (this.profileForm.invalid) {
      this.profileForm.markAllAsTouched();
      return;
    }
    this.savingProfile.set(true);
    this.auth.updatePlatformProfile(this.profileForm.getRawValue().full_name.trim()).subscribe({
      next: (member) => {
        this.access.member.set(member);
        this.profileForm.reset({ full_name: member.full_name ?? '' });
        this.savingProfile.set(false);
        this.profileMessage.set({ type: 'success', text: 'Tu nombre se actualizó correctamente.' });
      },
      error: () => {
        this.savingProfile.set(false);
        this.profileMessage.set({ type: 'error', text: 'No fue posible actualizar tu nombre. Intenta nuevamente.' });
      },
    });
  }

  protected changePassword(): void {
    this.passwordMessage.set(null);
    if (this.passwordForm.invalid || this.mismatch()) {
      this.passwordForm.markAllAsTouched();
      this.passwordMessage.set({
        type: 'error',
        text: this.mismatch() ? 'Las contraseñas no coinciden.' : 'Revisa los requisitos de la nueva contraseña.',
      });
      return;
    }
    const value = this.passwordForm.getRawValue();
    this.savingPassword.set(true);
    this.auth.changePlatformPassword(value.current_password, value.new_password).subscribe({
      next: () => {
        this.savingPassword.set(false);
        this.passwordForm.reset();
        this.passwordMessage.set({ type: 'success', text: 'Tu contraseña se cambió correctamente.' });
      },
      error: (error: HttpErrorResponse) => {
        this.savingPassword.set(false);
        const detail = String(error.error?.detail ?? '');
        this.passwordMessage.set({
          type: 'error',
          text: detail.includes('incorrect')
            ? 'La contraseña actual no es correcta.'
            : detail.includes('different')
              ? 'La nueva contraseña debe ser distinta de la actual.'
              : error.status === 422
                ? 'La nueva contraseña no cumple los requisitos.'
                : 'No fue posible cambiar la contraseña. Intenta nuevamente.',
        });
      },
    });
  }
}
