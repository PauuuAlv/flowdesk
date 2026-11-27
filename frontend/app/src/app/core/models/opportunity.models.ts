export type OpportunityStage = string;
export type OpportunityStageType = 'normal' | 'won' | 'lost';
/** Pipeline (embudo) de ventas: cada uno tiene sus propias etapas. */
export interface Pipeline {
  id: string;
  name: string;
  description: string | null;
  position: number;
  is_default: boolean;
  is_active: boolean;
  /** Color (#rrggbb) de sus actividades en el calendario. */
  color: string;
  stage_count: number;
  open_opportunities: number;
  total_opportunities: number;
  created_at: string;
}
export interface SavePipelineRequest {
  name: string;
  description: string | null;
  /** Solo al crear: copia las etapas de otro pipeline (sin él, etapas predeterminadas). */
  copy_stages_from?: string | null;
  /** Sin indicarlo se conserva (al editar) o se asigna uno de la paleta (al crear). */
  color?: string;
  is_active?: boolean;
  is_default?: boolean;
}
export interface OpportunityStageCatalog {
  id: string;
  pipeline_id: string;
  key: string;
  name: string;
  stage_type: OpportunityStageType;
  default_probability: number;
  position: number;
  /** Color base #rrggbb: el tablero usa un tono suave como fondo de la columna. */
  color: string;
  is_active: boolean;
  created_at: string;
}
export interface SaveOpportunityStageRequest {
  pipeline_id: string;
  name: string;
  stage_type: OpportunityStageType;
  default_probability: number;
  position: number;
  color?: string;
  is_active?: boolean;
}
export type LossReason =
  | 'price'
  | 'no_response'
  | 'competitor'
  | 'budget_cancelled'
  | 'not_qualified'
  | 'other';
export interface Opportunity {
  id: string;
  pipeline_id: string;
  pipeline_name: string;
  client_id: string;
  client_name: string;
  owner_user_id: string;
  owner_name: string;
  name: string;
  amount: number;
  currency: string;
  stage: OpportunityStage;
  probability: number;
  expected_close_date: string | null;
  notes: string | null;
  loss_reason: LossReason | null;
  loss_detail: string | null;
  archived: boolean;
  closed_at: string | null;
  created_at: string;
  updated_at: string;
}
export interface SaveOpportunityRequest {
  client_id: string;
  /** Sin indicarlo, el backend usa el pipeline predeterminado. */
  pipeline_id?: string;
  owner_user_id: string;
  name: string;
  amount: number;
  /** Sin indicarla, el backend usa la moneda de la empresa. */
  currency?: string;
  stage: OpportunityStage;
  probability: number;
  expected_close_date: string | null;
  notes: string | null;
}
export interface OpportunityAssignee {
  id: string;
  name: string;
}
export interface OpportunityStageHistory {
  id: string;
  from_stage_key: string | null;
  to_stage_key: string;
  from_stage_name: string | null;
  to_stage_name: string;
  probability: number;
  expected_close_date: string | null;
  note: string | null;
  changed_by_user_id: string;
  changed_by_name: string;
  created_at: string;
}
