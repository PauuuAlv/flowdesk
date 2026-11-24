import { Component, DestroyRef, HostListener, computed, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { forkJoin } from 'rxjs';
import { LossReason, Opportunity, OpportunityStage, OpportunityStageCatalog, OpportunityStageHistory, Pipeline } from '../../core/models/opportunity.models';
import { PERMISSIONS } from '../../core/models/permission.models';
import { OpportunityService } from '../../core/services/opportunity.service';
import { SessionService } from '../../core/services/session.service';
import { preferredPipeline, rememberPipeline } from '../../core/services/pipeline-selection';
import { Combobox, ComboOption } from '../../shared/ui/combobox/combobox';
import { DEFAULT_CURRENCY, formatMoney, MoneyTotal, sumByCurrency } from '../../core/models/currency.models';

@Component({
  selector: 'app-opportunity-board-page',
  imports: [RouterLink, Combobox],
  templateUrl: './opportunity-board-page.html',
  styleUrl: './opportunity-board-page.scss',
})
export class OpportunityBoardPage {
  private readonly service = inject(OpportunityService);
  private readonly user = inject(SessionService).getUser();
  private readonly companyCurrency = this.user?.tenant_currency || DEFAULT_CURRENCY;
  // Pipelines activos y el que se muestra en el tablero (se recuerda en el navegador).
  protected readonly pipelines = signal<Pipeline[]>([]);
  protected readonly pipelineId = signal<string | null>(null);
  protected readonly pipelineOptions = computed<ComboOption[]>(() =>
    this.pipelines().map((p) => ({ value: p.id, label: p.name, hint: p.is_default ? 'Predeterminado' : undefined })),
  );
  private readonly allStages = signal<OpportunityStageCatalog[]>([]);
  /** Etapas del pipeline elegido: son las columnas del tablero. */
  protected readonly stages = computed(() => this.allStages().filter((stage) => stage.pipeline_id === this.pipelineId()));
  protected readonly lossReasons: Array<{ key: LossReason; label: string }> = [
    { key: 'price', label: 'Precio' },
    { key: 'no_response', label: 'Sin respuesta' },
    { key: 'competitor', label: 'Eligió a un competidor' },
    { key: 'budget_cancelled', label: 'Presupuesto cancelado' },
    { key: 'not_qualified', label: 'No era una oportunidad calificada' },
    { key: 'other', label: 'Otro' },
  ];
  protected readonly lossReasonOptions: ComboOption[] = this.lossReasons.map((reason) => ({
    value: reason.key,
    label: reason.label,
  }));
  protected readonly items = signal<Opportunity[]>([]);
  protected readonly loading = signal(true);
  protected readonly error = signal('');
  protected readonly search = signal('');
  protected readonly showArchived = signal(false);
  protected readonly closing = signal<Opportunity | null>(null);
  protected readonly closingStage = signal<OpportunityStageCatalog | null>(null);
  protected readonly saving = signal(false);
  protected readonly changing = signal<Opportunity | null>(null);
  protected readonly changingStage = signal<OpportunityStageCatalog | null>(null);
  protected readonly historyItem = signal<Opportunity | null>(null);
  protected readonly historyEntries = signal<OpportunityStageHistory[]>([]);
  protected readonly loadingHistory = signal(false);
  protected readonly canCreate = this.has(PERMISSIONS.opportunitiesCreate);
  protected readonly canUpdate = this.has(PERMISSIONS.opportunitiesUpdate);
  protected readonly canClose = this.has(PERMISSIONS.opportunitiesClose);
  protected readonly canArchive = this.has(PERMISSIONS.opportunitiesArchive);
  protected readonly visible = computed(() => {
    const q = this.search().trim().toLowerCase();
    return this.items().filter(
      (x) =>
        x.pipeline_id === this.pipelineId() &&
        (this.showArchived() || !x.archived) &&
        (!q || `${x.name} ${x.client_name} ${x.owner_name}`.toLowerCase().includes(q)),
    );
  });
  constructor() {
    this.load();
    // El menú usa posición fija: se cierra al desplazar la página o el tablero (scroll horizontal).
    const onScroll = () => this.dismissMenu();
    document.addEventListener('scroll', onScroll, true);
    inject(DestroyRef).onDestroy(() => document.removeEventListener('scroll', onScroll, true));
  }
  protected load() {
    this.loading.set(true);
    forkJoin({
      items: this.service.list(true),
      stages: this.service.stages(true),
      pipelines: this.service.pipelines(),
    }).subscribe({
      next: (v) => {
        this.items.set(v.items);
        this.allStages.set(v.stages);
        this.pipelines.set(v.pipelines);
        this.pipelineId.set(preferredPipeline(v.pipelines, this.pipelineId())?.id ?? null);
        this.loading.set(false);
      },
      error: () => {
        this.error.set('No fue posible consultar las oportunidades.');
        this.loading.set(false);
      },
    });
  }
  protected byStage(stage: OpportunityStage) {
    return this.visible().filter((item) => item.stage === stage);
  }
  /** Total de la columna por moneda (nunca se suman monedas distintas). */
  protected stageTotals(stage: OpportunityStage): MoneyTotal[] {
    const totals = sumByCurrency(this.byStage(stage), (item) => item.currency, (item) => Number(item.amount));
    // La moneda de la empresa siempre primero (y en cero si la columna está vacía).
    const own = totals.find((total) => total.currency === this.companyCurrency) ?? { currency: this.companyCurrency, amount: 0 };
    return [own, ...totals.filter((total) => total.currency !== this.companyCurrency)];
  }
  protected choosePipeline(id: string) {
    this.pipelineId.set(id);
    rememberPipeline(id);
  }
  protected updateSearch(event: Event) {
    this.search.set((event.target as HTMLInputElement).value);
  }
  // --- Arrastrar y soltar (RF-028) ---------------------------------------------
  // Soltar en una etapa abierta abre el modal de cambio de etapa (con nota); en
  // Ganada/Perdida abre el de cierre (con motivo). Nada cambia hasta confirmar.
  protected readonly dragging = signal<Opportunity | null>(null);
  protected readonly dropTarget = signal<string | null>(null);

  /** Se arrastran las oportunidades abiertas, no archivadas, si se pueden mover o cerrar. */
  protected canDrag(item: Opportunity): boolean {
    return !item.archived && this.stageType(item.stage) === 'normal' && (this.canUpdate || this.canClose);
  }

  /** ¿Se puede soltar la tarjeta que se arrastra en esta columna? */
  protected canDropOn(stage: OpportunityStageCatalog): boolean {
    const item = this.dragging();
    if (!item || item.stage === stage.key || !stage.is_active) return false;
    return stage.stage_type === 'normal' ? this.canUpdate : this.canClose;
  }

  protected onDragStart(event: DragEvent, item: Opportunity): void {
    if (!this.canDrag(item)) {
      event.preventDefault();
      return;
    }
    this.closeMenu();
    this.dragging.set(item);
    event.dataTransfer?.setData('text/plain', item.id); // Firefox exige datos para arrastrar
    if (event.dataTransfer) event.dataTransfer.effectAllowed = 'move';
  }

  protected onDragEnd(): void {
    this.dragging.set(null);
    this.dropTarget.set(null);
  }

  protected onDragOver(event: DragEvent, stage: OpportunityStageCatalog): void {
    if (!this.canDropOn(stage)) return; // sin preventDefault el navegador no permite soltar
    event.preventDefault();
    if (event.dataTransfer) event.dataTransfer.dropEffect = 'move';
    this.dropTarget.set(stage.key);
  }

  protected onDragLeave(event: DragEvent, stage: OpportunityStageCatalog): void {
    // Ignora la salida hacia un elemento hijo de la misma columna.
    const next = event.relatedTarget as Node | null;
    if (next && (event.currentTarget as HTMLElement).contains(next)) return;
    if (this.dropTarget() === stage.key) this.dropTarget.set(null);
  }

  protected onDrop(event: DragEvent, stage: OpportunityStageCatalog): void {
    event.preventDefault();
    const item = this.dragging();
    const allowed = this.canDropOn(stage);
    this.onDragEnd();
    if (!item || !allowed) return;
    if (stage.stage_type === 'normal') {
      this.changing.set(item);
      this.changingStage.set(stage);
      this.error.set('');
    } else {
      this.openClose(item, stage);
    }
  }

  // --- Detalles plegables (esquina doblada abajo a la derecha) -------------------
  /** Tarjetas desplegadas; por defecto todas muestran solo monto, nombre y cliente. */
  private readonly expanded = signal<ReadonlySet<string>>(new Set());

  protected isExpanded(id: string): boolean {
    return this.expanded().has(id);
  }

  protected toggleDetails(event: MouseEvent, id: string): void {
    event.stopPropagation();
    this.expanded.update((current) => {
      const next = new Set(current);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  // --- Menú de acciones de cada tarjeta (botón ⋯ arriba a la izquierda) ---------
  protected readonly menuItem = signal<Opportunity | null>(null);
  protected readonly menuPosition = signal({ top: 0, left: 0 });

  protected toggleMenu(event: MouseEvent, item: Opportunity): void {
    event.stopPropagation();
    if (this.menuItem()?.id === item.id) {
      this.closeMenu();
      return;
    }
    // Posición fija junto al botón: el tablero tiene scroll horizontal y recortaría el menú.
    const rect = (event.currentTarget as HTMLElement).getBoundingClientRect();
    const width = 208;
    this.menuPosition.set({
      top: rect.bottom + 6,
      left: Math.max(8, Math.min(rect.left, window.innerWidth - width - 8)),
    });
    this.menuItem.set(item);
  }

  protected closeMenu(): void {
    this.menuItem.set(null);
  }

  @HostListener('document:click')
  @HostListener('document:keydown.escape')
  @HostListener('window:resize')
  protected dismissMenu(): void {
    if (this.menuItem()) this.closeMenu();
  }


  protected cancelStageChange() {
    if (!this.saving()) { this.changing.set(null); this.changingStage.set(null); }
  }
  protected submitStageChange(event: Event) {
    event.preventDefault();
    const item = this.changing();
    const stage = this.changingStage();
    if (!item || !stage) return;
    const form = new FormData(event.target as HTMLFormElement);
    this.saving.set(true);
    this.service.updateStage(item.id, {
      stage: stage.key,
      probability: Number(form.get('probability')),
      expected_close_date: String(form.get('expected_close_date') || '') || null,
      note: String(form.get('note') || '').trim() || null,
    }).subscribe({
      next: (value) => { this.replace(value); this.saving.set(false); this.cancelStageChange(); },
      error: () => { this.error.set('No fue posible cambiar la etapa.'); this.saving.set(false); },
    });
  }
  protected openClose(item: Opportunity, stage: OpportunityStageCatalog) {
    this.closing.set(item);
    this.closingStage.set(stage);
    this.error.set('');
  }
  protected cancelClose() {
    if (!this.saving()) this.closing.set(null);
  }
  protected submitClose(event: Event) {
    event.preventDefault();
    const form = new FormData(event.target as HTMLFormElement);
    const stage = this.closingStage();
    if (!stage) return;
    const reason = form.get('loss_reason') as LossReason | null;
    if (stage.stage_type === 'lost' && !reason) {
      this.error.set('Selecciona el motivo por el que se perdió la oportunidad.');
      return;
    }
    const item = this.closing();
    if (!item) return;
    this.saving.set(true);
    this.service
      .close(
        item.id,
        stage.key,
        stage.stage_type === 'lost' ? reason : null,
        stage.stage_type === 'lost' ? String(form.get('loss_detail') || '') : null,
        String(form.get('note') || '').trim() || null,
      )
      .subscribe({
        next: (value) => {
          this.replace(value);
          this.closing.set(null);
          this.saving.set(false);
        },
        error: () => {
          this.error.set('No fue posible cerrar la oportunidad.');
          this.saving.set(false);
        },
      });
  }
  protected openHistory(item: Opportunity) {
    this.historyItem.set(item); this.historyEntries.set([]); this.loadingHistory.set(true);
    this.service.history(item.id).subscribe({
      next: (entries) => { this.historyEntries.set(entries); this.loadingHistory.set(false); },
      error: () => { this.error.set('No fue posible consultar el historial.'); this.loadingHistory.set(false); },
    });
  }
  protected closeHistory() { this.historyItem.set(null); this.historyEntries.set([]); }
  protected dateTime(value: string) {
    return new Intl.DateTimeFormat('es-MX', { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(value));
  }
  protected stageType(key: string) {
    return this.stages().find((stage) => stage.key === key)?.stage_type ?? 'normal';
  }
  protected closingStages(type: 'won' | 'lost') {
    return this.stages().filter((stage) => stage.is_active && stage.stage_type === type);
  }
  protected archive(item: Opportunity) {
    if (!confirm(`¿Archivar la oportunidad “${item.name}”? Podrás restaurarla después.`)) return;
    this.service
      .archive(item.id)
      .subscribe({
        next: (value) => this.replace(value),
        error: () => this.error.set('No fue posible archivar la oportunidad.'),
      });
  }
  protected restore(item: Opportunity) {
    this.service
      .restore(item.id)
      .subscribe({
        next: (value) => this.replace(value),
        error: () => this.error.set('No fue posible restaurar la oportunidad.'),
      });
  }
  protected toggleArchived(event: Event) {
    this.showArchived.set((event.target as HTMLInputElement).checked);
  }
  protected money(value: number, currency: string) {
    return formatMoney(value, currency, 0);
  }
  private replace(item: Opportunity) {
    this.items.update((values) => values.map((value) => (value.id === item.id ? item : value)));
    this.error.set('');
  }
  private has(permission: (typeof PERMISSIONS)[keyof typeof PERMISSIONS]) {
    return Boolean(this.user?.permissions?.includes(permission));
  }
}
