import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { catchError, Observable, throwError } from 'rxjs';

import { Client, ClientStatus, SaveClientRequest } from '../models/client.models';

@Injectable({ providedIn: 'root' })
export class ClientService {
  private readonly http = inject(HttpClient);

  list(): Observable<Client[]> {
    return this.http.get<Client[]>('/api/clients');
  }

  get(clientId: string): Observable<Client> {
    return this.http.get<Client>(`/api/clients/${clientId}`);
  }

  save(request: SaveClientRequest, clientId?: string): Observable<Client> {
    const response = clientId
      ? this.http.patch<Client>(`/api/clients/${clientId}`, request)
      : this.http.post<Client>('/api/clients', request);
    return response.pipe(
      catchError((error: HttpErrorResponse) =>
        throwError(() => new Error(error.status === 409 ? 'DUPLICATE_EMAIL' : 'SAVE_FAILED'))
      )
    );
  }

  updateStatus(clientId: string, status: ClientStatus): Observable<Client> {
    return this.http.patch<Client>(`/api/clients/${clientId}/status`, { status });
  }
}
