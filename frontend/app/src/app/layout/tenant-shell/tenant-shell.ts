import { Component, HostListener, inject, signal } from '@angular/core';
import { Router, RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';

import { PERMISSIONS } from '../../core/models/permission.models';
import { SessionService } from '../../core/services/session.service';

@Component({
  selector: 'app-tenant-shell',
  imports: [RouterLink, RouterLinkActive, RouterOutlet],
  templateUrl: './tenant-shell.html',
  styleUrls: ['./tenant-shell.scss', './tenant-shell.mobile.scss']
})
export class TenantShell {
  private readonly sessionService = inject(SessionService);
  private readonly router = inject(Router);

  protected readonly user = this.sessionService.getUser();
  protected readonly sidebarOpen = signal(false);
  protected readonly profileOpen = signal(false);

  protected get companyName(): string {
    return this.user?.tenant_name?.trim() || 'Mi empresa';
  }

  protected get initials(): string {
    const source = this.user?.full_name?.trim() || this.user?.email || 'U';
    return source
      .split(/\s+/)
      .slice(0, 2)
      .map((part) => part.charAt(0).toUpperCase())
      .join('');
  }

  protected get canManageUsers(): boolean {
    const permissions = this.user?.permissions ?? [];
    return this.user?.role === 'admin' || permissions.includes(PERMISSIONS.usersInvite);
  }

  protected get canViewUsers(): boolean {
    const permissions = this.user?.permissions ?? [];
    return this.user?.role === 'admin' || permissions.includes(PERMISSIONS.usersView);
  }

  protected get canViewRoles(): boolean {
    const permissions = this.user?.permissions ?? [];
    return this.user?.role === 'admin' || permissions.includes(PERMISSIONS.rolesView);
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
    this.sessionService.clear();
    void this.router.navigate(['/iniciar-sesion']);
  }

  @HostListener('document:keydown.escape')
  protected closeMenus(): void {
    this.sidebarOpen.set(false);
    this.profileOpen.set(false);
  }
}
