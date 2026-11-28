import { HttpClient } from '@angular/common/http';
import { inject, Injectable, signal } from '@angular/core';
import { firstValueFrom } from 'rxjs';

export type PushState = 'unsupported' | 'disabled' | 'denied' | 'available' | 'subscribed';

interface PushConfig {
  enabled: boolean;
  public_key: string | null;
}

export interface PushTestResult {
  delivered: number;
  removed: number;
  failed: number;
}

const SERVICE_WORKER_URL = '/sw.js';
/** El usuario ya respondió la pregunta inicial en este navegador. */
export const PUSH_ASKED_KEY = 'flowdesk.push.asked.';
/** El usuario eligió no recibir avisos en este navegador (botón Desactivar o "Ahora no"). */
export const PUSH_OPTOUT_KEY = 'flowdesk.push.optout.';

/**
 * Web Push estándar (W3C Push API + VAPID).
 *
 * Registra `public/sw.js`, suscribe el navegador con la clave pública VAPID del
 * backend y envía la suscripción a `/api/notifications/push/subscriptions`.
 *
 * Persistencia por navegador y usuario:
 * - Cerrar sesión solo desvincula el navegador en el servidor; la suscripción del
 *   navegador se conserva y al volver a entrar se reasocia sin preguntar.
 * - La primera vez que un usuario entra en este navegador se le pregunta
 *   (`askNeeded`). Su respuesta se recuerda en localStorage.
 * - Si el permiso del sitio se retira, los avisos se desactivan (también en el servidor).
 */
@Injectable({ providedIn: 'root' })
export class PushNotificationService {
  private readonly http = inject(HttpClient);
  private config: PushConfig | null = null;
  private userId: string | null = null;
  private permissionWatch: PermissionStatus | null = null;

  readonly state = signal<PushState>('unsupported');
  readonly busy = signal(false);
  /** Primera sesión de este usuario en este navegador: hay que preguntarle. */
  readonly askNeeded = signal(false);

  get isSupported(): boolean {
    return typeof window !== 'undefined'
      && window.isSecureContext
      && 'serviceWorker' in navigator
      && 'PushManager' in window
      && 'Notification' in window;
  }

  /**
   * Revisa el estado al iniciar sesión (o al cambiar el permiso del sitio) y, si el
   * usuario ya aceptó en este navegador y el permiso sigue concedido, deja la
   * suscripción activa y asociada a él.
   */
  async sync(userId?: string | null): Promise<void> {
    if (userId !== undefined) this.userId = userId;
    this.askNeeded.set(false);
    if (!this.isSupported) {
      this.state.set('unsupported');
      return;
    }
    void this.watchPermission();
    try {
      this.config = await firstValueFrom(this.http.get<PushConfig>('/api/notifications/push/config'));
    } catch {
      this.state.set('disabled');
      return;
    }
    if (!this.config.enabled || !this.config.public_key) {
      this.state.set('disabled');
      return;
    }
    const registration = await this.registration();
    let subscription = await registration.pushManager.getSubscription();
    if (subscription && !this.sameKey(subscription, this.config.public_key)) {
      // Las claves VAPID cambiaron en el servidor: la suscripción anterior ya no sirve.
      await subscription.unsubscribe();
      subscription = null;
    }
    const permission = Notification.permission;
    if (permission !== 'granted') {
      // El permiso se retiró (o nunca se dio): nada debe seguir enviándose aquí.
      if (subscription) {
        await this.release(subscription);
        await subscription.unsubscribe().catch(() => undefined);
      }
      this.state.set(permission === 'denied' ? 'denied' : 'available');
      this.askNeeded.set(permission === 'default' && !this.flag(PUSH_ASKED_KEY));
      return;
    }
    if (!this.flag(PUSH_ASKED_KEY) || this.flag(PUSH_OPTOUT_KEY)) {
      // Primera vez de este usuario aquí, o eligió no recibir avisos: el navegador
      // puede estar suscrito por otra cuenta; se desvincula para no recibir sus avisos.
      if (subscription) await this.release(subscription);
      this.state.set('available');
      this.askNeeded.set(!this.flag(PUSH_ASKED_KEY));
      return;
    }
    subscription ??= await this.subscribe(registration, this.config.public_key);
    await this.save(subscription);
    this.state.set('subscribed');
  }

  /** "Ahora no" en la pregunta inicial: se recuerda; puede activarlas desde el menú. */
  declinePrompt(): void {
    this.setFlag(PUSH_ASKED_KEY, true);
    this.setFlag(PUSH_OPTOUT_KEY, true);
    this.askNeeded.set(false);
  }

