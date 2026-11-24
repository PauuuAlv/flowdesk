import { Component, DestroyRef, HostListener, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { NavigationEnd, Router, RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';
import { filter } from 'rxjs';

import { SessionService } from '../../../core/services/session.service';
import { PlatformAccessService } from '../../../core/services/platform-access.service';
import { PLATFORM_PERMISSIONS } from '../../../core/models/platform-access.models';

@Component({
  selector: 'app-platform-admin-shell',
  imports: [RouterLink, RouterLinkActive, RouterOutlet],
  templateUrl: './platform-admin-shell.html',
  styleUrl: './platform-admin-shell.scss',
})
export class PlatformAdminShell {
  private readonly session = inject(SessionService);
  private readonly router = inject(Router);
  protected readonly access = inject(PlatformAccessService);
  protected readonly P = PLATFORM_PERMISSIONS;
  /** Panel lateral abierto (solo aplica en pantallas angostas). */
  protected readonly sidebarOpen = signal(false);
  /** Menú desplegable del perfil (botón .profile-trigger). */
  protected readonly profileOpen = signal(false);

  constructor() {
    this.access.load();
    // Al navegar se cierran el panel lateral (móvil) y el menú de perfil.
    this.router.events
      .pipe(filter((event) => event instanceof NavigationEnd), takeUntilDestroyed(inject(DestroyRef)))
      .subscribe(() => this.closeMenus());
  }

  protected get initials(): string {
    const member = this.access.member();
    const source = member?.full_name?.trim() || member?.email || 'A';
    return source
      .split(/\s+/)
      .slice(0, 2)
      .map((part) => part.charAt(0).toUpperCase())
      .join('');
  }

  protected toggleSidebar(): void {
    this.sidebarOpen.update((open) => !open);
    this.profileOpen.set(false);
  }

  protected closeSidebar(): void {
    this.sidebarOpen.set(false);
  }

  protected toggleProfile(): void {
    this.profileOpen.update((open) => !open);
  }

  protected closeProfile(): void {
    this.profileOpen.set(false);
  }

  @HostListener('document:keydown.escape')
  protected closeMenus(): void {
    this.sidebarOpen.set(false);
    this.profileOpen.set(false);
  }

  protected logout(): void {
    this.session.clearPlatformAdmin();
    this.access.clear();
    void this.router.navigate(['/administracion-flowdesk/iniciar-sesion']);
  }
}
