import { HttpErrorResponse } from '@angular/common/http';
import { Component, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';

import {
  OpportunityStageCatalog,
  OpportunityStageType,
} from '../../core/models/opportunity.models';
import { OpportunityService } from '../../core/services/opportunity.service';

@Component({
  selector: 'app-opportunity-stage-catalog-page',
  imports: [ReactiveFormsModule],
  templateUrl: './opportunity-stage-catalog-page.html',
  styleUrl: './opportunity-stage-catalog-page.scss',
})
export class OpportunityStageCatalogPage {
  private readonly fb = inject(FormBuilder);
  private readonly service = inject(OpportunityService);

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
  });

  constructor() {
    this.load();
  }

  protected load(): void {
    this.loading.set(true);
    this.service.stages(this.showInactive(), this.search()).subscribe({
      next: (items) => { this.stages.set(items); this.loading.set(false); },
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

  protected edit(stage: OpportunityStageCatalog): void {
    this.editing.set(stage);
    this.form.setValue({
      name: stage.name,
      stage_type: stage.stage_type,
      default_probability: stage.default_probability,
      position: stage.position,
    });
    this.success.set('');
  }

  protected cancel(): void {
    this.editing.set(null);
    this.form.reset({ name: '', stage_type: 'normal', default_probability: 10, position: this.stages().length + 1 });
  }

  protected submit(): void {
    if (this.form.invalid) { this.form.markAllAsTouched(); return; }
    this.saving.set(true); this.error.set(''); this.success.set('');
    const current = this.editing();
    const request = current
      ? this.service.updateCatalogStage(current.id, { ...this.form.getRawValue(), is_active: current.is_active })
      : this.service.createStage(this.form.getRawValue());
    request.subscribe({
      next: () => { this.saving.set(false); this.success.set(current ? 'Etapa actualizada.' : 'Etapa creada.'); this.cancel(); this.load(); },
      error: (error: HttpErrorResponse) => { this.saving.set(false); this.error.set(this.message(error)); },
    });
  }

  protected toggle(stage: OpportunityStageCatalog): void {
    this.error.set(''); this.success.set('');
    this.service.updateCatalogStage(stage.id, {
      name: stage.name, stage_type: stage.stage_type,
      default_probability: stage.default_probability, position: stage.position,
      is_active: !stage.is_active,
    }).subscribe({
      next: () => { this.success.set(stage.is_active ? 'Etapa desactivada.' : 'Etapa activada.'); this.load(); },
      error: (error: HttpErrorResponse) => this.error.set(this.message(error)),
    });
  }

  private message(error: HttpErrorResponse): string {
    if (error.status === 409 && error.error?.detail === 'Stage has active opportunities')
      return 'No puedes desactivar una etapa que contiene oportunidades activas.';
    if (error.status === 409 && error.error?.detail === 'Opportunity stage limit reached')
      return 'Este tenant ya alcanzó el límite inicial de 20 etapas.';
    if (error.status === 409) return 'Ya existe una etapa con ese nombre.';
    return 'No fue posible guardar la etapa.';
  }
}
