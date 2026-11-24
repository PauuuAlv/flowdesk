import { Component, computed, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { forkJoin } from 'rxjs';
import { Client } from '../../core/models/client.models';
import { OpportunityAssignee, OpportunityStage, OpportunityStageCatalog, Pipeline } from '../../core/models/opportunity.models';
import { ClientService } from '../../core/services/client.service';
import { OpportunityService } from '../../core/services/opportunity.service';
import { Combobox, ComboOption } from '../../shared/ui/combobox/combobox';
import { CURRENCY_OPTIONS, DEFAULT_CURRENCY } from '../../core/models/currency.models';
import { SessionService } from '../../core/services/session.service';
import { preferredPipeline } from '../../core/services/pipeline-selection';

@Component({
  selector: 'app-opportunity-form-page',
  imports: [ReactiveFormsModule, RouterLink, Combobox],
  templateUrl: './opportunity-form-page.html',
  styleUrl: './opportunity-form-page.scss',
})
export class OpportunityFormPage {
  private readonly fb = inject(FormBuilder);
  private readonly service = inject(OpportunityService);
  private readonly clientsService = inject(ClientService);
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  protected readonly id = this.route.snapshot.paramMap.get('opportunityId');
  protected readonly clients = signal<Client[]>([]);
  protected readonly assignees = signal<OpportunityAssignee[]>([]);
  protected readonly loading = signal(true);
  protected readonly saving = signal(false);
  protected readonly error = signal('');
  protected readonly stages = signal<OpportunityStageCatalog[]>([]);
  // Opciones de los combos filtrables.
  protected readonly clientOptions = computed<ComboOption[]>(() =>
    this.clients().map((client) => ({ value: client.id, label: client.company_name })),
  );
  protected readonly assigneeOptions = computed<ComboOption[]>(() =>
    this.assignees().map((user) => ({ value: user.id, label: user.name })),
  );
  // Pipelines y el elegido en el formulario: las etapas se filtran por él.
  protected readonly pipelines = signal<Pipeline[]>([]);
  protected readonly pipelineId = signal<string | null>(null);
  /** Nombre del pipeline elegido, para el título ("Nueva oportunidad en Ventas"). */
  protected readonly pipelineName = computed(
    () => this.pipelines().find((p) => p.id === this.pipelineId())?.name ?? '',
  );
  protected readonly pipelineOptions = computed<ComboOption[]>(() =>
    this.pipelines()
      .filter((p) => p.is_active || p.id === this.pipelineId())
      .map((p) => ({ value: p.id, label: p.name, hint: p.is_default ? 'Predeterminado' : undefined })),
  );
  protected readonly stageOptions = computed<ComboOption[]>(() =>
    this.stages().filter((stage) => stage.pipeline_id === this.pipelineId()).map((stage) => ({
      value: stage.key,
      label: stage.name,
      hint: `${stage.default_probability}%`,
    })),
  );
  protected readonly currencyOptions = CURRENCY_OPTIONS;
  private readonly session = inject(SessionService);
  protected readonly form = this.fb.nonNullable.group({
    client_id: ['', Validators.required],
    pipeline_id: ['', Validators.required],
    owner_user_id: ['', Validators.required],
    name: ['', [Validators.required, Validators.minLength(3), Validators.maxLength(140)]],
    amount: [0, [Validators.required, Validators.min(0)]],
    // Por defecto, la moneda configurada de la empresa; se puede cambiar junto al valor.
    currency: [this.session.getUser()?.tenant_currency || DEFAULT_CURRENCY, Validators.required],
    stage: ['prospecting' as OpportunityStage, Validators.required],
    probability: [10, [Validators.required, Validators.min(0), Validators.max(100)]],
    expected_close_date: [''],
    notes: ['', Validators.maxLength(1000)],
  });
  constructor() {
    forkJoin({
      clients: this.clientsService.list(),
      assignees: this.service.assignees(),
      stages: this.service.stages(),
      pipelines: this.service.pipelines(true),
    }).subscribe({
      next: (d) => {
        this.clients.set(d.clients.filter((x) => x.status === 'active'));
        this.assignees.set(d.assignees);
        this.stages.set(d.stages);
        this.pipelines.set(d.pipelines);
        if (this.id) this.load(this.id);
        else {
          if (d.assignees.length) this.form.controls.owner_user_id.setValue(d.assignees[0].id);
          // El pipeline que venía mostrando el tablero (o el predeterminado).
          const requested = this.route.snapshot.queryParamMap.get('pipeline');
          const pipeline = preferredPipeline(d.pipelines.filter((p) => p.is_active), requested);
          if (pipeline) this.changePipeline(pipeline.id);
          this.loading.set(false);
        }
      },
      error: () => {
        this.error.set('No fue posible cargar los datos del formulario.');
        this.loading.set(false);
      },
    });
  }
  /** Al cambiar de pipeline se propone su primera etapa abierta. */
  protected changePipeline(id: string): void {
    this.pipelineId.set(id);
    this.form.controls.pipeline_id.setValue(id, { emitEvent: false });
    const options = this.stages().filter((stage) => stage.pipeline_id === id);
    const initial = options.find((stage) => stage.stage_type === 'normal') ?? options[0];
    this.form.controls.stage.setValue(initial?.key ?? '');
    if (initial) this.form.controls.probability.setValue(initial.default_probability);
  }
  protected changeStage(key: string): void {
    const stage = this.stages().find((item) => item.key === key);
    if (stage) this.form.controls.probability.setValue(stage.default_probability);
  }
  protected submit() {
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }
    const v = this.form.getRawValue();
    this.saving.set(true);
    this.service
      .save(
        {
          ...v,
          amount: Number(v.amount),
          expected_close_date: v.expected_close_date || null,
          notes: v.notes.trim() || null,
        },
        this.id ?? undefined,
      )
      .subscribe({
        next: () => void this.router.navigate(['/panel/oportunidades']),
        error: () => {
          this.saving.set(false);
          this.error.set('No fue posible guardar la oportunidad.');
        },
      });
  }
  private load(id: string) {
    this.service.get(id).subscribe({
      next: (x) => {
        this.form.setValue({
          client_id: x.client_id,
          pipeline_id: x.pipeline_id,
          owner_user_id: x.owner_user_id,
          name: x.name,
          amount: Number(x.amount),
          currency: x.currency,
          stage: x.stage,
          probability: x.probability,
          expected_close_date: x.expected_close_date ?? '',
          notes: x.notes ?? '',
        });
        this.pipelineId.set(x.pipeline_id);
        this.loading.set(false);
      },
      error: () => {
        this.error.set('La oportunidad no está disponible.');
        this.loading.set(false);
      },
    });
  }
}
