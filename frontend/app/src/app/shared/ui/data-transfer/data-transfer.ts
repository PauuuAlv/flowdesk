import { Component, ElementRef, HostListener, computed, inject, input, output, signal } from '@angular/core';
import {
  DATA_ENTITIES,
  DataEntity,
  DataTransferService,
  ImportResult,
} from '../../../core/services/data-transfer.service';
import { PERMISSIONS } from '../../../core/models/permission.models';
import { SessionService } from '../../../core/services/session.service';

/**
 * Botones "Exportar CSV" / "Importar CSV" de un módulo. Con entity="all"
 * trabaja con el ZIP de toda la empresa (pestaña de Configuración).
 * Emite `imported` cuando una importación se aplicó, para recargar la página.
 */
@Component({
  selector: 'app-data-transfer',
  templateUrl: './data-transfer.html',
  styleUrl: './data-transfer.scss',
})
export class DataTransfer {
  private readonly service = inject(DataTransferService);
  private readonly permissions = new Set(inject(SessionService).getUser()?.permissions ?? []);

  readonly entity = input.required<DataEntity | 'all'>();
  /** Etiquetas de los botones más compactas (para encabezados con poco espacio). */
  readonly compact = input(false);
  /** true: un botón ⋮ con las opciones en un menú; false: botones visibles. */
  readonly menu = input(true);
  readonly imported = output<ImportResult>();

  private readonly host = inject(ElementRef<HTMLElement>);
  protected readonly menuOpen = signal(false);

  protected toggleMenu(event: Event) {
    event.stopPropagation();
    this.menuOpen.update((open) => !open);
  }

  @HostListener('document:click', ['$event'])
  protected closeOnOutsideClick(event: Event) {
    if (this.menuOpen() && !this.host.nativeElement.contains(event.target as Node)) this.menuOpen.set(false);
  }

  @HostListener('document:keydown.escape')
  protected closeOnEscape() {
    this.menuOpen.set(false);
  }

  protected readonly info = computed(() => DATA_ENTITIES.find((x) => x.key === this.entity()) ?? null);
  protected readonly isAll = computed(() => this.entity() === 'all');
  protected readonly label = computed(() => this.info()?.label ?? 'Toda la empresa');
  protected readonly canExport = computed(() => {
    const info = this.info();
    return info ? this.permissions.has(info.view) : this.permissions.has(PERMISSIONS.settingsUpdate);
  });
  protected readonly canImport = computed(() => {
    const info = this.info();
    return info
      ? this.permissions.has(info.view) && info.import.every((p) => this.permissions.has(p))
      : this.permissions.has(PERMISSIONS.settingsUpdate);
  });

  protected readonly exporting = signal(false);
  protected readonly dialogOpen = signal(false);
  protected readonly file = signal<File | null>(null);
  protected readonly importing = signal(false);
  protected readonly result = signal<ImportResult | null>(null);
  protected readonly error = signal('');
  protected readonly exportError = signal('');

  protected exportData() {
    this.exporting.set(true);
    this.exportError.set('');
    this.service.export(this.entity()).subscribe({
      next: () => this.exporting.set(false),
      error: () => {
        this.exporting.set(false);
        this.exportError.set('No fue posible exportar la información.');
      },
    });
  }

  protected downloadTemplate() {
    const entity = this.entity();
    if (entity !== 'all') this.service.template(entity).subscribe();
  }

  protected openImport() {
    this.file.set(null);
    this.result.set(null);
    this.error.set('');
    this.dialogOpen.set(true);
  }

  protected close() {
    if (this.importing()) return;
    this.dialogOpen.set(false);
  }

  protected chooseFile(event: Event) {
    const input = event.target as HTMLInputElement;
    this.file.set(input.files?.[0] ?? null);
    this.result.set(null);
    this.error.set('');
  }

  protected runImport() {
    const file = this.file();
    if (!file) return;
    this.importing.set(true);
    this.error.set('');
    this.result.set(null);
    this.service.import(this.entity(), file).subscribe({
      next: (result) => {
        this.importing.set(false);
        this.result.set(result);
        if (result.applied) this.imported.emit(result);
      },
      error: (e: Error) => {
        this.importing.set(false);
        this.error.set(e.message);
      },
    });
  }
}
