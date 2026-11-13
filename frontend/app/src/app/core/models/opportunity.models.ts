export type OpportunityStage = 'prospecting' | 'contact' | 'proposal' | 'negotiation' | 'won' | 'lost';
export interface Opportunity { id:string; client_id:string; client_name:string; owner_user_id:string; owner_name:string; name:string; amount:number; stage:OpportunityStage; probability:number; expected_close_date:string|null; notes:string|null; created_at:string; updated_at:string; }
export interface SaveOpportunityRequest { client_id:string; owner_user_id:string; name:string; amount:number; stage:OpportunityStage; probability:number; expected_close_date:string|null; notes:string|null; }
export interface OpportunityAssignee { id:string; name:string; }
