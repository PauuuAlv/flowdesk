import { Component, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';

import { ClientStatus, SaveClientRequest } from '../../core/models/client.models';
import { ClientService } from '../../core/services/client.service';

@Component({
  selector: 'app-client-form-page',
  imports: [ReactiveFormsModule, RouterLink],
  templateUrl: './client-form-page.html',
  styleUrl: './client-form-page.scss'
})
export class ClientFormPage {
  private readonly formBuilder = inject(FormBuilder);
  private readonly clientService = inject(ClientService);
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);

  protected readonly clientId = this.route.snapshot.paramMap.get('clientId');
  protected readonly loading = signal(Boolean(this.clientId));
  protected readonly saving = signal(false);
  protected readonly errorMessage = signal('');

  protected readonly form = this.formBuilder.nonNullable.group({
    company_name: ['', [Validators.required, Validators.minLength(2), Validators.maxLength(120)]],
    contact_name: ['', [Validators.required, Validators.minLength(2), Validators.maxLength(120)]],
    email: ['', [Validators.required, Validators.email, Validators.maxLength(255)]],
    phone: ['', [Validators.maxLength(30), Validators.pattern(/^[0-9+()\-\s.]*$/)]],
    notes: ['', [Validators.maxLength(1000)]],
    status: ['active' as ClientStatus, Validators.required]
  });

  constructor() {
    if (this.clientId) this.loadClient(this.clientId);
  }

  protected submit(): void {
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }
    const value = this.form.getRawValue();
    const request: SaveClientRequest = {
      company_name: value.company_name.trim(),
      contact_name: value.contact_name.trim(),
      email: value.email.trim().toLowerCase(),
      phone: value.phone.trim() || null,
      notes: value.notes.trim() || null,
      ...(this.clientId ? { status: value.status } : {})
    };
    this.saving.set(true);
    this.errorMessage.set('');
    this.clientService.save(request, this.clientId ?? undefined).subscribe({
      next: () => void this.router.navigate(['/panel/clientes']),
      error: (error: Error) => {
        this.saving.set(false);
        this.errorMessage.set(
          error.message === 'DUPLICATE_EMAIL'
            ? 'Ya existe un cliente con ese correo en tu empresa.'
            : 'No fue posible guardar el cliente. Intenta nuevamente.'
        );
      }
    });
  }

  private loadClient(clientId: string): void {
    this.clientService.get(clientId).subscribe({
      next: (client) => {
        this.form.setValue({
          company_name: client.company_name,
          contact_name: client.contact_name,
          email: client.email,
          phone: client.phone ?? '',
          notes: client.notes ?? '',
          status: client.status
        });
        this.loading.set(false);
      },
      error: () => {
        this.loading.set(false);
        this.errorMessage.set('No fue posible cargar la información del cliente.');
      }
    });
  }
}
