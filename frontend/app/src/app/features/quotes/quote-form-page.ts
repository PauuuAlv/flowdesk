import { Component, computed, inject, signal } from '@angular/core';
import { FormArray, FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { Client } from '../../core/models/client.models';
import { Opportunity, OpportunityAssignee } from '../../core/models/opportunity.models';
import { SaveQuoteRequest } from '../../core/models/quote.models';
import { Product } from '../../core/models/product.models';
import { ClientService } from '../../core/services/client.service';
import { OpportunityService } from '../../core/services/opportunity.service';
import { QuoteService } from '../../core/services/quote.service';
import { ProductService } from '../../core/services/product.service';
import { CompanySettingsService } from '../../core/services/company-settings.service';
import { Combobox, ComboOption } from '../../shared/ui/combobox/combobox';
import { CURRENCY_OPTIONS, DEFAULT_CURRENCY, formatMoney } from '../../core/models/currency.models';
import { SessionService } from '../../core/services/session.service';
import { HttpErrorResponse } from '@angular/common/http';
@Component({
  selector: 'app-quote-form-page',
  imports: [ReactiveFormsModule, RouterLink, Combobox],
  templateUrl: './quote-form-page.html',
  styleUrl: './quote-form-page.scss',
})
export class QuoteFormPage {
  private fb = inject(FormBuilder);
  private service = inject(QuoteService);
  private cs = inject(ClientService);
  private os = inject(OpportunityService);
  private ps = inject(ProductService);
  private settingsService = inject(CompanySettingsService);
  private route = inject(ActivatedRoute);
  private router = inject(Router);
  id = this.route.snapshot.paramMap.get('quoteId');
  clients = signal<Client[]>([]);
  opportunities = signal<Opportunity[]>([]);
  users = signal<OpportunityAssignee[]>([]);
  products = signal<Product[]>([]);
  private session = inject(SessionService);
  private readonly companyCurrency = this.session.getUser()?.tenant_currency || DEFAULT_CURRENCY;
  currencyOptions = CURRENCY_OPTIONS;
  /** Moneda de la cotización (todos sus importes y conceptos del catálogo). */
  currency = signal(this.companyCurrency);
  currencyNotice = signal('');
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
    // Por defecto la moneda de la empresa; se puede cambiar junto a los conceptos.
    currency: [this.companyCurrency, Validators.required],
    notes: ['', Validators.maxLength(1000)],
    items: this.fb.array([this.item()]),
  });
  available = computed(() =>
    this.opportunities().filter((x) => x.client_id === this.selectedClient() && !x.archived),
  );
  // Opciones de los combos filtrables.
  clientOptions = computed<ComboOption[]>(() =>
    this.clients().map((client) => ({ value: client.id, label: client.company_name })),
  );
  opportunityOptions = computed<ComboOption[]>(() => [
    { value: '', label: 'Sin oportunidad' },
    ...this.available().map((item) => ({ value: item.id, label: item.name })),
  ]);
  userOptions = computed<ComboOption[]>(() =>
    this.users().map((user) => ({ value: user.id, label: user.name })),
  );
  /** Se busca por nombre o por SKU; "Concepto manual" deja escribir la descripción libre. */
  productOptions = computed<ComboOption[]>(() => [
    { value: '', label: 'Concepto manual' },
    // Solo productos en la moneda de la cotización: no se mezclan monedas.
    ...this.products()
      .filter((product) => product.currency === this.currency())
      .map((product) => ({ value: product.id, label: product.name, hint: product.sku })),
  ]);
  get items() {
    return this.form.controls.items as FormArray;
  }
  get subtotal() {
    return this.items.controls.reduce(
      (s, c) => s + Number(c.get('quantity')?.value || 0) * Number(c.get('unit_price')?.value || 0),
      0,
    );
  }
  get total() {
    return this.subtotal - this.discountValue;
  }
  rowGross(row: any) {
    return Number(row.get('quantity')?.value || 0) * Number(row.get('unit_price')?.value || 0);
  }
  rowDiscount(row: any) {
    return (this.rowGross(row) * Number(row.get('discount_percent')?.value || 0)) / 100;
  }
  rowAmount(row: any) {
    return this.rowGross(row) - this.rowDiscount(row);
  }
  get discountValue() {
    return this.items.controls.reduce((total, row) => total + this.rowDiscount(row), 0);
  }
  constructor() {
    let n = 5;
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
    this.ps.list().subscribe({
      next: (x) => {
        this.products.set(x.filter((p) => p.status === 'active'));
        done();
      },
      error: () => this.fail(),
    });
    this.settingsService.get().subscribe({
      next: (x) => {
        if (!this.id) {
          const issue = new Date(`${this.form.controls.issue_date.value}T12:00:00`);
          issue.setDate(issue.getDate() + x.quote_validity_days);
          this.form.patchValue({
            valid_until: issue.toISOString().slice(0, 10),
          });
        }
        done();
      },
      error: () => this.fail(),
    });
    this.form.controls.currency.valueChanges.subscribe((code) => this.onCurrencyChange(code));
    // En una cotización nueva, al elegir una oportunidad se adopta su moneda.
    this.form.controls.opportunity_id.valueChanges.subscribe((id) => {
      if (this.id || !id) return;
      const opportunity = this.opportunities().find((item) => item.id === id);
      if (opportunity && opportunity.currency !== this.form.controls.currency.value) {
        this.form.controls.currency.setValue(opportunity.currency);
      }
    });
    this.form.controls.client_id.valueChanges.subscribe((v) => {
      this.selectedClient.set(v);
      this.form.controls.opportunity_id.setValue('');
    });
  }
  item() {
    return this.fb.nonNullable.group({
      product_id: [''],
      description: ['', [Validators.required, Validators.minLength(2), Validators.maxLength(240)]],
      quantity: [1, [Validators.required, Validators.min(0.01)]],
      unit_price: [0, [Validators.required, Validators.min(0)]],
      discount_percent: [0, [Validators.required, Validators.min(0), Validators.max(100)]],
    });
  }
  add() {
    this.items.push(this.item());
  }
  remove(i: number) {
    if (this.items.length > 1) this.items.removeAt(i);
  }
  selectProduct(i: number, id: string) {
    const product = this.products().find((x) => x.id === id);
    if (product)
      this.items
        .at(i)
        .patchValue({
          product_id: product.id,
          description: product.name,
          unit_price: product.base_price,
        });
  }
  submit() {
    if (
      this.form.invalid ||
      this.form.controls.valid_until.value < this.form.controls.issue_date.value
    ) {
      this.form.markAllAsTouched();
      this.error.set('Revisa los campos, la vigencia y los descuentos por concepto.');
      return;
    }
    const v = this.form.getRawValue();
    const body: SaveQuoteRequest = {
      ...v,
      opportunity_id: v.opportunity_id || null,
      notes: v.notes.trim() || null,
      items: v.items.map((x) => ({
        ...x,
        product_id: x.product_id || null,
        description: x.description.trim(),
      })),
    };
    this.saving.set(true);
    this.service.save(body, this.id ?? undefined).subscribe({
      next: () => void this.router.navigate(['/panel/cotizaciones']),
      error: (e: HttpErrorResponse) => {
        const detail = e.error?.detail;
        this.error.set(
          detail?.code === 'PRODUCT_CURRENCY_MISMATCH'
            ? `El producto ${detail.product} está en ${detail.product_currency} y la cotización en ${detail.quote_currency}. Cambia la moneda o usa un concepto manual.`
            : 'No fue posible guardar la cotización.',
        );
        this.saving.set(false);
      },
    });
  }
  money(v: number) {
    return formatMoney(v, this.currency());
  }
  /**
   * Al cambiar la moneda, los conceptos ligados a productos de otra moneda pasan
   * a ser conceptos manuales (se conservan descripción y precio para revisarlos).
   */
  private onCurrencyChange(code: string) {
    this.currency.set(code);
    let unlinked = 0;
    for (const row of this.items.controls) {
      const productId = row.get('product_id')?.value;
      const product = productId ? this.products().find((x) => x.id === productId) : null;
      if (product && product.currency !== code) {
        row.patchValue({ product_id: '' });
        unlinked++;
      }
    }
    this.currencyNotice.set(
      unlinked
        ? `La cotización ahora está en ${code}. ${unlinked === 1 ? 'Un concepto quedó' : unlinked + ' conceptos quedaron'} como concepto manual porque su producto está en otra moneda; revisa su precio.`
        : '',
    );
  }
  private load(id: string) {
    this.service.get(id).subscribe({
      next: (q) => {
        this.items.clear();
        q.items.forEach((x) =>
          this.items.push(
            this.fb.nonNullable.group({
              product_id: [x.product_id ?? ''],
              description: [x.description, Validators.required],
              quantity: [x.quantity, [Validators.required, Validators.min(0.01)]],
              unit_price: [x.unit_price, [Validators.required, Validators.min(0)]],
              discount_percent: [
                x.discount_percent,
                [Validators.required, Validators.min(0), Validators.max(100)],
              ],
            }),
          ),
        );
        this.form.patchValue({
          client_id: q.client_id,
          owner_user_id: q.owner_user_id,
          issue_date: q.issue_date,
          valid_until: q.valid_until,
          notes: q.notes ?? '',
        });
        this.form.controls.currency.setValue(q.currency, { emitEvent: false });
        this.currency.set(q.currency);
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
