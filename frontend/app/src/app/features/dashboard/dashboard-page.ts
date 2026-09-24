import { Component, inject } from '@angular/core';
import { RouterLink } from '@angular/router';

import { SessionService } from '../../core/services/session.service';

@Component({
  selector: 'app-dashboard-page',
  imports: [RouterLink],
  templateUrl: './dashboard-page.html',
  styleUrl: './dashboard-page.scss'
})
export class DashboardPage {
  private readonly sessionService = inject(SessionService);
  protected readonly user = this.sessionService.getUser();
}
