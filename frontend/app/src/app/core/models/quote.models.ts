export type QuoteStatus = 'draft' | 'sent' | 'accepted' | 'rejected' | 'expired';
export interface QuoteItem {
  id: string;
  position: number;
  description: string;
  quantity: number;
  unit_price: number;
  amount: number;
}
export interface Quote {
  id: string;
  folio: string;
  tenant_name: string;
  client_id: string;
  client_name: string;
  client_contact: string;
  client_email: string;
  opportunity_id: string | null;
  opportunity_name: string | null;
  owner_user_id: string;
  owner_name: string;
  issue_date: string;
  valid_until: string;
  currency: string;
  discount: number;
  tax_rate: number;
  subtotal: number;
  tax: number;
  total: number;
  status: QuoteStatus;
  notes: string | null;
  items: QuoteItem[];
  created_at: string;
  updated_at: string;
}
export interface SaveQuoteRequest {
  client_id: string;
  opportunity_id: string | null;
  owner_user_id: string;
  issue_date: string;
  valid_until: string;
  discount: number;
  tax_rate: number;
  notes: string | null;
  items: Array<{ description: string; quantity: number; unit_price: number }>;
}
