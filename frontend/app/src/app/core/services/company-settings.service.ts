import { HttpClient } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { CompanySettings, SaveCompanySettings } from '../models/company-settings.models';
@Injectable({ providedIn: 'root' })
export class CompanySettingsService {
  private readonly http = inject(HttpClient);
  get(): Observable<CompanySettings> {
    return this.http.get<CompanySettings>('/api/company-settings');
  }
  update(body: SaveCompanySettings): Observable<CompanySettings> {
    return this.http.patch<CompanySettings>('/api/company-settings', body);
  }
  uploadLogo(file: File): Observable<CompanySettings> {
    const body = new FormData();
    body.append('logo', file);
    return this.http.post<CompanySettings>('/api/company-settings/logo', body);
  }
  deleteLogo(): Observable<void> {
    return this.http.delete<void>('/api/company-settings/logo');
  }
}
