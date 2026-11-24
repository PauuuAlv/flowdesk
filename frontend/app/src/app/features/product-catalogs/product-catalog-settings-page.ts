import { HttpErrorResponse } from '@angular/common/http';
import { Component, computed, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute } from '@angular/router';
import { Observable } from 'rxjs';

import { Brand, MeasurementUnit, ProductCategory, ProductType } from '../../core/models/product.models';
import { ProductService } from '../../core/services/product.service';
import { Combobox, ComboOption } from '../../shared/ui/combobox/combobox';

export const UNIT_TYPE_LABELS: Record<ProductType, string> = { product: 'Producto', service: 'Servicio' };

type CatalogKind = 'units' | 'brands' | 'categories';
/** Marcas y categorías comparten forma: nombre y descripción. */
type DescribedItem = Brand | ProductCategory;
type CatalogItem = MeasurementUnit | DescribedItem;

/** Textos de cada catálogo de productos y servicios. */
const CATALOGS: Record<CatalogKind, { title: string; help: string; singular: string; saved: string; placeholder: string; descriptionHint: string }> = {
  units: {
    title: 'Unidades de medida',
    help: 'Administra cómo se cuantifican los productos y servicios. Cada unidad se ofrece solo al tipo que le corresponde.',
    singular: 'unidad', saved: 'Unidad guardada correctamente.', placeholder: 'Ej: Caja', descriptionHint: '',
  },
  brands: {
    title: 'Marcas',
    help: 'Organiza las marcas de los productos que se utilizarán en cotizaciones.',
    singular: 'marca', saved: 'Marca guardada correctamente.', placeholder: 'Ej: Microsoft',
    descriptionHint: 'Información opcional de la marca',
  },
  categories: {
    title: 'Categorías',
    help: 'Agrupa tus productos y servicios (por ejemplo, licencias, soporte o capacitación) para encontrarlos y filtrarlos fácilmente.',
    singular: 'categoría', saved: 'Categoría guardada correctamente.', placeholder: 'Ej: Suscripciones',
    descriptionHint: '¿Qué productos o servicios incluye?',
  },
};

@Component({
  selector: 'app-product-catalog-settings-page',
  imports: [ReactiveFormsModule, Combobox],
  templateUrl: './product-catalog-settings-page.html',
  styleUrl: './product-catalog-settings-page.scss',
})
export class ProductCatalogSettingsPage {
  private readonly fb = inject(FormBuilder);
  private readonly service = inject(ProductService);
  protected readonly kind = inject(ActivatedRoute).snapshot.data['catalog'] as CatalogKind;
  protected readonly config = CATALOGS[this.kind];
  protected readonly typeLabels = UNIT_TYPE_LABELS;
  protected readonly typeOptions: ComboOption[] = [
    { value: 'product', label: 'Producto' },
    { value: 'service', label: 'Servicio' },
  ];
  protected readonly units = signal<MeasurementUnit[]>([]);
  /** Marcas o categorías, según la página. */
  protected readonly described = signal<DescribedItem[]>([]);
  protected readonly loading = signal(true);
  protected readonly saving = signal(false);
  protected readonly error = signal('');
  protected readonly success = signal('');
  protected readonly search = signal('');
  protected readonly typeFilter = signal<ProductType | 'all'>('all');
  protected readonly editing = signal<CatalogItem | null>(null);
  protected readonly visibleUnits = computed(() => {
    const filter = this.typeFilter();
    return filter === 'all' ? this.units() : this.units().filter((unit) => unit.item_type === filter);
  });
  protected readonly items = computed<CatalogItem[]>(() =>
    this.kind === 'units' ? this.visibleUnits() : this.described(),
  );
  protected readonly form = this.fb.nonNullable.group({
    name: ['', [Validators.required, Validators.minLength(2), Validators.maxLength(this.kind === 'brands' ? 100 : 80)]],
    abbreviation: ['', Validators.maxLength(15)],
    item_type: ['product' as ProductType, Validators.required],
    description: ['', Validators.maxLength(300)],
  });

  constructor() {
    if (this.kind === 'units') this.form.controls.abbreviation.addValidators(Validators.required);
    this.load();
  }

