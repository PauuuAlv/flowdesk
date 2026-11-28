import { Component, computed, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';

import { Client, ClientStatus } from '../../core/models/client.models';
import { PERMISSIONS } from '../../core/models/permission.models';
import { ClientService } from '../../core/services/client.service';
import { SessionService } from '../../core/services/session.service';

import { MultiSelect } from '../../shared/ui/multi-select/multi-select';
import { DataTransfer } from '../../shared/ui/data-transfer/data-transfer';

@Component({
  selector: 'app-client-list-page',
  imports: [RouterLink, DataTransfer, MultiSelect],
  templateUrl: './client-list-page.html',
  styleUrl: './client-list-page.scss',
})
export class ClientListPage {
  private readonly clientService = inject(ClientService);
  private readonly user = inject(SessionService).getUser();

  protected readonly clients = signal<Client[]>([]);
  protected readonly loading = signal(true);
  protected readonly processing = signal(false);
  protected readonly errorMessage = signal('');
  protected readonly successMessage = signal('');
  protected readonly search = signal('');
  protected readonly statusFilter = signal<ClientStatus[]>([]); // vacío = todos
  protected readonly clientToToggle = signal<Client | null>(null);

  protected readonly canCreate = this.hasPermission(PERMISSIONS.clientsCreate);
  protected readonly canUpdate = this.hasPermission(PERMISSIONS.clientsUpdate);
  protected readonly canDelete = this.hasPermission(PERMISSIONS.clientsDelete);

  protected readonly filteredClients = computed(() => {
    const term = this.search().trim().toLowerCase();
    const status = this.statusFilter();
    return this.clients().filter((client) => {
      const content = `${client.company_name} ${client.contact_name} ${client.email}`.toLowerCase();
      return (!term || content.includes(term)) && (!status.length || status.includes(client.status));
    });
  });

  constructor() {
    this.load();
  }

  protected load(): void {
    this.loading.set(true);
    this.errorMessage.set('');
    this.clientService.list().subscribe({
      next: (clients) => {
        this.clients.set(clients);
        this.loading.set(false);
      },
      error: () => {
        this.loading.set(false);
        this.errorMessage.set('No fue posible consultar los clientes. Intenta nuevamente.');
      },
    });
  }

  protected updateSearch(event: Event): void {
    this.search.set((event.target as HTMLInputElement).value);
  }

  protected updateStatusFilter(values: string[]): void {
    this.statusFilter.set(values as ClientStatus[]);
  }

  protected requestStatusChange(client: Client): void {
    this.clientToToggle.set(client);
  }

  protected cancelStatusChange(): void {
    this.clientToToggle.set(null);
  }

  protected confirmStatusChange(): void {
    const client = this.clientToToggle();
    if (!client) return;
    const newStatus: ClientStatus = client.status === 'active' ? 'inactive' : 'active';
    this.processing.set(true);
    this.errorMessage.set('');
    this.clientService.updateStatus(client.id, newStatus).subscribe({
      next: (updated) => {
        this.processing.set(false);
        this.clientToToggle.set(null);
        this.clients.update((clients) =>
          clients.map((item) => (item.id === updated.id ? updated : item)),
        );
        this.successMessage.set(
          `${updated.company_name} quedó ${updated.status === 'active' ? 'activo' : 'inactivo'}.`,
        );
      },
      error: () => {
        this.processing.set(false);
        this.clientToToggle.set(null);
        this.errorMessage.set('No fue posible cambiar el estado del cliente.');
      },
    });
  }

  protected initials(client: Client): string {
    return client.company_name
      .split(/\s+/)
      .slice(0, 2)
      .map((part) => part.charAt(0).toUpperCase())
      .join('');
  }

  private hasPermission(permission: (typeof PERMISSIONS)[keyof typeof PERMISSIONS]): boolean {
    return Boolean(this.user?.permissions?.includes(permission));
  }
}
