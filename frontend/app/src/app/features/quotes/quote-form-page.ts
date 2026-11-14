import { Component, computed, inject, signal } from '@angular/core';
import { FormArray, FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { Client } from '../../core/models/client.models';
import { Opportunity, OpportunityAssignee } from '../../core/models/opportunity.models';
import { SaveQuoteRequest } from '../../core/models/quote.models';
import { ClientService } from '../../core/services/client.service';
import { OpportunityService } from '../../core/services/opportunity.service';
import { QuoteService } from '../../core/services/quote.service';
@Component({
  selector: 'app-quote-form-page',
  imports: [ReactiveFormsModule, RouterLink],
  templateUrl: './quote-form-page.html',
  styleUrl: './quote-form-page.scss',
})
export class QuoteFormPage {
  private fb = inject(FormBuilder);
  private service = inject(QuoteService);
  private cs = inject(ClientService);
  private os = inject(OpportunityService);
  private route = inject(ActivatedRoute);
  private router = inject(Router);
  id = this.route.snapshot.paramMap.get('quoteId');
  clients = signal<Client[]>([]);
  opportunities = signal<Opportunity[]>([]);
  users = signal<OpportunityAssignee[]>([]);
  selectedClient = signal('');
  loading = signal(true);
  saving = signal(false);
  error = signal('');
  form = this.fb.nonNullable.group({
    client_id: ['', Validators.required],
    opportunity_id: [''],
    owner_user_id: ['', Validators.required],
    issue_date: [new Date().toISOString().slice(0, 10), Validators.required],
    valid_until: ['', Validators.required],
    discount: [0, [Validators.required, Validators.min(0)]],
    tax_rate: [16, [Validators.required, Validators.min(0), Validators.max(100)]],
    notes: ['', Validators.maxLength(1000)],
    items: this.fb.array([this.item()]),
  });
  available = computed(() =>
    this.opportunities().filter((x) => x.client_id === this.selectedClient() && !x.archived),
  );
  get items() {
    return this.form.controls.items as FormArray;
  }
  get subtotal() {
    return this.items.controls.reduce(
      (s, c) => s + Number(c.get('quantity')?.value || 0) * Number(c.get('unit_price')?.value || 0),
      0,
    );
  }
  get tax() {
    return (
      (Math.max(0, this.subtotal - Number(this.form.controls.discount.value || 0)) *
        Number(this.form.controls.tax_rate.value || 0)) /
      100
    );
  }
  get total() {
    return Math.max(0, this.subtotal - Number(this.form.controls.discount.value || 0)) + this.tax;
  }
  rowAmount(row: any) {
    return Number(row.get('quantity')?.value || 0) * Number(row.get('unit_price')?.value || 0);
  }
  get discountValue() {
    return Number(this.form.controls.discount.value || 0);
  }
  constructor() {
    let n = 3;
    const done = () => {
      if (!--n) this.id ? this.load(this.id) : this.loading.set(false);
    };
    this.cs.list().subscribe({
      next: (x) => {
        this.clients.set(x.filter((c) => c.status === 'active'));
        done();
      },
      error: () => this.fail(),
    });
    this.os.list().subscribe({
      next: (x) => {
        this.opportunities.set(x);
        done();
      },
      error: () => this.fail(),
    });
    this.os.assignees().subscribe({
      next: (x) => {
        this.users.set(x);
        if (x[0]) this.form.controls.owner_user_id.setValue(x[0].id);
        done();
      },
      error: () => this.fail(),
    });
    this.form.controls.client_id.valueChanges.subscribe((v) => {
      this.selectedClient.set(v);
      this.form.controls.opportunity_id.setValue('');
    });
  }
  item() {
    return this.fb.nonNullable.group({
      description: ['', [Validators.required, Validators.minLength(2), Validators.maxLength(240)]],
      quantity: [1, [Validators.required, Validators.min(0.01)]],
      unit_price: [0, [Validators.required, Validators.min(0)]],
    });
  }
  add() {
    this.items.push(this.item());
  }
  remove(i: number) {
    if (this.items.length > 1) this.items.removeAt(i);
  }
  submit() {
    if (
      this.form.invalid ||
      this.form.controls.valid_until.value < this.form.controls.issue_date.value ||
      Number(this.form.controls.discount.value) > this.subtotal
    ) {
      this.form.markAllAsTouched();
      this.error.set('Revisa los campos, la vigencia y el descuento.');
      return;
    }
    const v = this.form.getRawValue();
    const body: SaveQuoteRequest = {
      ...v,
      opportunity_id: v.opportunity_id || null,
      notes: v.notes.trim() || null,
      items: v.items.map((x) => ({ ...x, description: x.description.trim() })),
    };
    this.saving.set(true);
    this.service.save(body, this.id ?? undefined).subscribe({
      next: () => void this.router.navigate(['/panel/cotizaciones']),
      error: () => {
        this.error.set('No fue posible guardar la cotización.');
        this.saving.set(false);
      },
    });
  }
  money(v: number) {
    return new Intl.NumberFormat('es-MX', { style: 'currency', currency: 'MXN' }).format(v);
  }
  private load(id: string) {
    this.service.get(id).subscribe({
      next: (q) => {
        this.items.clear();
        q.items.forEach((x) =>
          this.items.push(
            this.fb.nonNullable.group({
              description: [x.description, Validators.required],
              quantity: [x.quantity, [Validators.required, Validators.min(0.01)]],
              unit_price: [x.unit_price, [Validators.required, Validators.min(0)]],
            }),
          ),
        );
        this.form.patchValue({
          client_id: q.client_id,
          owner_user_id: q.owner_user_id,
          issue_date: q.issue_date,
          valid_until: q.valid_until,
          discount: q.discount,
          tax_rate: q.tax_rate,
          notes: q.notes ?? '',
        });
        this.selectedClient.set(q.client_id);
        this.form.controls.opportunity_id.setValue(q.opportunity_id ?? '');
        this.loading.set(false);
      },
      error: () => this.fail(),
    });
  }
  private fail() {
    this.error.set('No fue posible cargar la información necesaria.');
    this.loading.set(false);
  }
}
