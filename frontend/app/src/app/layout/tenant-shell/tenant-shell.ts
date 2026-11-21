import { Component, DestroyRef, HostListener, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { Router, RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';
import { catchError, of, switchMap, timer } from 'rxjs';

import { PERMISSIONS } from '../../core/models/permission.models';
import { FlowdeskNotification } from '../../core/models/notification.models';
import { NotificationService } from '../../core/services/notification.service';
import { SessionService } from '../../core/services/session.service';

@Component({
  selector: 'app-tenant-shell',
  imports: [RouterLink, RouterLinkActive, RouterOutlet],
  templateUrl: './tenant-shell.html',
  styleUrls: ['./tenant-shell.scss', './tenant-shell.mobile.scss'],
})
export class TenantShell {
  private readonly sessionService = inject(SessionService);
  private readonly router = inject(Router);
  private readonly notificationsService = inject(NotificationService);
  private readonly destroyRef = inject(DestroyRef);

  protected user = this.sessionService.getUser();
  protected readonly sidebarOpen = signal(false);
  protected readonly profileOpen = signal(false);
  protected readonly notificationsOpen = signal(false);
  protected readonly notificationsLoading = signal(false);
  protected readonly notifications = signal<FlowdeskNotification[]>([]);
  protected readonly unreadCount = signal(0);

  constructor() {
    this.sessionService.userUpdates$.pipe(takeUntilDestroyed(this.destroyRef)).subscribe((user) => this.user = user);
    timer(0, 60_000).pipe(
      switchMap(() => this.notificationsService.list().pipe(catchError(() => of(null)))),
      takeUntilDestroyed(this.destroyRef),
    ).subscribe((response) => {
      if (!response) return;
      this.notifications.set(response.items);
      this.unreadCount.set(response.unread_count);
      this.notificationsLoading.set(false);
    });
  }

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
    return permissions.includes(PERMISSIONS.usersInvite);
  }

  protected get canViewUsers(): boolean {
    const permissions = this.user?.permissions ?? [];
    return permissions.includes(PERMISSIONS.usersView);
  }

  protected get canViewRoles(): boolean {
    const permissions = this.user?.permissions ?? [];
    return permissions.includes(PERMISSIONS.rolesView);
  }

  protected get canViewClients(): boolean {
    const permissions = this.user?.permissions ?? [];
    return permissions.includes(PERMISSIONS.clientsView);
  }
  protected get canViewOpportunities(): boolean {
    const p = this.user?.permissions ?? [];
    return p.includes(PERMISSIONS.opportunitiesView);
  }
  protected get canManageOpportunityStages(): boolean {
    const p = this.user?.permissions ?? [];
    return p.includes(PERMISSIONS.opportunitiesUpdate);
  }
  protected get canViewActivities(): boolean {
    const p = this.user?.permissions ?? [];
    return p.includes(PERMISSIONS.activitiesView);
  }
  protected get canViewQuotes(): boolean {
    const p = this.user?.permissions ?? [];
    return p.includes(PERMISSIONS.quotesView);
  }
  protected get canViewSettings(): boolean {
    const p = this.user?.permissions ?? [];
    return p.includes(PERMISSIONS.settingsView);
  }
  protected get canViewProducts(): boolean {
    const p = this.user?.permissions ?? [];
    return p.includes(PERMISSIONS.productsView);
  }
  protected get canManageProductCatalogs(): boolean {
    const p = this.user?.permissions ?? [];
    return p.includes(PERMISSIONS.productsUpdate);
  }

  protected toggleSidebar(): void {
    this.sidebarOpen.update((open) => !open);
    this.profileOpen.set(false);
    this.notificationsOpen.set(false);
  }

  protected closeSidebar(): void {
    this.sidebarOpen.set(false);
  }

  protected toggleProfile(): void {
    this.profileOpen.update((open) => !open);
    this.notificationsOpen.set(false);
  }

  protected closeProfile(): void {
    this.profileOpen.set(false);
  }

  protected toggleNotifications(): void {
    this.notificationsOpen.update((open) => !open);
    this.profileOpen.set(false);
  }

  protected openNotification(item: FlowdeskNotification): void {
    this.notificationsOpen.set(false);
    if (!item.is_read) {
      this.notificationsService.markRead(item.id).subscribe({
        next: () => {
          this.notifications.update((items) => items.map((current) => current.id === item.id ? { ...current, is_read: true } : current));
          this.unreadCount.update((count) => Math.max(0, count - 1));
        },
      });
    }
    void this.router.navigateByUrl(item.route);
  }

  protected markAllRead(): void {
    this.notificationsService.markAllRead().subscribe({
      next: () => {
        this.notifications.update((items) => items.map((item) => ({ ...item, is_read: true })));
        this.unreadCount.set(0);
      },
    });
  }

  protected notificationDate(value: string): string {
    return new Intl.DateTimeFormat('es-MX', { dateStyle: 'short', timeStyle: 'short' }).format(new Date(value));
  }

  protected logout(): void {
    this.sessionService.clear();
    void this.router.navigate(['/iniciar-sesion']);
  }

  @HostListener('document:keydown.escape')
  protected closeMenus(): void {
    this.sidebarOpen.set(false);
    this.profileOpen.set(false);
    this.notificationsOpen.set(false);
  }
}
