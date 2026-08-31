import { HttpClient } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { Observable } from 'rxjs';

export interface ApiHealthResponse {
  status?: string;
  service?: string;
  version?: string;
}

@Injectable({ providedIn: 'root' })
export class ApiHealthService {
  private readonly http = inject(HttpClient);

  check(): Observable<ApiHealthResponse> {
    return this.http.get<ApiHealthResponse>('/api/health');
  }
}
