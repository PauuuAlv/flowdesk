import { Component, inject, signal } from '@angular/core';
import { ApiHealthService } from '../../core/services/api-health.service';

type ApiState = 'idle' | 'checking' | 'online' | 'offline';

@Component({
  selector: 'app-welcome-page',
  templateUrl: './welcome-page.html',
  styleUrl: './welcome-page.scss'
})
export class WelcomePage {
  private readonly apiHealth = inject(ApiHealthService);

  protected readonly apiState = signal<ApiState>('idle');
  protected readonly apiMessage = signal('La comprobación se hará cuando el backend esté disponible.');

  protected checkApi(): void {
    this.apiState.set('checking');
    this.apiMessage.set('Consultando /api/health...');

    this.apiHealth.check().subscribe({
      next: (response) => {
        this.apiState.set('online');
        this.apiMessage.set(response.status ? `Backend disponible: ${response.status}` : 'Backend disponible.');
      },
      error: () => {
        this.apiState.set('offline');
        this.apiMessage.set('No fue posible conectar. Confirma que el servicio backend esté ejecutándose.');
      }
    });
  }
}
