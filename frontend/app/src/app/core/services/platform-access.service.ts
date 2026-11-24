import { computed, inject, Injectable, signal } from '@angular/core';

import { PlatformAdminMe } from '../models/auth.models';
import { PLATFORM_PERMISSIONS, PlatformPermissionCode } from '../models/platform-access.models';
import { AuthService } from './auth.service';

/**
 * Identidad y permisos de la cuenta de plataforma con sesión iniciada.
 * La interfaz solo oculta o deshabilita acciones: el backend valida cada permiso.
 */
@Injectable({ providedIn: 'root' })
export class PlatformAccessService {
  private readonly auth = inject(AuthService);
  readonly member = signal<PlatformAdminMe | null>(null);
  readonly loaded = signal(false);
  readonly permissions = computed(() => new Set(this.member()?.permissions ?? []));

  /** Compatibilidad: acciones de gestión de empresas (plan, suscripción, estado). */
  readonly canManage = computed(() => this.can(PLATFORM_PERMISSIONS.tenantsUpdate));

  can(permission: PlatformPermissionCode): boolean {
    return this.permissions().has(permission);
  }

  load(): void {
    this.auth.platformAdminMe().subscribe({
      next: (member) => { this.member.set(member); this.loaded.set(true); },
      error: () => this.loaded.set(true),
    });
  }

  clear(): void { this.member.set(null); this.loaded.set(false); }
}
