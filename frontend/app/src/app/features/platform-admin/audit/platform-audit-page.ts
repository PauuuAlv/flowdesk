import { Component, computed, inject } from '@angular/core';

import { PLATFORM_PERMISSIONS } from '../../../core/models/platform-access.models';
import { PlatformAccessService } from '../../../core/services/platform-access.service';
import { AuditLog } from '../../../shared/ui/audit-log/audit-log';

/** Auditoría de las acciones de la administración de Flowdesk. */
@Component({
  selector: 'app-platform-audit-page',
  imports: [AuditLog],
  templateUrl: './platform-audit-page.html',
  styleUrl: '../../audit/audit-page.scss',
})
export class PlatformAuditPage {
  private readonly access = inject(PlatformAccessService);
  protected readonly canExport = computed(
    () => this.access.permissions().has(PLATFORM_PERMISSIONS.auditExport),
  );
}
