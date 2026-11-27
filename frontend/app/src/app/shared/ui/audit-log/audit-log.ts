import { Component, computed, inject, input, OnDestroy, OnInit, signal } from '@angular/core';

import {
  AuditEntry,
  AuditFilters,
  AuditOperation,
  AuditPage,
  AuditScope,
} from '../../../core/models/audit.models';
import { AuditService } from '../../../core/services/audit.service';
import { ComboOption } from '../combobox/combobox';
import { MultiSelect } from '../multi-select/multi-select';

const OPERATION_LABELS: Record<AuditOperation, string> = {
  CREATE: 'Creación',
  UPDATE: 'Modificación',
  DELETE: 'Eliminación',
  EVENT: 'Evento',
};

const EVENT_LABELS: Record<string, string> = {
  'auth.login': 'Inicio de sesión',
  'auth.login_failed': 'Inicio de sesión fallido',
  'auth.register': 'Registro por invitación',
  'auth.password_changed': 'Cambio de contraseña',
  'auth.password_reset_requested': 'Solicitud de restablecer contraseña',
  'auth.password_reset': 'Contraseña restablecida',
  'tenant.created': 'Empresa creada',
  'tenant.deleted': 'Empresa eliminada',
  'subscription.updated': 'Suscripción actualizada',
  'plan_change.requested': 'Cambio de plan solicitado',
  'plan_change.approved': 'Cambio de plan aprobado',
  'plan_change.rejected': 'Cambio de plan rechazado',
};

/** Nombres legibles de los campos más comunes; el resto se muestra tal cual. */
const FIELD_LABELS: Record<string, string> = {
  id: 'Identificador',
  tenant_id: 'Empresa',
  name: 'Nombre',
  full_name: 'Nombre completo',
  company_name: 'Empresa',
  contact_name: 'Contacto',
  email: 'Correo',
  phone: 'Teléfono',
  status: 'Estado',
  notes: 'Notas',
  description: 'Descripción',
  title: 'Título',
  is_active: 'Activo',
  is_primary: 'Principal',
  is_default: 'Predeterminado',
  role_id: 'Rol',
  client_id: 'Cliente',
  owner_user_id: 'Responsable',
  job_title: 'Puesto',
  hashed_password: 'Contraseña',
  sku: 'SKU',
  price: 'Precio',
  unit_price: 'Precio unitario',
  quantity: 'Cantidad',
  currency: 'Moneda',
  amount: 'Monto',
  position: 'Posición',
  color: 'Color',
  plan_key: 'Plan',
  permission_code: 'Permiso',
  reason: 'Motivo',
};

interface FieldRow {
  field: string;
  before: string;
  after: string;
}

@Component({
  selector: 'app-audit-log',
  imports: [MultiSelect],
  templateUrl: './audit-log.html',
  styleUrl: './audit-log.scss',
})
export class AuditLog implements OnInit, OnDestroy {
  private readonly service = inject(AuditService);

  /** Qué bitácora consultar. */
  readonly scope = input.required<AuditScope>();
  /** Si la persona puede descargar el reporte PDF (permiso `*.audit.export`). */
  readonly canExport = input(false);

  protected readonly page = signal<AuditPage | null>(null);
  protected readonly loading = signal(true);
  protected readonly error = signal('');
  protected readonly expandedId = signal<string | null>(null);
  protected readonly filterOptions = signal<AuditFilters>({ entities: [], actors: [] });
  protected readonly downloading = signal(false);
  protected readonly downloadError = signal('');

  protected readonly pageNumber = signal(1);
  protected readonly pageSize = 25;
  protected readonly search = signal('');
  protected readonly operations = signal<AuditOperation[]>([]);
  protected readonly entities = signal<string[]>([]);
  protected readonly actorIds = signal<string[]>([]);
  protected readonly dateFrom = signal('');
  protected readonly dateTo = signal('');

