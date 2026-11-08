export type ClientStatus = 'active' | 'inactive';

export interface Client {
  id: string;
  company_name: string;
  contact_name: string;
  email: string;
  phone: string | null;
  status: ClientStatus;
  notes: string | null;
  created_at: string;
  updated_at: string;
}

export interface SaveClientRequest {
  company_name: string;
  contact_name: string;
  email: string;
  phone: string | null;
  notes: string | null;
  status?: ClientStatus;
}
