export interface Contact {
  id: string;
  client_id: string;
  full_name: string;
  job_title: string | null;
  email: string | null;
  phone: string | null;
  is_primary: boolean;
  created_at: string;
  updated_at: string;
}

export interface SaveContactRequest {
  full_name: string;
  job_title: string | null;
  email: string | null;
  phone: string | null;
  is_primary: boolean;
}
