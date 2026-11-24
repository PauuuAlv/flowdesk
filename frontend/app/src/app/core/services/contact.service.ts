import { HttpClient } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { Observable } from 'rxjs';

import { Contact, SaveContactRequest } from '../models/contact.models';

@Injectable({ providedIn: 'root' })
export class ContactService {
  private readonly http = inject(HttpClient);

  private base(clientId: string): string {
    return `/api/clients/${clientId}/contacts`;
  }

  list(clientId: string): Observable<Contact[]> {
    return this.http.get<Contact[]>(this.base(clientId));
  }

  save(clientId: string, request: SaveContactRequest, contactId?: string): Observable<Contact> {
    return contactId
      ? this.http.patch<Contact>(`${this.base(clientId)}/${contactId}`, request)
      : this.http.post<Contact>(this.base(clientId), request);
  }

  setPrimary(clientId: string, contactId: string): Observable<Contact> {
    return this.http.post<Contact>(`${this.base(clientId)}/${contactId}/primary`, {});
  }

  delete(clientId: string, contactId: string): Observable<void> {
    return this.http.delete<void>(`${this.base(clientId)}/${contactId}`);
  }
}
