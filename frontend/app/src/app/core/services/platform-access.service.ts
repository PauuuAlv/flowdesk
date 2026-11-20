import { computed, inject, Injectable, signal } from '@angular/core';

import { PlatformAdminMe } from '../models/auth.models';
import { AuthService } from './auth.service';

@Injectable({ providedIn: 'root' })
export class PlatformAccessService {
  private readonly auth = inject(AuthService);
  readonly member = signal<PlatformAdminMe | null>(null);
  readonly loaded = signal(false);
  readonly canManage = computed(() => this.member()?.role === 'superadmin');

  load(): void {
    this.auth.platformAdminMe().subscribe({
      next: (member) => { this.member.set(member); this.loaded.set(true); },
      error: () => this.loaded.set(true),
    });
  }
  clear(): void { this.member.set(null); this.loaded.set(false); }
}
