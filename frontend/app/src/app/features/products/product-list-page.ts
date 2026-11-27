import { Component, computed, inject, signal } from '@angular/core';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { Product, ProductStatus, ProductType } from '../../core/models/product.models';
import { PERMISSIONS } from '../../core/models/permission.models';
import { ProductService } from '../../core/services/product.service';
import { SessionService } from '../../core/services/session.service';
import { Combobox, ComboOption } from '../../shared/ui/combobox/combobox';
import { formatMoney } from '../../core/models/currency.models';
import { DataTransfer } from '../../shared/ui/data-transfer/data-transfer';

/** Valor de filtro para los elementos sin categoría o sin marca. */
const NONE = '__none__';

type SortKey = 'name' | 'category' | 'brand' | 'unit' | 'base_price' | 'tax_rate' | 'status';

function sortValue(item: Product, key: SortKey): string | number {
  switch (key) {
    case 'name':
      return item.name;
    case 'category':
      return item.category ?? '';
    case 'brand':
      return item.brand_name ?? '';
    case 'unit':
      return item.unit_name;
    case 'base_price':
      return Number(item.base_price);
    case 'tax_rate':
      return Number(item.tax_rate);
    case 'status':
      return item.status === 'active' ? 0 : 1;
  }
}

@Component({
  selector: 'app-product-list-page',
  imports: [RouterLink, Combobox, DataTransfer],
  templateUrl: './product-list-page.html',
  styleUrl: './product-list-page.scss',
})
export class ProductListPage {
  private readonly service = inject(ProductService);
  private readonly user = inject(SessionService).getUser();
  protected readonly items = signal<Product[]>([]);
  protected readonly loading = signal(true);
  protected readonly error = signal('');
  protected readonly success = signal('');
  /** Sección actual: la misma página sirve para productos y para servicios. */
  protected readonly itemType: ProductType =
    inject(ActivatedRoute).snapshot.data['itemType'] === 'product' ? 'product' : 'service';
  protected readonly isProduct = this.itemType === 'product';
  protected readonly basePath = this.isProduct ? '/panel/productos' : '/panel/servicios';
  protected readonly search = signal('');
  protected readonly status = signal<ProductStatus | 'all'>('all');
  protected readonly category = signal('all');
  protected readonly brand = signal('all');
  protected readonly unitFilter = signal('all');
  protected readonly sortKey = signal<SortKey>('name');
  protected readonly sortDir = signal<'asc' | 'desc'>('asc');
  protected readonly pending = signal<Product | null>(null);
  protected readonly processing = signal(false);
  protected readonly canCreate = this.has(PERMISSIONS.productsCreate);
  protected readonly canUpdate = this.has(PERMISSIONS.productsUpdate);
  protected readonly canDelete = this.has(PERMISSIONS.productsDelete);
  protected readonly statusOptions: ComboOption[] = [
    { value: 'all', label: 'Todos' },
    { value: 'active', label: 'Activos' },
    { value: 'inactive', label: 'Inactivos' },
  ];
  /** Elementos de la sección (solo productos o solo servicios). */
  private readonly sectionItems = computed(() => this.items().filter((x) => x.item_type === this.itemType));
  // Opciones de filtro tomadas de los elementos registrados en la sección.
  protected readonly categoryOptions = computed(() =>
    this.optionsFrom((x) => (x.category_id ? [x.category_id, x.category ?? ''] : [NONE, 'Sin categoría'])),
  );
  protected readonly brandOptions = computed(() =>
    this.optionsFrom((x) => (x.brand_id ? [x.brand_id, x.brand_name ?? ''] : [NONE, 'Sin marca'])),
  );
  protected readonly unitOptions = computed(() => this.optionsFrom((x) => [x.unit_id, x.unit_name]));
  protected readonly hasFilters = computed(
    () =>
      Boolean(this.search().trim()) ||
      [this.status(), this.category(), this.brand(), this.unitFilter()].some((v) => v !== 'all'),
  );
  protected readonly filtered = computed(() => {
    const q = this.search().trim().toLowerCase();
    const matches = (filter: string, id: string | null) => filter === 'all' || filter === (id ?? NONE);
    const rows = this.sectionItems().filter(
      (x) =>
        (this.status() === 'all' || x.status === this.status()) &&
        matches(this.category(), x.category_id) &&
        matches(this.brand(), x.brand_id) &&
        matches(this.unitFilter(), x.unit_id) &&
        (!q || `${x.name} ${x.sku} ${x.category ?? ''} ${x.brand_name ?? ''}`.toLowerCase().includes(q)),
    );
    const key = this.sortKey();
    const dir = this.sortDir() === 'asc' ? 1 : -1;
    return [...rows].sort((a, b) => {
      const va = sortValue(a, key);
      const vb = sortValue(b, key);
      const result =
        typeof va === 'number' && typeof vb === 'number'
          ? va - vb
          : String(va).localeCompare(String(vb), 'es', { sensitivity: 'base', numeric: true });
      return result * dir || a.name.localeCompare(b.name, 'es', { sensitivity: 'base' });
    });
  });
  constructor() {
    this.load();
  }
  protected load() {
    this.loading.set(true);
    this.service.list().subscribe({
      next: (x) => {
        this.items.set(x);
        this.loading.set(false);
      },
      error: () => {
        this.error.set(`No fue posible consultar los ${this.isProduct ? 'productos' : 'servicios'}.`);
        this.loading.set(false);
      },
    });
  }
  protected setSearch(e: Event) {
    this.search.set((e.target as HTMLInputElement).value);
  }
  protected setStatus(value: string) {
    this.status.set(value as ProductStatus | 'all');
  }
  protected setCategory(value: string) {
    this.category.set(value || 'all');
  }
  protected setBrand(value: string) {
    this.brand.set(value || 'all');
  }
  protected setUnit(value: string) {
    this.unitFilter.set(value || 'all');
  }
  protected clearFilters() {
    this.search.set('');
    this.status.set('all');
    this.category.set('all');
    this.brand.set('all');
    this.unitFilter.set('all');
  }
  /** Primer clic ordena ascendente; clics siguientes alternan el sentido. */
  protected sortBy(key: SortKey) {
    if (this.sortKey() === key) this.sortDir.update((d) => (d === 'asc' ? 'desc' : 'asc'));
    else {
      this.sortKey.set(key);
      this.sortDir.set('asc');
    }
  }
  protected ariaSort(key: SortKey) {
    return this.sortKey() === key ? (this.sortDir() === 'asc' ? 'ascending' : 'descending') : 'none';
  }
  protected confirm() {
    const item = this.pending();
    if (!item) return;
    const next: ProductStatus = item.status === 'active' ? 'inactive' : 'active';
    this.processing.set(true);
    this.service.updateStatus(item.id, next).subscribe({
      next: (x) => {
        this.items.update((all) => all.map((v) => (v.id === x.id ? x : v)));
        this.pending.set(null);
        this.processing.set(false);
        this.success.set(`${x.name} quedó ${x.status === 'active' ? 'activo' : 'inactivo'}.`);
      },
      error: () => {
        this.pending.set(null);
        this.processing.set(false);
        this.error.set('No fue posible cambiar el estado.');
      },
    });
  }
  protected money(v: number, currency: string) {
    return formatMoney(v, currency);
  }
  protected unit(v: string) {
    return (
      {
        piece: 'Pieza',
        service: 'Servicio',
        hour: 'Hora',
        day: 'Día',
        month: 'Mes',
        license: 'Licencia',
        package: 'Paquete',
      }[v] ?? v
    );
  }
  private optionsFrom(pick: (x: Product) => [string, string]): ComboOption[] {
    const seen = new Map<string, string>();
    for (const item of this.sectionItems()) {
      const [value, label] = pick(item);
      if (!seen.has(value)) seen.set(value, label);
    }
    const options = [...seen].map(([value, label]) => ({ value, label }));
    options.sort((a, b) =>
      a.value === NONE ? 1 : b.value === NONE ? -1 : a.label.localeCompare(b.label, 'es', { sensitivity: 'base' }),
    );
    return [{ value: 'all', label: 'Todas' }, ...options];
  }
  private has(p: (typeof PERMISSIONS)[keyof typeof PERMISSIONS]) {
    return Boolean(this.user?.permissions?.includes(p));
  }
}
