import { Component, computed, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { Quote, QuoteItem, QuoteStatus } from '../../core/models/quote.models';
import { PERMISSIONS } from '../../core/models/permission.models';
import { QuoteService } from '../../core/services/quote.service';
import { SessionService } from '../../core/services/session.service';

import { ComboOption } from '../../shared/ui/combobox/combobox';
import { MultiSelect } from '../../shared/ui/multi-select/multi-select';
import { formatMoney } from '../../core/models/currency.models';
import { DataTransfer } from '../../shared/ui/data-transfer/data-transfer';

/** Valor de filtro para las cotizaciones sin oportunidad. */
const NONE = '__none__';

/**
 * Clave de un concepto: el producto/servicio del catálogo si la partida viene
 * de él; si es una partida libre, su descripción (sin mayúsculas ni espacios
 * extra) para agrupar las que se escribieron igual.
 */
function conceptKey(item: QuoteItem): string {
  return item.product_id ? `p:${item.product_id}` : `d:${item.description.trim().toLowerCase().replace(/\s+/g, ' ')}`;
}

function sortedOptions(map: Map<string, string>): ComboOption[] {
  return [...map]
    .map(([value, label]) => ({ value, label }))
    .sort((a, b) =>
      a.value === NONE ? 1 : b.value === NONE ? -1 : a.label.localeCompare(b.label, 'es', { sensitivity: 'base' }),
    );
}

@Component({
  selector: 'app-quote-list-page',
  imports: [RouterLink, DataTransfer, MultiSelect],
  templateUrl: './quote-list-page.html',
  styleUrl: './quote-list-page.scss',
})
export class QuoteListPage {
  private s = inject(QuoteService);
  private u = inject(SessionService).getUser();
  items = signal<Quote[]>([]);
  loading = signal(true);
  error = signal('');
  search = signal('');
  // Cada filtro admite varios valores; vacío = todos.
  filter = signal<QuoteStatus[]>([]);
  opportunities = signal<string[]>([]);
  owners = signal<string[]>([]);
  concepts = signal<string[]>([]);
  statusOptions: ComboOption[] = [
    { value: 'draft', label: 'Borradores' },
    { value: 'sent', label: 'Enviadas' },
    { value: 'accepted', label: 'Aceptadas' },
    { value: 'rejected', label: 'Rechazadas' },
    { value: 'expired', label: 'Vencidas' },
  ];
  // Opciones tomadas de las cotizaciones registradas.
  opportunityOptions = computed(() => {
    const map = new Map<string, string>();
    for (const x of this.items()) {
      if (x.opportunity_id) map.set(x.opportunity_id, x.opportunity_name ?? 'Oportunidad');
      else map.set(NONE, 'Sin oportunidad');
    }
    return sortedOptions(map);
  });
  ownerOptions = computed(() => {
    const map = new Map<string, string>();
    for (const x of this.items()) map.set(x.owner_user_id, x.owner_name);
    return sortedOptions(map);
  });
  conceptOptions = computed(() => {
    const map = new Map<string, string>();
    for (const x of this.items()) {
      for (const item of x.items) {
        const key = conceptKey(item);
        if (!map.has(key)) map.set(key, item.description.trim());
      }
    }
    return sortedOptions(map);
  });
  hasFilters = computed(
    () =>
      Boolean(this.search().trim()) ||
      [this.filter(), this.opportunities(), this.owners(), this.concepts()].some((v) => v.length > 0),
  );
  canCreate = this.has(PERMISSIONS.quotesCreate);
  canUpdate = this.has(PERMISSIONS.quotesUpdate);
  canStatus = this.has(PERMISSIONS.quotesStatus);
  visible = computed(() => {
    const q = this.search().trim().toLowerCase();
    const opportunities = this.opportunities();
    const owners = this.owners();
    const concepts = new Set(this.concepts());
    return this.items().filter(
      (x) =>
        (!this.filter().length || this.filter().includes(x.status)) &&
        (!opportunities.length || opportunities.includes(x.opportunity_id ?? NONE)) &&
        (!owners.length || owners.includes(x.owner_user_id)) &&
        // Basta con que la cotización incluya alguno de los conceptos elegidos.
        (!concepts.size || x.items.some((item) => concepts.has(conceptKey(item)))) &&
        (!q ||
          `${x.folio} ${x.client_name} ${x.opportunity_name ?? ''} ${x.owner_name}`.toLowerCase().includes(q)),
    );
  });
  constructor() {
    this.load();
  }
  protected load() {
    this.s.list().subscribe({
      next: (x) => {
        this.items.set(x);
        this.loading.set(false);
      },
      error: () => {
        this.error.set('No fue posible consultar las cotizaciones.');
        this.loading.set(false);
      },
    });
  }
  setSearch(e: Event) {
    this.search.set((e.target as HTMLInputElement).value);
  }
  setFilter(values: string[]) {
    this.filter.set(values as QuoteStatus[]);
  }
  clearFilters() {
    this.search.set('');
    this.filter.set([]);
    this.opportunities.set([]);
    this.owners.set([]);
    this.concepts.set([]);
  }
  // --- Envío por correo ---
  sending = signal<Quote | null>(null);
  sendMessage = signal('');
  sendBusy = signal(false);
  sendError = signal('');
  sentNotice = signal('');
  openSend(x: Quote) {
    this.sending.set(x);
    this.sendMessage.set('');
    this.sendError.set('');
    this.sentNotice.set('');
  }
  closeSend() {
    if (!this.sendBusy()) this.sending.set(null);
  }
  confirmSend() {
    const quote = this.sending();
    if (!quote || this.sendBusy()) return;
    this.sendBusy.set(true);
    this.sendError.set('');
    this.s.send(quote.id, this.sendMessage().trim() || null).subscribe({
      next: (v) => {
        this.items.update((all) => all.map((i) => (i.id === v.id ? v : i)));
        this.sendBusy.set(false);
        this.sending.set(null);
        this.sentNotice.set(`Cotización ${v.folio} enviada a ${v.client_email}.`);
      },
      error: (err) => {
        this.sendBusy.set(false);
        this.sendError.set(
          err?.status === 422
            ? 'El cliente no tiene un correo registrado.'
            : 'No fue posible enviar el correo. Revisa la configuración de correo e inténtalo de nuevo.',
        );
      },
    });
  }
  change(x: Quote, status: 'sent' | 'accepted' | 'rejected') {
    this.s
      .status(x.id, status)
      .subscribe({
        next: (v) => this.items.update((all) => all.map((i) => (i.id === v.id ? v : i))),
        error: () => this.error.set('No fue posible cambiar el estado.'),
      });
  }
  money(v: number, currency: string) {
    return formatMoney(v, currency);
  }
  label(s: QuoteStatus) {
    return {
      draft: 'Borrador',
      sent: 'Enviada',
      accepted: 'Aceptada',
      rejected: 'Rechazada',
      expired: 'Vencida',
    }[s];
  }
  private has(p: any) {
    return this.u?.permissions?.includes(p);
  }
}
