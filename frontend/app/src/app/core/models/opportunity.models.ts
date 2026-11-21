export type OpportunityStage = string;
export type OpportunityStageType = 'normal' | 'won' | 'lost';
export interface OpportunityStageCatalog {
  id: string;
  key: string;
  name: string;
  stage_type: OpportunityStageType;
  default_probability: number;
  position: number;
  is_active: boolean;
  created_at: string;
}
export interface SaveOpportunityStageRequest {
  name: string;
  stage_type: OpportunityStageType;
  default_probability: number;
  position: number;
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
  client_id: string;
  client_name: string;
  owner_user_id: string;
  owner_name: string;
  name: string;
  amount: number;
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
  owner_user_id: string;
  name: string;
  amount: number;
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
