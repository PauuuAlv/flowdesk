export type AuditOperation = 'CREATE' | 'UPDATE' | 'DELETE' | 'EVENT';
export type AuditActorType = 'user' | 'platform_admin' | 'system' | 'anonymous';
/** `tenant`: auditoría de la empresa. `platform`: administración de Flowdesk. */
export type AuditScope = 'tenant' | 'platform';

export interface AuditEntry {
  id: string;
  created_at: string;
  operation: AuditOperation;
  action: string;
  description: string;
  entity: string | null;
  entity_label: string | null;
  entity_id: string | null;
  actor_type: AuditActorType;
  actor_id: string | null;
  actor_email: string | null;
  ip_address: string | null;
  user_agent: string | null;
  http_method: string | null;
  endpoint: string | null;
  before_data: Record<string, unknown> | null;
  after_data: Record<string, unknown> | null;
  details: Record<string, unknown>;
  tenant_id: string | null;
  tenant_name: string | null;
}

export interface AuditPage {
  items: AuditEntry[];
  total: number;
  page: number;
  page_size: number;
}

export interface AuditFilterOption {
  value: string;
  label: string;
}

export interface AuditFilters {
  entities: AuditFilterOption[];
  actors: AuditFilterOption[];
}

export interface AuditQuery {
  page: number;
  page_size: number;
  /** Vacío = todas. Cada filtro admite varios valores. */
  operations?: AuditOperation[];
  entities?: string[];
  actor_ids?: string[];
  search?: string;
  /** ISO 8601 (ya convertido desde la fecha local). */
  date_from?: string;
  date_to?: string;
}
