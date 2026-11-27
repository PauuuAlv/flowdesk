import { HttpClient, HttpErrorResponse, HttpResponse } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { catchError, map, Observable, throwError } from 'rxjs';
import { PERMISSIONS, PermissionCode } from '../models/permission.models';

/** Módulos que se pueden exportar e importar en CSV ('all' = toda la empresa en ZIP). */
export type DataEntity =
  | 'units'
  | 'brands'
  | 'categories'
  | 'products'
  | 'services'
  | 'clients'
  | 'pipelines'
  | 'opportunities'
  | 'activities'
  | 'quotes';

export interface DataEntityInfo {
  key: DataEntity;
  label: string;
  /** Permiso para exportar y permisos adicionales para importar (igual que el backend). */
  view: PermissionCode;
  import: PermissionCode[];
  hint: string;
}

export const DATA_ENTITIES: DataEntityInfo[] = [
  { key: 'units', label: 'Unidades de medida', view: PERMISSIONS.productsView, import: [PERMISSIONS.productsUpdate],
    hint: 'Se identifican por su clave; si no la indicas se genera a partir del nombre.' },
  { key: 'brands', label: 'Marcas', view: PERMISSIONS.productsView, import: [PERMISSIONS.productsUpdate],
    hint: 'Se identifican por su nombre.' },
  { key: 'categories', label: 'Categorías', view: PERMISSIONS.productsView, import: [PERMISSIONS.productsUpdate],
    hint: 'Se identifican por su nombre.' },
  { key: 'products', label: 'Productos', view: PERMISSIONS.productsView,
    import: [PERMISSIONS.productsCreate, PERMISSIONS.productsUpdate],
    hint: 'Se identifican por su código. La unidad debe existir; las marcas y categorías nuevas se crean solas.' },
  { key: 'services', label: 'Servicios', view: PERMISSIONS.productsView,
    import: [PERMISSIONS.productsCreate, PERMISSIONS.productsUpdate],
    hint: 'Se identifican por su código. La unidad debe existir; las marcas y categorías nuevas se crean solas.' },
  { key: 'clients', label: 'Clientes', view: PERMISSIONS.clientsView,
    import: [PERMISSIONS.clientsCreate, PERMISSIONS.clientsUpdate], hint: 'Se identifican por su correo.' },
  { key: 'pipelines', label: 'Pipelines y etapas', view: PERMISSIONS.opportunitiesView,
    import: [PERMISSIONS.opportunitiesUpdate],
    hint: 'Una fila por etapa. Un pipeline nuevo necesita al menos una etapa normal, una Ganada y una Perdida.' },
  { key: 'opportunities', label: 'Oportunidades', view: PERMISSIONS.opportunitiesView,
    import: [PERMISSIONS.opportunitiesCreate, PERMISSIONS.opportunitiesUpdate],
    hint: 'Con ID se actualizan; sin ID se crean. El cliente se indica por su correo.' },
  { key: 'activities', label: 'Actividades', view: PERMISSIONS.activitiesView,
    import: [PERMISSIONS.activitiesCreate, PERMISSIONS.activitiesUpdate],
    hint: 'Con ID se actualizan; sin ID se crean. Las fechas usan el formato AAAA-MM-DD HH:MM.' },
  { key: 'quotes', label: 'Cotizaciones', view: PERMISSIONS.quotesView,
    import: [PERMISSIONS.quotesCreate, PERMISSIONS.quotesUpdate],
    hint: 'Una fila por partida; las filas con el mismo folio forman una cotización. Los totales se recalculan.' },
];

export interface ImportResult {
  applied: boolean;
  created: number;
  updated: number;
  entities: { entity: string; label: string; rows: number; created: number; updated: number }[];
  errors: { file: string; row: number; message: string }[];
  error_count: number;
}

@Injectable({ providedIn: 'root' })
export class DataTransferService {
  private readonly http = inject(HttpClient);

  private base(entity: DataEntity | 'all') {
    return entity === 'all' ? '/api/data-transfer' : `/api/data-transfer/${entity}`;
  }

  /** Descarga el CSV (o el ZIP de toda la empresa). */
  export(entity: DataEntity | 'all'): Observable<void> {
    return this.download(`${this.base(entity)}/export`, entity === 'all' ? 'flowdesk.zip' : `${entity}.csv`);
  }

  template(entity: DataEntity): Observable<void> {
    return this.download(`${this.base(entity)}/template`, `${entity}_plantilla.csv`);
  }

  import(entity: DataEntity | 'all', file: File): Observable<ImportResult> {
    const body = new FormData();
    body.append('file', file);
    return this.http.post<ImportResult>(`${this.base(entity)}/import`, body).pipe(
      catchError((error: HttpErrorResponse) => {
        const detail = error.error?.detail;
        const message =
          typeof detail?.message === 'string'
            ? detail.message
            : error.status === 413
              ? 'El archivo es demasiado grande.'
              : error.status === 403
                ? 'No tienes permiso para importar esta información.'
                : 'No fue posible importar el archivo.';
        return throwError(() => new Error(message));
      }),
    );
  }

  private download(url: string, fallbackName: string): Observable<void> {
    return this.http.get(url, { observe: 'response', responseType: 'blob' }).pipe(
      map((response: HttpResponse<Blob>) => {
        const header = response.headers.get('Content-Disposition') ?? '';
        const name = /filename="?([^"]+)"?/.exec(header)?.[1] ?? fallbackName;
        const link = document.createElement('a');
        link.href = URL.createObjectURL(response.body as Blob);
        link.download = name;
        link.click();
        setTimeout(() => URL.revokeObjectURL(link.href), 1000);
      }),
    );
  }
}
