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

/**
 * Web Push estándar (W3C Push API + VAPID).
 *
 * Registra `public/sw.js`, suscribe el navegador con la clave pública VAPID del
 * backend y envía la suscripción a `/api/notifications/push/subscriptions`.
 */
@Injectable({ providedIn: 'root' })
export class PushNotificationService {
  private readonly http = inject(HttpClient);
  private config: PushConfig | null = null;

  readonly state = signal<PushState>('unsupported');
  readonly busy = signal(false);

  get isSupported(): boolean {
    return typeof window !== 'undefined'
      && window.isSecureContext
      && 'serviceWorker' in navigator
      && 'PushManager' in window
      && 'Notification' in window;
  }

  /** Revisa el estado y, si ya hay suscripción, la reasocia con el usuario actual. */
  async sync(): Promise<void> {
    if (!this.isSupported) {
      this.state.set('unsupported');
      return;
    }
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
    if (Notification.permission === 'denied') {
      this.state.set('denied');
      return;
    }
    const registration = await this.registration();
    let subscription = await registration.pushManager.getSubscription();
    if (subscription && !this.sameKey(subscription, this.config.public_key)) {
      // Las claves VAPID cambiaron en el servidor: la suscripción anterior ya no sirve.
      await subscription.unsubscribe();
      subscription = null;
    }
    if (subscription && Notification.permission === 'granted') {
      await this.save(subscription);
      this.state.set('subscribed');
    } else {
      this.state.set('available');
    }
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
      if (permission !== 'granted') {
        this.state.set(permission === 'denied' ? 'denied' : 'available');
        return this.state();
      }
      const registration = await this.registration();
      const subscription = (await registration.pushManager.getSubscription())
        ?? (await registration.pushManager.subscribe({
          userVisibleOnly: true,
          applicationServerKey: this.decodeKey(this.config.public_key),
        }));
      await this.save(subscription);
      this.state.set('subscribed');
      return 'subscribed';
    } finally {
      this.busy.set(false);
    }
  }

  /** Quita la suscripción de este navegador (también al cerrar sesión). */
  async disable(): Promise<void> {
    if (!this.isSupported) return;
    this.busy.set(true);
    try {
      const registration = await navigator.serviceWorker.getRegistration(SERVICE_WORKER_URL);
      const subscription = await registration?.pushManager.getSubscription();
      if (subscription) {
        await firstValueFrom(this.http.delete<void>('/api/notifications/push/subscriptions', {
          body: { endpoint: subscription.endpoint },
        })).catch(() => undefined);
        await subscription.unsubscribe();
      }
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
