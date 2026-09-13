import { Component, inject } from '@angular/core';
import { Router, RouterLink } from '@angular/router';

import { SessionService } from '../../core/services/session.service';

@Component({
  selector: 'app-dashboard-page',
  imports: [RouterLink],
  templateUrl: './dashboard-page.html',
  styleUrl: './dashboard-page.scss'
})
export class DashboardPage {
  private readonly sessionService = inject(SessionService);
  private readonly router = inject(Router);

  protected readonly user = this.sessionService.getUser();

  protected logout(): void {
    this.sessionService.clear();
    void this.router.navigate(['/iniciar-sesion']);
  }
}
