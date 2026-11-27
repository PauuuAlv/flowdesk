import { Component, DestroyRef, ElementRef, HostListener, inject, signal, viewChild } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { NavigationEnd, Router, RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';
import { catchError, filter, merge, of, Subject, switchMap, timer } from 'rxjs';

import { PERMISSIONS } from '../../core/models/permission.models';
import { FlowdeskNotification } from '../../core/models/notification.models';
import { NotificationService } from '../../core/services/notification.service';
import { PushNotificationService } from '../../core/services/push-notification.service';
import { SessionService } from '../../core/services/session.service';

@Component({
  selector: 'app-tenant-shell',
  imports: [RouterLink, RouterLinkActive, RouterOutlet],
  templateUrl: './tenant-shell.html',
  styleUrls: ['./tenant-shell.scss', './tenant-shell.mobile.scss', './tenant-shell.push.scss'],
})
export class TenantShell {
  private readonly sessionService = inject(SessionService);
  private readonly router = inject(Router);
  private readonly notificationsService = inject(NotificationService);
  private readonly destroyRef = inject(DestroyRef);
  protected readonly push = inject(PushNotificationService);
  private readonly refreshNotifications = new Subject<void>();
  protected readonly pushMessage = signal('');

  protected user = this.sessionService.getUser();
  protected readonly sidebarOpen = signal(false);
  protected readonly profileOpen = signal(false);
  protected readonly notificationsOpen = signal(false);
  protected readonly notificationsLoading = signal(false);
  protected readonly notifications = signal<FlowdeskNotification[]>([]);
  protected readonly unreadCount = signal(0);
  /** Submenú de "Productos y servicios" (productos, servicios, categorías, unidades y marcas). */
  protected readonly productsOpen = signal(false);
  protected readonly inProductsSection = signal(false);

  constructor() {
    // Al entrar a una página de la sección, su submenú se despliega solo.
    const syncSection = (url: string) => {
      const inside = /^\/panel\/(productos|servicios|configuracion\/(categorias|unidades|marcas))(\/|\?|#|$)/.test(url);
      this.inProductsSection.set(inside);
      if (inside) this.productsOpen.set(true);
    };
    syncSection(this.router.url);
    this.router.events.pipe(
      filter((event): event is NavigationEnd => event instanceof NavigationEnd),
      takeUntilDestroyed(this.destroyRef),
    ).subscribe((event) => syncSection(event.urlAfterRedirects));
    this.sessionService.userUpdates$.pipe(takeUntilDestroyed(this.destroyRef)).subscribe((user) => this.user = user);
    merge(timer(0, 60_000), this.refreshNotifications).pipe(
      switchMap(() => this.notificationsService.list().pipe(catchError(() => of(null)))),
      takeUntilDestroyed(this.destroyRef),
    ).subscribe((response) => {
      if (!response) return;
      this.notifications.set(response.items);
      this.unreadCount.set(response.unread_count);
      this.notificationsLoading.set(false);
    });
    this.listenToServiceWorker();
    void this.push.sync().catch(() => undefined);
  }

  /** Mensajes de `public/sw.js`: llegó un push o se hizo clic en una notificación. */
  private listenToServiceWorker(): void {
    if (!('serviceWorker' in navigator)) return;
    const onMessage = (event: MessageEvent) => {
      const data = event.data as { type?: string; url?: string } | null;
      if (data?.type === 'flowdesk:push') this.refreshNotifications.next();
      if (data?.type === 'flowdesk:navigate' && data.url?.startsWith('/')) void this.router.navigateByUrl(data.url);
    };
    navigator.serviceWorker.addEventListener('message', onMessage);
    this.destroyRef.onDestroy(() => navigator.serviceWorker.removeEventListener('message', onMessage));
  }

  protected async enablePush(): Promise<void> {
    this.pushMessage.set('');
    try {
      const state = await this.push.enable();
      if (state === 'subscribed') {
        await this.sendTestPush();
      } else if (state === 'denied') {
        this.pushMessage.set('El navegador bloqueó las notificaciones. Habilítalas en la configuración del sitio.');
      }
    } catch {
      this.pushMessage.set('No fue posible activar las notificaciones en este navegador.');
    }
  }

  protected async sendTestPush(): Promise<void> {
    try {
      const result = await this.push.sendTest();
      this.pushMessage.set(result.delivered > 0
        ? 'Aviso de prueba enviado. Si no lo ves, revisa que Windows/tu sistema permita notificaciones del navegador.'
        : 'El servicio push no aceptó el aviso. Desactiva y vuelve a activar las notificaciones.');
    } catch {
      this.pushMessage.set('No fue posible enviar el aviso de prueba.');
    }
  }

  protected async disablePush(): Promise<void> {
    this.pushMessage.set('');
    await this.push.disable().catch(() => undefined);
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

  protected toggleProducts(): void {
    this.productsOpen.update((open) => !open);
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

  protected async logout(): Promise<void> {
    // Este navegador deja de recibir avisos de la cuenta que cierra sesión.
    await this.push.disable().catch(() => undefined);
    this.sessionService.clear();
    void this.router.navigate(['/iniciar-sesion']);
  }

  private readonly notificationsArea = viewChild<ElementRef<HTMLElement>>('notificationsArea');

  /** Cierra el menú de notificaciones al hacer clic fuera de él (incluye el botón que lo abre). */
  @HostListener('document:click', ['$event'])
  protected closeNotificationsOnOutsideClick(event: MouseEvent): void {
    if (!this.notificationsOpen()) return;
    const area = this.notificationsArea()?.nativeElement;
    // composedPath conserva el recorrido aunque el elemento pulsado ya se haya
    // quitado del DOM (p. ej. "Marcar todas" desaparece al usarse).
    if (area && !event.composedPath().includes(area)) this.notificationsOpen.set(false);
  }

  @HostListener('document:keydown.escape')
  protected closeMenus(): void {
    this.sidebarOpen.set(false);
    this.profileOpen.set(false);
    this.notificationsOpen.set(false);
  }
}
