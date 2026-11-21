import { HttpClient } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { Observable } from 'rxjs';

import { FlowdeskNotification, NotificationListResponse } from '../models/notification.models';

@Injectable({ providedIn: 'root' })
export class NotificationService {
  private readonly http = inject(HttpClient);

  list(): Observable<NotificationListResponse> {
    return this.http.get<NotificationListResponse>('/api/notifications');
  }

  markRead(id: string): Observable<FlowdeskNotification> {
    return this.http.patch<FlowdeskNotification>(`/api/notifications/${id}/read`, {});
  }

  markAllRead(): Observable<void> {
    return this.http.post<void>('/api/notifications/read-all', {});
  }
}
