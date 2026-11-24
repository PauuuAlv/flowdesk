import { MoneyTotal } from './currency.models';

export interface DashboardMetrics {
  /** Moneda de la empresa: siempre es el primer total de cada lista. */
  currency: string;
  active_clients: number;
  open_opportunities: number;
  pipeline_value: MoneyTotal[];
  weighted_pipeline_value: MoneyTotal[];
  pending_activities: number;
  overdue_activities: number;
  pending_quotes: number;
  accepted_quotes_value: MoneyTotal[];
}
export interface DashboardPipelineStage {
  pipeline_id: string;
  pipeline_name: string;
  stage: string;
  stage_name: string;
  color: string;
  count: number;
  value: MoneyTotal[];
}
export interface DashboardActivity {
  id: string;
  title: string;
  activity_type: 'call' | 'email' | 'meeting' | 'task';
  client_name: string;
  scheduled_at: string;
  is_overdue: boolean;
}
export interface DashboardQuote {
  id: string;
  folio: string;
  client_name: string;
  total: number;
  currency: string;
  status: 'draft' | 'sent' | 'accepted' | 'rejected' | 'expired';
}
export interface DashboardSummary {
  metrics: DashboardMetrics;
  pipeline: DashboardPipelineStage[];
  upcoming_activities: DashboardActivity[];
  recent_quotes: DashboardQuote[];
}
