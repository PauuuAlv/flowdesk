import { Component, inject } from '@angular/core';
import { Router, RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';

import { SessionService } from '../../../core/services/session.service';
import { PlatformAccessService } from '../../../core/services/platform-access.service';

@Component({
  selector: 'app-platform-admin-shell',
  imports: [RouterLink, RouterLinkActive, RouterOutlet],
  templateUrl: './platform-admin-shell.html',
  styleUrl: './platform-admin-shell.scss',
})
export class PlatformAdminShell {
  private readonly session = inject(SessionService);
  private readonly router = inject(Router);
  protected readonly access = inject(PlatformAccessService);

  constructor() { this.access.load(); }

  protected logout(): void {
    this.session.clearPlatformAdmin();
    this.access.clear();
    void this.router.navigate(['/administracion-flowdesk/iniciar-sesion']);
  }
}
