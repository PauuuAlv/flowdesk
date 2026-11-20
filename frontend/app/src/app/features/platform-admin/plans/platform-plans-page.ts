import { Component, inject, signal } from '@angular/core';

import { SaaSPlan } from '../../../core/models/auth.models';
import { AuthService } from '../../../core/services/auth.service';

@Component({
  selector: 'app-platform-plans-page',
  templateUrl: './platform-plans-page.html',
  styleUrl: './platform-plans-page.scss',
})
export class PlatformPlansPage {
  private readonly service = inject(AuthService);
  protected readonly plans = signal<SaaSPlan[]>([]);
  protected readonly loading = signal(true);
  protected readonly error = signal('');

  constructor() {
    this.service.listSaaSPlans().subscribe({
      next: (items) => { this.plans.set(items); this.loading.set(false); },
      error: () => { this.error.set('No fue posible consultar los planes.'); this.loading.set(false); },
    });
  }
  protected number(value: number): string { return new Intl.NumberFormat('es-MX').format(value); }
}
