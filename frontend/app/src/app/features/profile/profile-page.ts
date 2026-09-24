import { Component, inject } from '@angular/core';

import { SessionService } from '../../core/services/session.service';

@Component({
  selector: 'app-profile-page',
  templateUrl: './profile-page.html',
  styleUrl: './profile-page.scss'
})
export class ProfilePage {
  private readonly sessionService = inject(SessionService);
  protected readonly user = this.sessionService.getUser();
}
