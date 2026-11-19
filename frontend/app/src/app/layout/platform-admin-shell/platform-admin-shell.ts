import { Component, HostListener, inject, signal } from '@angular/core';
import { Router, RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';

import { SessionService } from '../../core/services/session.service';

@Component({
  selector: 'app-platform-admin-shell',
  imports: [RouterLink, RouterLinkActive, RouterOutlet],
  templateUrl: './platform-admin-shell.html',
  // Reutiliza los estilos del shell de empresa para mantener el mismo aspecto.
  styleUrls: ['../tenant-shell/tenant-shell.scss', '../tenant-shell/tenant-shell.mobile.scss']
})
export class PlatformAdminShell {
  private readonly sessionService = inject(SessionService);
  private readonly router = inject(Router);

  protected readonly email = this.sessionService.getPlatformAdminEmail();
  protected readonly sidebarOpen = signal(false);
  protected readonly profileOpen = signal(false);

  protected get initials(): string {
    return (this.email?.charAt(0) || 'S').toUpperCase();
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

  protected logout(): void {
    this.sessionService.clearPlatformAdmin();
    void this.router.navigate(['/administracion-flowdesk/iniciar-sesion']);
  }

  @HostListener('document:keydown.escape')
  protected closeMenus(): void {
    this.sidebarOpen.set(false);
    this.profileOpen.set(false);
  }
}
