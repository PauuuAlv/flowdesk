import { Injectable, signal } from '@angular/core';

import { UserMeResponse } from '../models/auth.models';
import { PUSH_ASKED_KEY, PUSH_OPTOUT_KEY } from './push-notification.service';

/** Cuenta que ya inició sesión en este navegador (sin tokens ni contraseña). */
export interface KnownAccount {
  id: string;
  email: string;
  full_name: string | null;
  tenant_name: string | null;
  last_used_at: string;
}

const STORAGE_KEY = 'flowdesk.known_accounts';
const MAX_ACCOUNTS = 10;

/**
 * Cuentas que han accedido desde este navegador, al estilo del selector de Google:
 * el inicio de sesión las muestra para elegir una, y se pueden quitar.
 *
 * Solo guarda datos de presentación; para entrar siempre se pide la contraseña.
 * Quitar una cuenta también olvida sus preferencias de notificaciones en este
 * navegador, así que la próxima vez se le vuelve a preguntar.
 */
@Injectable({ providedIn: 'root' })
export class KnownAccountsService {
  readonly accounts = signal<KnownAccount[]>(this.read());

  /** Registra (o actualiza y pone primero) la cuenta con la que se inició sesión. */
  remember(user: Pick<UserMeResponse, 'id' | 'email' | 'full_name' | 'tenant_name'> | null): void {
    if (!user?.id || !user.email) return;
    const entry: KnownAccount = {
      id: user.id,
      email: user.email,
      full_name: user.full_name?.trim() || null,
      tenant_name: user.tenant_name?.trim() || null,
      last_used_at: new Date().toISOString(),
    };
    const rest = this.read().filter((account) => account.id !== entry.id);
    this.write([entry, ...rest].slice(0, MAX_ACCOUNTS));
  }

  /** Quita la cuenta de este navegador y olvida sus preferencias locales. */
  forget(id: string): void {
    this.write(this.read().filter((account) => account.id !== id));
    try {
      localStorage.removeItem(PUSH_ASKED_KEY + id);
      localStorage.removeItem(PUSH_OPTOUT_KEY + id);
    } catch {
      /* almacenamiento no disponible */
    }
  }

  private read(): KnownAccount[] {
    try {
      const value = JSON.parse(localStorage.getItem(STORAGE_KEY) ?? '[]');
      return Array.isArray(value) ? value.filter((item) => item?.id && item?.email) : [];
    } catch {
      return [];
    }
  }

  private write(accounts: KnownAccount[]): void {
    this.accounts.set(accounts);
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(accounts));
    } catch {
      /* almacenamiento no disponible: la lista solo vive en esta pestaña */
    }
  }
}
