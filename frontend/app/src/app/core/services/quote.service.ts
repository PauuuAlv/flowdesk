import { HttpClient } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { Quote, QuoteStatus, SaveQuoteRequest } from '../models/quote.models';
@Injectable({ providedIn: 'root' })
export class QuoteService {
  private readonly http = inject(HttpClient);
  list(): Observable<Quote[]> {
    return this.http.get<Quote[]>('/api/quotes');
  }
  get(id: string): Observable<Quote> {
    return this.http.get<Quote>(`/api/quotes/${id}`);
  }
  save(body: SaveQuoteRequest, id?: string): Observable<Quote> {
    return id
      ? this.http.patch<Quote>(`/api/quotes/${id}`, body)
      : this.http.post<Quote>('/api/quotes', body);
  }
  status(id: string, status: Exclude<QuoteStatus, 'draft' | 'expired'>): Observable<Quote> {
    return this.http.patch<Quote>(`/api/quotes/${id}/status`, { status });
  }
  pdf(id: string): Observable<Blob> {
    return this.http.get(`/api/quotes/${id}/pdf`, { responseType: 'blob' });
  }
}