  /**
   * Al cerrar sesión: el servidor deja de enviar a este navegador los avisos de
   * esta cuenta, pero la suscripción del navegador se conserva para la próxima sesión.
   */
  async detach(): Promise<void> {
    if (!this.isSupported) return;
    const registration = await navigator.serviceWorker.getRegistration(SERVICE_WORKER_URL);
    const subscription = await registration?.pushManager.getSubscription();
    if (subscription) await this.release(subscription);
    this.userId = null;
    this.askNeeded.set(false);
    this.state.set('unsupported');
  }

  /** Pide permiso (debe llamarse desde un clic del usuario) y suscribe el navegador. */
  async enable(): Promise<PushState> {
    if (!this.config?.public_key) await this.sync();
    if (!this.config?.public_key || this.state() === 'unsupported' || this.state() === 'disabled') {
      return this.state();
    }
    this.busy.set(true);
    try {
      const permission = await Notification.requestPermission();
      this.setFlag(PUSH_ASKED_KEY, true);
      this.askNeeded.set(false);
      if (permission !== 'granted') {
        this.state.set(permission === 'denied' ? 'denied' : 'available');
        return this.state();
      }
      this.setFlag(PUSH_OPTOUT_KEY, false);
      const registration = await this.registration();
      const subscription = (await registration.pushManager.getSubscription())
        ?? (await this.subscribe(registration, this.config.public_key));
      await this.save(subscription);
      this.state.set('subscribed');
      return 'subscribed';
    } finally {
      this.busy.set(false);
    }
  }

  /** Botón Desactivar: el usuario ya no quiere avisos en este navegador (se recuerda). */
  async disable(): Promise<void> {
    if (!this.isSupported) return;
    this.busy.set(true);
    try {
      this.setFlag(PUSH_ASKED_KEY, true);
      this.setFlag(PUSH_OPTOUT_KEY, true);
      const registration = await navigator.serviceWorker.getRegistration(SERVICE_WORKER_URL);
      const subscription = await registration?.pushManager.getSubscription();
      if (subscription) await this.release(subscription);
      if (this.state() === 'subscribed') this.state.set('available');
    } finally {
      this.busy.set(false);
    }
  }

  sendTest(): Promise<PushTestResult> {
    return firstValueFrom(this.http.post<PushTestResult>('/api/notifications/push/test', {}));
  }

  private async registration(): Promise<ServiceWorkerRegistration> {
    await navigator.serviceWorker.register(SERVICE_WORKER_URL, { scope: '/' });
    return navigator.serviceWorker.ready;
  }

  private subscribe(registration: ServiceWorkerRegistration, publicKey: string): Promise<PushSubscription> {
    return registration.pushManager.subscribe({
      userVisibleOnly: true,
      applicationServerKey: this.decodeKey(publicKey),
    });
  }

  /** Desvincula el navegador en el servidor (sin tocar la suscripción del navegador). */
  private release(subscription: PushSubscription): Promise<void> {
    return firstValueFrom(this.http.delete<void>('/api/notifications/push/subscriptions', {
      body: { endpoint: subscription.endpoint },
    })).catch(() => undefined);
  }

  /** Si el usuario quita o concede el permiso del sitio con la app abierta, se sincroniza. */
  private async watchPermission(): Promise<void> {
    if (this.permissionWatch || !navigator.permissions?.query) return;
    try {
      this.permissionWatch = await navigator.permissions.query({ name: 'notifications' });
      this.permissionWatch.onchange = () => {
        if (this.userId) void this.sync().catch(() => undefined);
      };
    } catch {
      /* el navegador no permite observar el permiso: se revisa al iniciar sesión */
    }
  }

  private flag(prefix: string): boolean {
    if (!this.userId) return false;
    try {
      return localStorage.getItem(prefix + this.userId) === '1';
    } catch {
      return false;
    }
  }

  private setFlag(prefix: string, value: boolean): void {
    if (!this.userId) return;
    try {
      if (value) localStorage.setItem(prefix + this.userId, '1');
      else localStorage.removeItem(prefix + this.userId);
    } catch {
      /* almacenamiento no disponible: se volverá a preguntar */
    }
  }

  private save(subscription: PushSubscription): Promise<void> {
    return firstValueFrom(this.http.post<void>('/api/notifications/push/subscriptions', subscription.toJSON()));
  }

  private sameKey(subscription: PushSubscription, publicKey: string): boolean {
    const current = subscription.options.applicationServerKey;
    if (!current) return true;
    const expected = this.decodeKey(publicKey);
    const actual = new Uint8Array(current);
    return actual.length === expected.length && actual.every((value, index) => value === expected[index]);
  }

  private decodeKey(base64Url: string): Uint8Array<ArrayBuffer> {
    const padded = (base64Url + '='.repeat((4 - (base64Url.length % 4)) % 4)).replace(/-/g, '+').replace(/_/g, '/');
    const raw = atob(padded);
    const output = new Uint8Array(new ArrayBuffer(raw.length));
    for (let i = 0; i < raw.length; i += 1) output[i] = raw.charCodeAt(i);
    return output;
  }
}
