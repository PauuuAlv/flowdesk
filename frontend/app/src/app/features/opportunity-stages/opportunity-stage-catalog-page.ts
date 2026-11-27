import { HttpErrorResponse } from '@angular/common/http';
import { Component, computed, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { Observable } from 'rxjs';

import {
  OpportunityStageCatalog,
  OpportunityStageType,
  Pipeline,
} from '../../core/models/opportunity.models';
import { PERMISSIONS } from '../../core/models/permission.models';
import { OpportunityService } from '../../core/services/opportunity.service';
import { preferredPipeline, rememberPipeline } from '../../core/services/pipeline-selection';
import { SessionService } from '../../core/services/session.service';
import { Combobox, ComboOption } from '../../shared/ui/combobox/combobox';
import { STAGE_PALETTE, suggestedStageColor } from '../../core/models/stage-colors';
import { DataTransfer } from '../../shared/ui/data-transfer/data-transfer';

type PipelineDialog = 'create' | 'edit' | 'delete' | null;

/** Pipelines de la empresa y las etapas de cada uno (RF-021/022/023). */
@Component({
  selector: 'app-opportunity-stage-catalog-page',
  imports: [ReactiveFormsModule, Combobox, DataTransfer],
  templateUrl: './opportunity-stage-catalog-page.html',
  styleUrl: './opportunity-stage-catalog-page.scss',
})
export class OpportunityStageCatalogPage {
  protected readonly stageTypeOptions: ComboOption[] = [
    { value: 'normal', label: 'Etapa normal' },
    { value: 'won', label: 'Cierre ganado' },
    { value: 'lost', label: 'Cierre perdido' },
  ];
  private readonly fb = inject(FormBuilder);
  private readonly service = inject(OpportunityService);
  protected readonly canManage = Boolean(
    inject(SessionService).getUser()?.permissions?.includes(PERMISSIONS.opportunitiesUpdate),
  );

  // --- Pipelines ---------------------------------------------------------------
  protected readonly pipelines = signal<Pipeline[]>([]);
  protected readonly selectedId = signal<string | null>(null);
  protected readonly selected = computed(() => this.pipelines().find((p) => p.id === this.selectedId()) ?? null);
  protected readonly pipelineOptions = computed<ComboOption[]>(() =>
    this.pipelines().map((p) => ({
      value: p.id,
      label: p.name,
      hint: p.is_default ? 'Predeterminado' : p.is_active ? undefined : 'Inactivo',
    })),
  );
  protected readonly copyOptions = computed<ComboOption[]>(() => [
    { value: '', label: 'Etapas predeterminadas', hint: '6 etapas' },
    ...this.pipelines().map((p) => ({ value: p.id, label: `Copiar de ${p.name}`, hint: `${p.stage_count} etapas` })),
  ]);
  protected readonly dialog = signal<PipelineDialog>(null);
  protected readonly dialogError = signal('');
  protected readonly processing = signal(false);
  protected readonly pipelineForm = this.fb.nonNullable.group({
    name: ['', [Validators.required, Validators.minLength(2), Validators.maxLength(80)]],
    description: ['', Validators.maxLength(200)],
    copy_stages_from: [''],
    color: [STAGE_PALETTE[0].value, [Validators.required, Validators.pattern(/^#[0-9a-fA-F]{6}$/)]],
  });

  // --- Etapas del pipeline elegido --------------------------------------------
  protected readonly stages = signal<OpportunityStageCatalog[]>([]);
  protected readonly loading = signal(true);
  protected readonly saving = signal(false);
  protected readonly error = signal('');
  protected readonly success = signal('');
  protected readonly search = signal('');
  protected readonly showInactive = signal(true);
  protected readonly editing = signal<OpportunityStageCatalog | null>(null);
  protected readonly form = this.fb.nonNullable.group({
    name: ['', [Validators.required, Validators.minLength(2), Validators.maxLength(80)]],
    stage_type: ['normal' as OpportunityStageType, Validators.required],
    default_probability: [10, [Validators.required, Validators.min(0), Validators.max(100)]],
    position: [1, [Validators.required, Validators.min(1), Validators.max(20)]],
    color: [STAGE_PALETTE[0].value, [Validators.required, Validators.pattern(/^#[0-9a-fA-F]{6}$/)]],
  });
  protected readonly palette = STAGE_PALETTE;
  /** Si la persona eligió un color, ya no se sugiere uno al cambiar el tipo. */
  private colorChosen = false;

  constructor() {
    this.loadPipelines();
    this.form.controls.stage_type.valueChanges.subscribe((type) => {
      if (!this.editing() && !this.colorChosen) {
        this.form.controls.color.setValue(suggestedStageColor(type, this.openStageCount()));
      }
    });
  }

  protected selectColor(color: string): void {
    this.colorChosen = true;
    this.form.controls.color.setValue(color.toLowerCase());
    this.form.controls.color.markAsDirty();
  }

  protected selectPipelineColor(color: string): void {
    this.pipelineForm.controls.color.setValue(color.toLowerCase());
    this.pipelineForm.controls.color.markAsDirty();
  }

  protected customPipelineColor(event: Event): void {
    this.selectPipelineColor((event.target as HTMLInputElement).value);
  }

  protected customColor(event: Event): void {
    this.selectColor((event.target as HTMLInputElement).value);
  }

  protected isPaletteColor(color: string): boolean {
    return this.palette.some((swatch) => swatch.value === color);
  }

  private openStageCount(): number {
    return this.stages().filter((stage) => stage.stage_type === 'normal').length;
  }

  protected loadPipelines(selectId?: string): void {
    this.service.pipelines(true).subscribe({
      next: (items) => {
        this.pipelines.set(items);
        const choice = preferredPipeline(items, selectId ?? this.selectedId());
        this.selectedId.set(choice?.id ?? null);
        this.load();
      },
      error: () => {
        this.error.set('No fue posible consultar los pipelines.');
        this.loading.set(false);
      },
    });
  }

  protected choosePipeline(id: string): void {
    this.selectedId.set(id);
    rememberPipeline(id);
    this.cancel();
    this.load();
  }

  protected load(): void {
    const pipeline = this.selectedId();
    if (!pipeline) {
      this.stages.set([]);
      this.loading.set(false);
      return;
    }
    this.loading.set(true);
    this.service.stages(this.showInactive(), this.search(), pipeline).subscribe({
      next: (items) => {
        this.stages.set(items);
        this.loading.set(false);
        if (!this.editing()) {
          this.form.controls.position.setValue(items.length + 1);
          if (!this.colorChosen) this.form.controls.color.setValue(suggestedStageColor(this.form.controls.stage_type.value, this.openStageCount()));
        }
      },
      error: () => { this.error.set('No fue posible consultar las etapas.'); this.loading.set(false); },
    });
  }

  protected searchChanged(event: Event): void {
    this.search.set((event.target as HTMLInputElement).value);
    this.load();
  }

  protected inactiveChanged(event: Event): void {
    this.showInactive.set((event.target as HTMLInputElement).checked);
    this.load();
  }

  // --- Diálogos de pipeline -----------------------------------------------------
  protected openPipelineDialog(kind: Exclude<PipelineDialog, null>): void {
    this.dialogError.set('');
    this.success.set('');
    const current = this.selected();
    if (kind === 'create') {
      const used = new Set(this.pipelines().map((p) => p.color));
      const color = (STAGE_PALETTE.slice(0, 8).find((swatch) => !used.has(swatch.value)) ?? STAGE_PALETTE[0]).value;
      this.pipelineForm.reset({ name: '', description: '', copy_stages_from: '', color });
    } else if (kind === 'edit' && current) {
      this.pipelineForm.reset({
        name: current.name,
        description: current.description ?? '',
        copy_stages_from: '',
        color: current.color,
      });
    }
    this.dialog.set(kind);
  }

  protected closeDialog(): void {
    if (this.processing()) return;
    this.dialog.set(null);
  }

  protected savePipeline(): void {
    if (this.pipelineForm.invalid) {
      this.pipelineForm.markAllAsTouched();
      return;
    }
    const value = this.pipelineForm.getRawValue();
    const current = this.dialog() === 'edit' ? this.selected() : null;
    const body = {
      name: value.name.trim(),
      description: value.description.trim() || null,
      color: value.color,
      ...(current
        ? { is_active: current.is_active, is_default: current.is_default }
        : { copy_stages_from: value.copy_stages_from || null }),
    };
    this.runPipelineRequest(this.service.savePipeline(body, current?.id), (saved) => {
      this.success.set(current ? `Se actualizó el pipeline ${saved.name}.` : `Se creó el pipeline ${saved.name} con ${saved.stage_count} etapas.`);
      if (!current) rememberPipeline(saved.id);
      this.loadPipelines(saved.id);
    });
  }

  protected makeDefault(): void {
    const current = this.selected();
    if (!current) return;
    this.updateFlags(current, { is_default: true, is_active: true }, `${current.name} ahora es el pipeline predeterminado.`);
  }

  protected toggleActive(): void {
    const current = this.selected();
    if (!current) return;
    this.updateFlags(
      current,
      { is_default: current.is_default, is_active: !current.is_active },
      current.is_active ? `Se desactivó el pipeline ${current.name}.` : `Se activó el pipeline ${current.name}.`,
    );
  }

  protected deletePipeline(): void {
    const current = this.selected();
    if (!current) return;
    this.runPipelineRequest(this.service.deletePipeline(current.id), () => {
      this.success.set(`Se eliminó el pipeline ${current.name}.`);
      this.selectedId.set(null);
      this.loadPipelines();
    });
  }

  private updateFlags(current: Pipeline, flags: { is_default: boolean; is_active: boolean }, message: string): void {
    this.error.set('');
    this.success.set('');
    this.service
      .savePipeline({ name: current.name, description: current.description, ...flags }, current.id)
      .subscribe({
        next: () => {
          this.success.set(message);
          this.loadPipelines(current.id);
        },
        error: (error: HttpErrorResponse) => this.error.set(this.pipelineMessage(error)),
      });
  }

  private runPipelineRequest<T>(request: Observable<T>, done: (result: T) => void): void {
    this.processing.set(true);
    this.dialogError.set('');
    request.subscribe({
      next: (result) => {
        this.processing.set(false);
        this.dialog.set(null);
        done(result);
      },
      error: (error: HttpErrorResponse) => {
        this.processing.set(false);
        this.dialogError.set(this.pipelineMessage(error));
      },
    });
  }

  private pipelineMessage(error: HttpErrorResponse): string {
    const detail = String(error.error?.detail ?? '');
    if (detail.includes('name already exists')) return 'Ya existe un pipeline con ese nombre.';
    if (detail.includes('limit')) return 'La empresa ya tiene el máximo de 10 pipelines.';
    if (detail.includes('open opportunities')) return 'No se puede desactivar: tiene oportunidades abiertas. Ciérralas, archívalas o muévelas a otro pipeline.';
    if (detail.includes('has opportunities')) return 'No se puede eliminar: tiene oportunidades (incluidas cerradas o archivadas). Puedes desactivarlo.';
    if (detail.includes('default pipeline cannot be deleted')) return 'El pipeline predeterminado no se puede eliminar.';
    if (detail.includes('another pipeline as default')) return 'Para cambiarlo, marca otro pipeline como predeterminado.';
    if (detail.includes('must be active')) return 'El pipeline predeterminado debe estar activo.';
    return 'No fue posible guardar el pipeline.';
  }

  // --- Etapas -------------------------------------------------------------------
  protected edit(stage: OpportunityStageCatalog): void {
    this.editing.set(stage);
    this.form.setValue({
      name: stage.name,
      stage_type: stage.stage_type,
      default_probability: stage.default_probability,
      position: stage.position,
      color: stage.color,
    });
    this.colorChosen = true;
    this.success.set('');
  }

  protected cancel(): void {
    this.editing.set(null);
    this.colorChosen = false;
    this.form.reset({
      name: '', stage_type: 'normal', default_probability: 10, position: this.stages().length + 1,
      color: suggestedStageColor('normal', this.openStageCount()),
    });
  }

  protected submit(): void {
    const pipelineId = this.selectedId();
    if (!pipelineId) return;
    if (this.form.invalid) { this.form.markAllAsTouched(); return; }
    this.saving.set(true); this.error.set(''); this.success.set('');
    const current = this.editing();
    const body = { ...this.form.getRawValue(), pipeline_id: pipelineId };
    const request = current
      ? this.service.updateCatalogStage(current.id, { ...body, is_active: current.is_active })
      : this.service.createStage(body);
    request.subscribe({
      next: () => {
        this.saving.set(false);
        this.success.set(current ? 'Etapa actualizada.' : 'Etapa creada.');
        this.cancel();
        this.load();
        this.loadPipelines();
      },
      error: (error: HttpErrorResponse) => { this.saving.set(false); this.error.set(this.message(error)); },
    });
  }

  protected toggle(stage: OpportunityStageCatalog): void {
    this.error.set(''); this.success.set('');
    this.service.updateCatalogStage(stage.id, {
      pipeline_id: stage.pipeline_id, name: stage.name, stage_type: stage.stage_type,
      default_probability: stage.default_probability, position: stage.position,
      color: stage.color, is_active: !stage.is_active,
    }).subscribe({
      next: () => { this.success.set(stage.is_active ? 'Etapa desactivada.' : 'Etapa activada.'); this.load(); },
      error: (error: HttpErrorResponse) => this.error.set(this.message(error)),
    });
  }

  private message(error: HttpErrorResponse): string {
    if (error.status === 409 && error.error?.detail === 'Stage has active opportunities')
      return 'No puedes desactivar una etapa que contiene oportunidades activas.';
    if (error.status === 409 && error.error?.detail === 'Opportunity stage limit reached')
      return 'Este pipeline ya alcanzó el límite de 20 etapas.';
    if (error.status === 409) return 'Ya existe una etapa con ese nombre en este pipeline.';
    return 'No fue posible guardar la etapa.';
  }
}