  protected readonly operationOptions: ComboOption[] = Object.entries(OPERATION_LABELS).map(
    ([value, label]) => ({ value, label }),
  );
  protected readonly entityOptions = computed<ComboOption[]>(() => this.filterOptions().entities);
  protected readonly actorOptions = computed<ComboOption[]>(() => this.filterOptions().actors);
  protected readonly hasFilters = computed(
    () =>
      !!(
        this.search() ||
        this.operations().length ||
        this.entities().length ||
        this.actorIds().length ||
        this.dateFrom() ||
        this.dateTo()
      ),
  );
  protected readonly rangeLabel = computed(() => {
    const page = this.page();
    if (!page || page.total === 0) return '';
    const start = (page.page - 1) * page.page_size + 1;
    const end = Math.min(page.page * page.page_size, page.total);
    return `${start}–${end} de ${page.total}`;
  });
  protected readonly hasNext = computed(() => {
    const page = this.page();
    return !!page && page.page * page.page_size < page.total;
  });

  private searchTimer: ReturnType<typeof setTimeout> | null = null;

  ngOnInit(): void {
    this.service.filters(this.scope()).subscribe({
      next: (options) => this.filterOptions.set(options),
      error: () => undefined, // los filtros son opcionales; la lista sigue funcionando
    });
    this.load();
  }

  ngOnDestroy(): void {
    if (this.searchTimer) clearTimeout(this.searchTimer);
  }

  protected load(): void {
    this.loading.set(true);
    this.error.set('');
    this.service
      .list(this.scope(), { page: this.pageNumber(), page_size: this.pageSize, ...this.currentFilters() })
      .subscribe({
        next: (page) => {
          this.page.set(page);
          this.loading.set(false);
        },
        error: () => {
          this.error.set('No fue posible consultar la auditoría. Intenta de nuevo.');
          this.loading.set(false);
        },
      });
  }

  /** Descarga el reporte PDF con los filtros aplicados. */
  protected downloadReport(): void {
    this.downloading.set(true);
    this.downloadError.set('');
    this.service.report(this.scope(), this.currentFilters()).subscribe({
      next: (blob) => {
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        const stamp = new Date().toISOString().slice(0, 10);
        link.href = url;
        link.download = `auditoria-${this.scope() === 'platform' ? 'plataforma-' : ''}${stamp}.pdf`;
        link.click();
        setTimeout(() => URL.revokeObjectURL(url), 1000);
        this.downloading.set(false);
      },
      error: () => {
        this.downloadError.set('No fue posible generar el reporte PDF.');
        this.downloading.set(false);
      },
    });
  }

  private currentFilters() {
    return {
      operations: this.operations(),
      entities: this.entities(),
      actor_ids: this.actorIds(),
      search: this.search(),
      date_from: this.dateFrom() ? new Date(`${this.dateFrom()}T00:00:00`).toISOString() : undefined,
      date_to: this.dateTo() ? new Date(`${this.dateTo()}T23:59:59.999`).toISOString() : undefined,
    };
  }

  protected onSearch(value: string): void {
    this.search.set(value);
    if (this.searchTimer) clearTimeout(this.searchTimer);
    this.searchTimer = setTimeout(() => this.applyFilters(), 350);
  }

  protected setOperations(values: string[]): void {
    this.operations.set(values as AuditOperation[]);
    this.applyFilters();
  }

  protected setEntities(values: string[]): void {
    this.entities.set(values);
    this.applyFilters();
  }

  protected setActors(values: string[]): void {
    this.actorIds.set(values);
    this.applyFilters();
  }

  protected setDateFrom(value: string): void {
    this.dateFrom.set(value);
    this.applyFilters();
  }

  protected setDateTo(value: string): void {
    this.dateTo.set(value);
    this.applyFilters();
  }

  protected clearFilters(): void {
    this.search.set('');
    this.operations.set([]);
    this.entities.set([]);
    this.actorIds.set([]);
    this.dateFrom.set('');
    this.dateTo.set('');
    this.applyFilters();
  }