  protected get title() { return this.config.title; }
  protected get help() { return this.config.help; }

  protected load() {
    this.loading.set(true);
    const request: Observable<CatalogItem[]> =
      this.kind === 'units' ? this.service.units(true, this.search())
      : this.kind === 'brands' ? this.service.brands(true, this.search())
      : this.service.categories(true, this.search());
    request.subscribe({
      next: (items) => {
        if (this.kind === 'units') this.units.set(items as MeasurementUnit[]);
        else this.described.set(items as DescribedItem[]);
        this.loading.set(false);
      },
      error: () => { this.error.set(`No fue posible consultar ${this.title.toLowerCase()}.`); this.loading.set(false); },
    });
  }

  protected searchChanged(event: Event) { this.search.set((event.target as HTMLInputElement).value); this.load(); }
  protected typeFilterChanged(value: string) { this.typeFilter.set(value as ProductType | 'all'); }

  protected edit(item: CatalogItem) {
    this.editing.set(item);
    this.form.setValue({
      name: item.name,
      abbreviation: 'abbreviation' in item ? item.abbreviation : '',
      item_type: 'item_type' in item ? item.item_type : 'product',
      description: 'description' in item ? item.description ?? '' : '',
    });
  }

  protected cancel() { this.editing.set(null); this.form.reset({ name: '', abbreviation: '', item_type: 'product', description: '' }); }

  protected submit() {
    if (this.form.invalid) { this.form.markAllAsTouched(); return; }
    const v = this.form.getRawValue();
    const current = this.editing();
    this.saving.set(true); this.error.set(''); this.success.set('');
    const unit = { name: v.name.trim(), abbreviation: v.abbreviation.trim(), item_type: v.item_type };
    const described = { name: v.name.trim(), description: v.description.trim() || null };
    const request: Observable<CatalogItem> =
      this.kind === 'units'
        ? current ? this.service.updateUnit(current.id, { ...unit, is_active: current.is_active }) : this.service.createUnit(unit)
        : this.kind === 'brands'
          ? current ? this.service.updateBrand(current.id, { ...described, is_active: current.is_active }) : this.service.createBrand(described)
          : current ? this.service.updateCategory(current.id, { ...described, is_active: current.is_active }) : this.service.createCategory(described);
    request.subscribe({
      next: () => { this.saving.set(false); this.success.set(this.config.saved); this.cancel(); this.load(); },
      error: (e: HttpErrorResponse) => { this.saving.set(false); this.error.set(this.saveErrorMessage(e)); },
    });
  }

  protected toggle(item: CatalogItem) {
    const request: Observable<CatalogItem> =
      this.kind === 'units'
        ? this.service.updateUnit(item.id, { name: item.name, abbreviation: (item as MeasurementUnit).abbreviation, item_type: (item as MeasurementUnit).item_type, is_active: !item.is_active })
        : this.kind === 'brands'
          ? this.service.updateBrand(item.id, { name: item.name, description: (item as Brand).description, is_active: !item.is_active })
          : this.service.updateCategory(item.id, { name: item.name, description: (item as ProductCategory).description, is_active: !item.is_active });
    request.subscribe({
      next: () => { this.success.set(item.is_active ? 'Registro desactivado.' : 'Registro activado.'); this.load(); },
      error: (e: HttpErrorResponse) => this.error.set(e.status === 409 ? 'No se puede desactivar porque está siendo utilizado por productos activos.' : 'No fue posible cambiar el estado.'),
    });
  }

  /** Productos que usan la categoría (solo en el catálogo de categorías). */
  protected productCount(item: CatalogItem): number | null {
    return 'product_count' in item ? item.product_count : null;
  }

  private saveErrorMessage(e: HttpErrorResponse): string {
    if (e.status !== 409) return 'No fue posible guardar el registro.';
    if (String(e.error?.detail ?? '').includes('another type')) {
      return 'No se puede cambiar el tipo: hay productos o servicios del tipo actual que usan esta unidad.';
    }
    return `Ya existe o está en uso esta ${this.config.singular}.`;
  }
}
