import { Component, inject } from '@angular/core';

import { PERMISSIONS } from '../../core/models/permission.models';
import { SessionService } from '../../core/services/session.service';

import { AuditLog } from '../../shared/ui/audit-log/audit-log';

/** Auditoría de la empresa (requiere el permiso `audit.view`). */
@Component({
  selector: 'app-tenant-audit-page',
  imports: [AuditLog],
  template: `
    <main class="page">
      <header>
        <p class="eyebrow">Seguridad y control</p>
        <h1>Auditoría</h1>
        <span>
          Historial de lo que los usuarios de tu empresa crean, modifican y eliminan: quién, cuándo,
          desde qué IP y navegador, y cómo estaba la información antes y después.
        </span>
      </header>
      <app-audit-log scope="tenant" [canExport]="canExport" />
    </main>
  `,
  styleUrl: './audit-page.scss',
})
export class TenantAuditPage {
  protected readonly canExport =
    inject(SessionService).getUser()?.permissions?.includes(PERMISSIONS.auditExport) ?? false;
}
