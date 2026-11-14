export type ProductType='product'|'service';
export type ProductUnit='piece'|'service'|'hour'|'day'|'month'|'license'|'package';
export type ProductStatus='active'|'inactive';
export interface Product{id:string;name:string;sku:string;description:string|null;category:string|null;item_type:ProductType;unit:ProductUnit;base_price:number;tax_rate:number;status:ProductStatus;created_at:string;updated_at:string}
export interface SaveProductRequest{name:string;sku:string;description:string|null;category:string|null;item_type:ProductType;unit:ProductUnit;base_price:number;tax_rate:number;status?:ProductStatus}
