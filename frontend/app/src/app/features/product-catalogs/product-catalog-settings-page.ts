import { HttpErrorResponse } from '@angular/common/http';
import { Component, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute } from '@angular/router';
import { Observable } from 'rxjs';

import { Brand, MeasurementUnit } from '../../core/models/product.models';
import { ProductService } from '../../core/services/product.service';

@Component({
  selector: 'app-product-catalog-settings-page',
  imports: [ReactiveFormsModule],
  templateUrl: './product-catalog-settings-page.html',
  styleUrl: './product-catalog-settings-page.scss',
})
export class ProductCatalogSettingsPage {
  private readonly fb = inject(FormBuilder);
  private readonly service = inject(ProductService);
  protected readonly kind = inject(ActivatedRoute).snapshot.data['catalog'] as 'units' | 'brands';
  protected readonly units = signal<MeasurementUnit[]>([]);
  protected readonly brands = signal<Brand[]>([]);
  protected readonly loading = signal(true);
  protected readonly saving = signal(false);
  protected readonly error = signal('');
  protected readonly success = signal('');
  protected readonly search = signal('');
  protected readonly editing = signal<MeasurementUnit | Brand | null>(null);
  protected readonly form = this.fb.nonNullable.group({
    name: ['', [Validators.required, Validators.minLength(2), Validators.maxLength(100)]],
    abbreviation: ['', Validators.maxLength(15)],
    description: ['', Validators.maxLength(300)],
  });

  constructor() { if (this.kind === 'units') this.form.controls.abbreviation.addValidators(Validators.required); this.load(); }
  protected get title() { return this.kind === 'units' ? 'Unidades de medida' : 'Marcas'; }
  protected get help() { return this.kind === 'units' ? 'Administra cómo se cuantifican los productos y servicios.' : 'Organiza las marcas de los productos que se utilizarán en cotizaciones.'; }

  protected load() {
    this.loading.set(true);
    const request: Observable<MeasurementUnit[] | Brand[]> = this.kind === 'units' ? this.service.units(true, this.search()) : this.service.brands(true, this.search());
    request.subscribe({ next: (items) => { if (this.kind === 'units') this.units.set(items as MeasurementUnit[]); else this.brands.set(items as Brand[]); this.loading.set(false); }, error: () => { this.error.set(`No fue posible consultar ${this.title.toLowerCase()}.`); this.loading.set(false); } });
  }
  protected searchChanged(event: Event) { this.search.set((event.target as HTMLInputElement).value); this.load(); }
  protected edit(item: MeasurementUnit | Brand) {
    this.editing.set(item);
    this.form.setValue({ name: item.name, abbreviation: 'abbreviation' in item ? item.abbreviation : '', description: 'description' in item ? item.description ?? '' : '' });
  }
  protected cancel() { this.editing.set(null); this.form.reset({ name: '', abbreviation: '', description: '' }); }
  protected submit() {
    if (this.form.invalid) { this.form.markAllAsTouched(); return; }
    const v = this.form.getRawValue(); const current = this.editing(); this.saving.set(true); this.error.set(''); this.success.set('');
    const request: Observable<MeasurementUnit | Brand> = this.kind === 'units'
      ? current ? this.service.updateUnit(current.id, { name: v.name.trim(), abbreviation: v.abbreviation.trim(), is_active: current.is_active }) : this.service.createUnit({ name: v.name.trim(), abbreviation: v.abbreviation.trim() })
      : current ? this.service.updateBrand(current.id, { name: v.name.trim(), description: v.description.trim() || null, is_active: current.is_active }) : this.service.createBrand({ name: v.name.trim(), description: v.description.trim() || null });
    request.subscribe({ next: () => { this.saving.set(false); this.success.set(`${this.kind === 'units' ? 'Unidad' : 'Marca'} guardada correctamente.`); this.cancel(); this.load(); }, error: (e: HttpErrorResponse) => { this.saving.set(false); this.error.set(e.status === 409 ? `Ya existe o está en uso esta ${this.kind === 'units' ? 'unidad' : 'marca'}.` : 'No fue posible guardar el registro.'); } });
  }
  protected toggle(item: MeasurementUnit | Brand) {
    const request: Observable<MeasurementUnit | Brand> = this.kind === 'units'
      ? this.service.updateUnit(item.id, { name: item.name, abbreviation: (item as MeasurementUnit).abbreviation, is_active: !item.is_active })
      : this.service.updateBrand(item.id, { name: item.name, description: (item as Brand).description, is_active: !item.is_active });
    request.subscribe({ next: () => { this.success.set(item.is_active ? 'Registro desactivado.' : 'Registro activado.'); this.load(); }, error: (e: HttpErrorResponse) => this.error.set(e.status === 409 ? 'No se puede desactivar porque está siendo utilizado por productos activos.' : 'No fue posible cambiar el estado.') });
  }
}
