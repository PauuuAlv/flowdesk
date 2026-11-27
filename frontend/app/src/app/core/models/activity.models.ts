export type ActivityType = 'call' | 'email' | 'meeting' | 'task';
export type ActivityStatus = 'pending' | 'completed' | 'cancelled';
export interface ActivityReminder {
  id: string;
  minutes_before: number | null;
  fixed_at: string | null;
  remind_at: string;
  sent_at: string | null;
}
/** Exactamente uno: `minutes_before` (X tiempo antes) o `fixed_at` (fecha y hora exacta, ISO). */
export interface ActivityReminderInput {
  id: string | null;
  minutes_before?: number;
  fixed_at?: string;
}
export interface Activity {
  id: string;
  client_id: string;
  client_name: string;
  opportunity_id: string | null;
  opportunity_name: string | null;
  /** Pipeline de la oportunidad relacionada; null si la actividad no tiene oportunidad. */
  pipeline_id: string | null;
  pipeline_name: string | null;
  pipeline_color: string | null;
  owner_user_id: string;
  owner_name: string;
  activity_type: ActivityType;
  title: string;
  description: string | null;
  scheduled_at: string;
  status: ActivityStatus;
  completed_at: string | null;
  reminders: ActivityReminder[];
  created_at: string;
  updated_at: string;
}
export interface SaveActivityRequest {
  client_id: string;
  opportunity_id: string | null;
  owner_user_id: string;
  activity_type: ActivityType;
  title: string;
  description: string | null;
  scheduled_at: string;
  /** Conjunto completo de recordatorios; los que falten se eliminan. */
  reminders?: ActivityReminderInput[];
}
