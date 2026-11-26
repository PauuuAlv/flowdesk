import { HttpClient } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { Activity, ActivityReminderInput, ActivityStatus, SaveActivityRequest } from '../models/activity.models';
@Injectable({ providedIn: 'root' })
export class ActivityService {
  private readonly http = inject(HttpClient);
  list(): Observable<Activity[]> {
    return this.http.get<Activity[]>('/api/activities');
  }
  get(id: string): Observable<Activity> {
    return this.http.get<Activity>(`/api/activities/${id}`);
  }
  save(body: SaveActivityRequest, id?: string): Observable<Activity> {
    return id
      ? this.http.patch<Activity>(`/api/activities/${id}`, body)
      : this.http.post<Activity>('/api/activities', body);
  }
  /** Solo recordatorios: disponible para el responsable aunque no pueda editar la actividad. */
  updateReminders(id: string, reminders: ActivityReminderInput[]): Observable<Activity> {
    return this.http.put<Activity>(`/api/activities/${id}/reminders`, { reminders });
  }
  updateStatus(id: string, status: ActivityStatus): Observable<Activity> {
    return this.http.patch<Activity>(`/api/activities/${id}/status`, { status });
  }
}
