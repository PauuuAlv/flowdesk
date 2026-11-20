import { Component, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { forkJoin } from 'rxjs';
import { Client } from '../../core/models/client.models';
import { OpportunityAssignee, OpportunityStage, OpportunityStageCatalog } from '../../core/models/opportunity.models';
import { ClientService } from '../../core/services/client.service';
import { OpportunityService } from '../../core/services/opportunity.service';

@Component({
  selector: 'app-opportunity-form-page',
  imports: [ReactiveFormsModule, RouterLink],
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
  protected readonly form = this.fb.nonNullable.group({
    client_id: ['', Validators.required],
    owner_user_id: ['', Validators.required],
    name: ['', [Validators.required, Validators.minLength(3), Validators.maxLength(140)]],
    amount: [0, [Validators.required, Validators.min(0)]],
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
    }).subscribe({
      next: (d) => {
        this.clients.set(d.clients.filter((x) => x.status === 'active'));
        this.assignees.set(d.assignees);
        this.stages.set(d.stages);
        if (this.id) this.load(this.id);
        else {
          if (d.assignees.length) this.form.controls.owner_user_id.setValue(d.assignees[0].id);
          const initialStage = d.stages.find((stage) => stage.stage_type === 'normal') ?? d.stages[0];
          if (initialStage) {
            this.form.controls.stage.setValue(initialStage.key);
            this.form.controls.probability.setValue(initialStage.default_probability);
          }
          this.loading.set(false);
        }
      },
      error: () => {
        this.error.set('No fue posible cargar los datos del formulario.');
        this.loading.set(false);
      },
    });
  }
  protected changeStage(event: Event): void {
    const key = (event.target as HTMLSelectElement).value;
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
          owner_user_id: x.owner_user_id,
          name: x.name,
          amount: Number(x.amount),
          stage: x.stage,
          probability: x.probability,
          expected_close_date: x.expected_close_date ?? '',
          notes: x.notes ?? '',
        });
        this.loading.set(false);
      },
      error: () => {
        this.error.set('La oportunidad no está disponible.');
        this.loading.set(false);
      },
    });
  }
}
