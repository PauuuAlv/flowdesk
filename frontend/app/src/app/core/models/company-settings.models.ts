export interface CompanySettings {
  id:string; slug:string; name:string; legal_name:string|null; tax_id:string|null;
  contact_email:string|null; contact_phone:string|null; website:string|null; logo_url:string|null;
  address_line:string|null; city:string|null; state:string|null; postal_code:string|null;
  country:string; currency:string; default_tax_rate:number; quote_validity_days:number;
  quote_prefix:string; payment_instructions:string|null;
}

export type SaveCompanySettings = Omit<CompanySettings,'id'|'slug'>;
