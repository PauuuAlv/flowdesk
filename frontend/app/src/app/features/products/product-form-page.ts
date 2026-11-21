import { Component, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { forkJoin } from 'rxjs';
import {
  Brand,
  MeasurementUnit,
  ProductStatus,
  ProductType,
  SaveProductRequest,
} from '../../core/models/product.models';
import { ProductService } from '../../core/services/product.service';
@Component({
  selector: 'app-product-form-page',
  imports: [ReactiveFormsModule, RouterLink],
  templateUrl: './product-form-page.html',
  styleUrl: './product-form-page.scss',
})
export class ProductFormPage {
  private readonly fb = inject(FormBuilder);
  private readonly service = inject(ProductService);
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  protected readonly id = this.route.snapshot.paramMap.get('productId');
  protected readonly loading = signal(Boolean(this.id));
  protected readonly saving = signal(false);
  protected readonly error = signal('');
  protected readonly units = signal<MeasurementUnit[]>([]);
  protected readonly brands = signal<Brand[]>([]);
  protected readonly form = this.fb.nonNullable.group({
    name: ['', [Validators.required, Validators.minLength(2), Validators.maxLength(140)]],
    sku: [
      '',
      [
        Validators.required,
        Validators.minLength(2),
        Validators.maxLength(50),
        Validators.pattern(/^[A-Za-z0-9._-]+$/),
      ],
    ],
    item_type: ['service' as ProductType, Validators.required],
    unit_id: ['', Validators.required],
    brand_id: [''],
    category: ['', Validators.maxLength(80)],
    base_price: [0, [Validators.required, Validators.min(0)]],
    tax_rate: [16, [Validators.required, Validators.min(0), Validators.max(100)]],
    description: ['', Validators.maxLength(1000)],
    status: ['active' as ProductStatus, Validators.required],
  });
  constructor() {
    this.form.controls.sku.disable();
    this.form.controls.name.valueChanges.subscribe(() => this.refreshAutomaticSku());
    this.form.controls.item_type.valueChanges.subscribe(() => this.refreshAutomaticSku());
    forkJoin({ units: this.service.units(Boolean(this.id)), brands: this.service.brands(Boolean(this.id)) }).subscribe({
      next: ({ units, brands }) => {
        this.units.set(units); this.brands.set(brands);
        if (this.id) this.load(this.id);
        else { if (units.length) this.form.controls.unit_id.setValue(units[0].id); this.loading.set(false); }
      },
      error: () => { this.error.set('No fue posible cargar unidades y marcas.'); this.loading.set(false); },
    });
  }
  protected submit() {
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }
    const value = this.form.getRawValue();
    const body: SaveProductRequest = {
      name: value.name.trim(),
      item_type: value.item_type,
      unit_id: value.unit_id,
      brand_id: value.brand_id || null,
      category: value.category.trim() || null,
      base_price: Number(value.base_price),
      tax_rate: Number(value.tax_rate),
      description: value.description.trim() || null,
      ...(this.id ? { sku: value.sku.trim().toUpperCase(), status: value.status } : {}),
    };
    this.saving.set(true);
    this.error.set('');
    this.service.save(body, this.id ?? undefined).subscribe({
      next: () => void this.router.navigate(['/panel/productos']),
      error: (e) => {
        this.saving.set(false);
        const duplicateName = e.message?.startsWith('DUPLICATE_NAME:');
        const existingSku = duplicateName ? e.message.split(':', 2)[1] : '';
        this.error.set(
          duplicateName
            ? `Ya existe un elemento con ese nombre y utiliza el código ${existingSku}. Puedes editar el registro existente.`
            : e.message === 'DUPLICATE_SKU'
            ? 'Ya existe un elemento con ese código en tu empresa.'
            : 'No fue posible guardar el elemento.',
        );
      },
    });
  }
  private load(id: string) {
    this.service.get(id).subscribe({
      next: (x) => {
        this.form.setValue({
          name: x.name,
          sku: x.sku,
          item_type: x.item_type,
          unit_id: x.unit_id,
          brand_id: x.brand_id ?? '',
          category: x.category ?? '',
          base_price: x.base_price,
          tax_rate: x.tax_rate,
          description: x.description ?? '',
          status: x.status,
        });
        this.loading.set(false);
      },
      error: () => {
        this.loading.set(false);
        this.error.set('No fue posible cargar el elemento.');
      },
    });
  }

  private refreshAutomaticSku() {
    if (this.id) return;
    const name = this.form.controls.name.value.trim();
    const prefix = this.form.controls.item_type.value === 'product' ? 'PRO' : 'SER';
    const slug = name
      .normalize('NFD')
      .replace(/[\u0300-\u036f]/g, '')
      .toUpperCase()
      .replace(/[^A-Z0-9]+/g, '-')
      .replace(/^-|-$/g, '') || 'ELEMENTO';
    this.form.controls.sku.setValue(`${prefix}-${slug}`.slice(0, 50).replace(/-$/, ''), { emitEvent: false });
  }
}