  protected goTo(page: number): void {
    this.pageNumber.set(Math.max(1, page));
    this.expandedId.set(null);
    this.load();
  }

  protected toggle(entry: AuditEntry): void {
    this.expandedId.set(this.expandedId() === entry.id ? null : entry.id);
  }

  private applyFilters(): void {
    this.pageNumber.set(1);
    this.expandedId.set(null);
    this.load();
  }

  // --- Presentación -------------------------------------------------------

  protected operationLabel(entry: AuditEntry): string {
    if (entry.operation === 'EVENT') return EVENT_LABELS[entry.action] ?? OPERATION_LABELS.EVENT;
    return OPERATION_LABELS[entry.operation];
  }

  protected actorLabel(entry: AuditEntry): string {
    if (entry.actor_type === 'system') return entry.actor_email ?? 'Sistema';
    if (entry.actor_type === 'anonymous') return entry.actor_email ? `Visitante (${entry.actor_email})` : 'Visitante';
    return entry.actor_email ?? 'Usuario no disponible';
  }

  protected actorKind(entry: AuditEntry): string {
    return (
      {
        user: 'Usuario de la empresa',
        platform_admin: 'Administración Flowdesk',
        system: 'Proceso del sistema',
        anonymous: 'Sin sesión',
      }[entry.actor_type] ?? entry.actor_type
    );
  }

  protected date(value: string): string {
    return new Intl.DateTimeFormat('es-MX', { dateStyle: 'medium', timeStyle: 'medium' }).format(
      new Date(value),
    );
  }

  protected day(value: string): string {
    return new Intl.DateTimeFormat('es-MX', { dateStyle: 'medium' }).format(new Date(value));
  }

  protected time(value: string): string {
    return new Intl.DateTimeFormat('es-MX', { timeStyle: 'medium' }).format(new Date(value));
  }

  /** "Chrome 131 · Windows" a partir del User-Agent. */
  protected browser(userAgent: string | null): string {
    if (!userAgent) return 'No disponible';
    const ua = userAgent;
    const match =
      ua.match(/(Edg|OPR|SamsungBrowser|Firefox|FxiOS|CriOS|Chrome|Version)\/(\d+)/) ?? null;
    const names: Record<string, string> = {
      Edg: 'Edge',
      OPR: 'Opera',
      SamsungBrowser: 'Samsung Internet',
      Firefox: 'Firefox',
      FxiOS: 'Firefox',
      CriOS: 'Chrome',
      Chrome: 'Chrome',
      Version: 'Safari',
    };
    const name = match ? `${names[match[1]]} ${match[2]}` : ua.split(' ')[0];
    const os = /Windows/.test(ua)
      ? 'Windows'
      : /Android/.test(ua)
        ? 'Android'
        : /iPhone|iPad/.test(ua)
          ? 'iOS'
          : /Mac OS X/.test(ua)
            ? 'macOS'
            : /Linux/.test(ua)
              ? 'Linux'
              : '';
    return os ? `${name} · ${os}` : name;
  }

  protected dataTitle(entry: AuditEntry): string {
    return (
      {
        CREATE: 'Información registrada',
        UPDATE: 'Cambios realizados',
        DELETE: 'Información eliminada',
        EVENT: 'Detalles del evento',
      }[entry.operation] ?? 'Detalles'
    );
  }

  protected rows(entry: AuditEntry): FieldRow[] {
    const before = entry.before_data ?? {};
    const after = entry.after_data ?? (entry.operation === 'EVENT' ? entry.details : {});
    const keys = Array.from(new Set([...Object.keys(before), ...Object.keys(after)]));
    return keys.map((key) => ({
      field: FIELD_LABELS[key] ?? key,
      before: this.value(before[key]),
      after: this.value(after[key]),
    }));
  }

  private value(value: unknown): string {
    if (value === undefined) return '';
    if (value === null || value === '') return '—';
    if (value === true) return 'Sí';
    if (value === false) return 'No';
    if (typeof value === 'object') return JSON.stringify(value);
    return String(value);
  }
}
