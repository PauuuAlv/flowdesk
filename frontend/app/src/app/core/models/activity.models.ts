export type ActivityType='call'|'email'|'meeting'|'task';
export type ActivityStatus='pending'|'completed'|'cancelled';
export interface Activity{id:string;client_id:string;client_name:string;opportunity_id:string|null;opportunity_name:string|null;owner_user_id:string;owner_name:string;activity_type:ActivityType;title:string;description:string|null;scheduled_at:string;status:ActivityStatus;completed_at:string|null;created_at:string;updated_at:string}
export interface SaveActivityRequest{client_id:string;opportunity_id:string|null;owner_user_id:string;activity_type:ActivityType;title:string;description:string|null;scheduled_at:string}
