import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { catchError, Observable, throwError } from 'rxjs';
import { Brand, MeasurementUnit, Product, ProductStatus, SaveProductRequest } from '../models/product.models';
@Injectable({ providedIn: 'root' })
export class ProductService {
  private readonly http = inject(HttpClient);
  list(): Observable<Product[]> {
    return this.http.get<Product[]>('/api/products');
  }
  get(id: string): Observable<Product> {
    return this.http.get<Product>(`/api/products/${id}`);
  }
  save(body: SaveProductRequest, id?: string): Observable<Product> {
    const request = id
      ? this.http.patch<Product>(`/api/products/${id}`, body)
      : this.http.post<Product>('/api/products', body);
    return request.pipe(
      catchError((error: HttpErrorResponse) =>
        throwError(() => {
          if (error.status !== 409) return new Error('REQUEST_FAILED');
          const detail = error.error?.detail;
          if (detail?.code === 'PRODUCT_NAME_EXISTS') {
            return new Error(`DUPLICATE_NAME:${detail.sku}`);
          }
          return new Error('DUPLICATE_SKU');
        }),
      ),
    );
  }
  updateStatus(id: string, status: ProductStatus): Observable<Product> {
    return this.http.patch<Product>(`/api/products/${id}/status`, { status });
  }
  units(includeInactive = false, search = ''): Observable<MeasurementUnit[]> {
    return this.http.get<MeasurementUnit[]>('/api/product-catalogs/units', { params: { include_inactive: includeInactive, search } });
  }
  createUnit(body: { name: string; abbreviation: string }): Observable<MeasurementUnit> {
    return this.http.post<MeasurementUnit>('/api/product-catalogs/units', body);
  }
  updateUnit(id: string, body: { name: string; abbreviation: string; is_active: boolean }): Observable<MeasurementUnit> {
    return this.http.patch<MeasurementUnit>(`/api/product-catalogs/units/${id}`, body);
  }
  brands(includeInactive = false, search = ''): Observable<Brand[]> {
    return this.http.get<Brand[]>('/api/product-catalogs/brands', { params: { include_inactive: includeInactive, search } });
  }
  createBrand(body: { name: string; description: string | null }): Observable<Brand> {
    return this.http.post<Brand>('/api/product-catalogs/brands', body);
  }
  updateBrand(id: string, body: { name: string; description: string | null; is_active: boolean }): Observable<Brand> {
    return this.http.patch<Brand>(`/api/product-catalogs/brands/${id}`, body);
  }
}
