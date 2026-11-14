export interface DashboardMetrics { active_clients:number; open_opportunities:number; pipeline_value:number; weighted_pipeline_value:number; pending_activities:number; overdue_activities:number; pending_quotes:number; accepted_quotes_value:number }
export interface DashboardPipelineStage { stage:'prospecting'|'qualification'|'proposal'|'negotiation'; count:number; value:number }
export interface DashboardActivity { id:string; title:string; activity_type:'call'|'email'|'meeting'|'task'; client_name:string; scheduled_at:string; is_overdue:boolean }
export interface DashboardQuote { id:string; folio:string; client_name:string; total:number; status:'draft'|'sent'|'accepted'|'rejected'|'expired' }
export interface DashboardSummary { metrics:DashboardMetrics; pipeline:DashboardPipelineStage[]; upcoming_activities:DashboardActivity[]; recent_quotes:DashboardQuote[] }
