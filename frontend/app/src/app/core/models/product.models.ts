export type ProductType = 'product' | 'service';
export type ProductUnit = string;
export type ProductStatus = 'active' | 'inactive';
export interface Product {
  id: string;
  name: string;
  sku: string;
  description: string | null;
  /** Categoría del catálogo (opcional) y su nombre para mostrar. */
  category_id: string | null;
  category: string | null;
  item_type: ProductType;
  unit: ProductUnit;
  unit_id: string;
  unit_name: string;
  unit_abbreviation: string;
  brand_id: string | null;
  brand_name: string | null;
  base_price: number;
  currency: string;
  tax_rate: number;
  status: ProductStatus;
  created_at: string;
  updated_at: string;
}
export interface SaveProductRequest {
  name: string;
  sku?: string;
  description: string | null;
  category_id: string | null;
  item_type: ProductType;
  unit_id: string;
  brand_id: string | null;
  base_price: number;
  /** Sin indicarla, el backend usa la moneda de la empresa. */
  currency?: string;
  tax_rate: number;
  status?: ProductStatus;
}
export interface MeasurementUnit {
  id: string;
  key: string;
  name: string;
  abbreviation: string;
  /** Las unidades de producto solo se ofrecen a productos y las de servicio, a servicios. */
  item_type: ProductType;
  is_active: boolean;
  created_at: string;
}
export interface Brand {
  id: string;
  name: string;
  description: string | null;
  is_active: boolean;
  created_at: string;
}
export interface ProductCategory {
  id: string;
  name: string;
  description: string | null;
  is_active: boolean;
  /** Productos y servicios que usan la categoría. */
  product_count: number;
  created_at: string;
}
