import { Component, computed, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { forkJoin } from 'rxjs';
import {
  Brand,
  MeasurementUnit,
  ProductCategory,
  ProductStatus,
  ProductType,
  SaveProductRequest,
} from '../../core/models/product.models';
import { ProductService } from '../../core/services/product.service';
import { Combobox, ComboOption } from '../../shared/ui/combobox/combobox';
import { CURRENCY_OPTIONS, DEFAULT_CURRENCY } from '../../core/models/currency.models';
import { SessionService } from '../../core/services/session.service';
@Component({
  selector: 'app-product-form-page',
  imports: [ReactiveFormsModule, RouterLink, Combobox],
  templateUrl: './product-form-page.html',
  styleUrl: './product-form-page.scss',
})
export class ProductFormPage {
  private readonly fb = inject(FormBuilder);
  private readonly service = inject(ProductService);
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly session = inject(SessionService);
  protected readonly currencyOptions = CURRENCY_OPTIONS;
  protected readonly id = this.route.snapshot.paramMap.get('productId');
  protected readonly loading = signal(Boolean(this.id));
  protected readonly saving = signal(false);
  protected readonly error = signal('');
  protected readonly units = signal<MeasurementUnit[]>([]);
  protected readonly brands = signal<Brand[]>([]);
  protected readonly categories = signal<ProductCategory[]>([]);
  /** Tipo de la sección desde la que se abrió (productos o servicios). */
  protected readonly routeType: ProductType =
    this.route.snapshot.data['itemType'] === 'product' ? 'product' : 'service';
  /** Ruta de la lista de la sección actual. */
  protected readonly listPath = this.routeType === 'product' ? '/panel/productos' : '/panel/servicios';
  private readonly itemType = signal<ProductType>(this.routeType);
  /** Solo las unidades del tipo seleccionado (producto o servicio). */
  protected readonly availableUnits = computed(() =>
    this.units().filter((unit) => unit.item_type === this.itemType()),
  );
  // Opciones de los combos filtrables.
  protected readonly typeOptions: ComboOption[] = [
    { value: 'product', label: 'Producto' },
    { value: 'service', label: 'Servicio' },
  ];
  protected readonly statusOptions: ComboOption[] = [
    { value: 'active', label: 'Activo' },
    { value: 'inactive', label: 'Inactivo' },
  ];
  protected readonly unitOptions = computed<ComboOption[]>(() =>
    this.availableUnits().map((unit) => ({
      value: unit.id,
      label: unit.is_active ? unit.name : `${unit.name} · Inactiva`,
      hint: unit.abbreviation,
    })),
  );
  protected readonly brandOptions = computed<ComboOption[]>(() => [
    { value: '', label: 'Sin marca' },
    ...this.brands().map((brand) => ({
      value: brand.id,
      label: brand.is_active ? brand.name : `${brand.name} · Inactiva`,
    })),
  ]);
  /** Categorías del catálogo; al editar incluye la actual aunque esté inactiva. */
  protected readonly categoryOptions = computed<ComboOption[]>(() => [
    { value: '', label: 'Sin categoría' },
    ...this.categories().map((category) => ({
      value: category.id,
      label: category.is_active ? category.name : `${category.name} · Inactiva`,
    })),
  ]);
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
    item_type: [this.routeType, Validators.required],
    unit_id: ['', Validators.required],
    brand_id: [''],
    category_id: [''],
    base_price: [0, [Validators.required, Validators.min(0)]],
    // Por defecto, la moneda configurada de la empresa; se puede cambiar junto al precio.
    currency: [this.session.getUser()?.tenant_currency || DEFAULT_CURRENCY, Validators.required],
    tax_rate: [16, [Validators.required, Validators.min(0), Validators.max(100)]],
    description: ['', Validators.maxLength(1000)],
    status: ['active' as ProductStatus, Validators.required],
  });
  constructor() {
    this.form.controls.sku.disable();
    this.form.controls.name.valueChanges.subscribe(() => this.refreshAutomaticSku());
    this.form.controls.item_type.valueChanges.subscribe((type) => {
      this.itemType.set(type);
      this.syncUnitWithType();
      this.refreshAutomaticSku();
    });
    forkJoin({
      units: this.service.units(Boolean(this.id)),
      brands: this.service.brands(Boolean(this.id)),
      categories: this.service.categories(Boolean(this.id)),
    }).subscribe({
      next: ({ units, brands, categories }) => {
        this.units.set(units); this.brands.set(brands); this.categories.set(categories);
        if (this.id) this.load(this.id);
        else { this.syncUnitWithType(); this.loading.set(false); }
      },
      error: () => { this.error.set('No fue posible cargar los catálogos (unidades, marcas y categorías).'); this.loading.set(false); },
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
      category_id: value.category_id || null,
      base_price: Number(value.base_price),
      currency: value.currency,
      tax_rate: Number(value.tax_rate),
      description: value.description.trim() || null,
      ...(this.id ? { sku: value.sku.trim().toUpperCase(), status: value.status } : {}),
    };
    this.saving.set(true);
    this.error.set('');
    this.service.save(body, this.id ?? undefined).subscribe({
      next: (saved) =>
        void this.router.navigate([saved.item_type === 'product' ? '/panel/productos' : '/panel/servicios']),
      error: (e) => {
        this.saving.set(false);
        const duplicateName = e.message?.startsWith('DUPLICATE_NAME:');
        const existingSku = duplicateName ? e.message.split(':', 2)[1] : '';
        this.error.set(
          e.message === 'UNIT_TYPE_MISMATCH'
            ? 'La unidad seleccionada no corresponde al tipo elegido. Selecciona otra unidad.'
            : duplicateName
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
          category_id: x.category_id ?? '',
          base_price: x.base_price,
          currency: x.currency,
          tax_rate: x.tax_rate,
          description: x.description ?? '',
          status: x.status,
        });
        // Si su unidad actual es de otro tipo (registros previos), se propone una válida.
        this.syncUnitWithType();
        this.loading.set(false);
      },
      error: () => {
        this.loading.set(false);
        this.error.set('No fue posible cargar el elemento.');
      },
    });
  }

  /** Mantiene la unidad seleccionada dentro de las del tipo actual. */
  private syncUnitWithType() {
    const available = this.availableUnits();
    const control = this.form.controls.unit_id;
    if (!available.some((unit) => unit.id === control.value)) control.setValue(available[0]?.id ?? '');
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
