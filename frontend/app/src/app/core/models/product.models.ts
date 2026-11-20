export type ProductType = 'product' | 'service';
export type ProductUnit = string;
export type ProductStatus = 'active' | 'inactive';
export interface Product {
  id: string;
  name: string;
  sku: string;
  description: string | null;
  category: string | null;
  item_type: ProductType;
  unit: ProductUnit;
  unit_id: string;
  unit_name: string;
  unit_abbreviation: string;
  brand_id: string | null;
  brand_name: string | null;
  base_price: number;
  tax_rate: number;
  status: ProductStatus;
  created_at: string;
  updated_at: string;
}
export interface SaveProductRequest {
  name: string;
  sku?: string;
  description: string | null;
  category: string | null;
  item_type: ProductType;
  unit_id: string;
  brand_id: string | null;
  base_price: number;
  tax_rate: number;
  status?: ProductStatus;
}
export interface MeasurementUnit {
  id: string;
  key: string;
  name: string;
  abbreviation: string;
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
