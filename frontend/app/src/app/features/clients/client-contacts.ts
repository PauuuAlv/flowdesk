import { Component, inject, input, OnInit, output, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';

import { Contact, SaveContactRequest } from '../../core/models/contact.models';
import { ContactService } from '../../core/services/contact.service';

/** EPIC-006: contactos de un cliente (RF-018 a RF-020). */
@Component({
  selector: 'app-client-contacts',
  imports: [ReactiveFormsModule],
  templateUrl: './client-contacts.html',
  styleUrl: './client-contacts.scss',
})
export class ClientContacts implements OnInit {
  private readonly formBuilder = inject(FormBuilder);
  private readonly contactService = inject(ContactService);

  readonly clientId = input.required<string>();
  readonly canEdit = input(false);
  /** Avisa el nombre del contacto principal para refrescar el formulario del cliente. */
  readonly primaryChanged = output<string>();

  protected readonly contacts = signal<Contact[]>([]);
  protected readonly loading = signal(true);
  protected readonly saving = signal(false);
  protected readonly errorMessage = signal('');
  protected readonly editing = signal<Contact | 'new' | null>(null);
  protected readonly contactToDelete = signal<Contact | null>(null);

  protected readonly form = this.formBuilder.nonNullable.group({
    full_name: ['', [Validators.required, Validators.minLength(2), Validators.maxLength(120)]],
    job_title: ['', [Validators.maxLength(120)]],
    email: ['', [Validators.email, Validators.maxLength(255)]],
    phone: ['', [Validators.maxLength(30), Validators.pattern(/^[0-9+()\-\s.]*$/)]],
    is_primary: [false],
  });

  ngOnInit(): void {
    this.load();
  }

  protected startCreate(): void {
    this.form.reset({ full_name: '', job_title: '', email: '', phone: '', is_primary: false });
    this.errorMessage.set('');
    this.editing.set('new');
  }

  protected startEdit(contact: Contact): void {
    this.form.reset({
      full_name: contact.full_name,
      job_title: contact.job_title ?? '',
      email: contact.email ?? '',
      phone: contact.phone ?? '',
      is_primary: contact.is_primary,
    });
    this.errorMessage.set('');
    this.editing.set(contact);
  }

  protected cancelEdit(): void {
    this.editing.set(null);
  }

  protected submit(): void {
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }
    const value = this.form.getRawValue();
    const request: SaveContactRequest = {
      full_name: value.full_name.trim(),
      job_title: value.job_title.trim() || null,
      email: value.email.trim().toLowerCase() || null,
      phone: value.phone.trim() || null,
      is_primary: value.is_primary,
    };
    const current = this.editing();
    const contactId = current && current !== 'new' ? current.id : undefined;
    this.saving.set(true);
    this.errorMessage.set('');
    this.contactService.save(this.clientId(), request, contactId).subscribe({
      next: () => {
        this.saving.set(false);
        this.editing.set(null);
        this.load();
      },
      error: () => {
        this.saving.set(false);
        this.errorMessage.set('No fue posible guardar el contacto. Intenta nuevamente.');
      },
    });
  }

  protected makePrimary(contact: Contact): void {
    this.saving.set(true);
    this.contactService.setPrimary(this.clientId(), contact.id).subscribe({
      next: () => {
        this.saving.set(false);
        this.load();
      },
      error: () => {
        this.saving.set(false);
        this.errorMessage.set('No fue posible marcar el contacto como principal.');
      },
    });
  }

  protected confirmDelete(): void {
    const contact = this.contactToDelete();
    if (!contact) return;
    this.saving.set(true);
    this.contactService.delete(this.clientId(), contact.id).subscribe({
      next: () => {
        this.saving.set(false);
        this.contactToDelete.set(null);
        this.load();
      },
      error: () => {
        this.saving.set(false);
        this.contactToDelete.set(null);
        this.errorMessage.set('No fue posible eliminar el contacto.');
      },
    });
  }

  private load(): void {
    this.loading.set(true);
    this.contactService.list(this.clientId()).subscribe({
      next: (contacts) => {
        this.contacts.set(contacts);
        this.loading.set(false);
        const primary = contacts.find((item) => item.is_primary);
        if (primary) this.primaryChanged.emit(primary.full_name);
      },
      error: () => {
        this.loading.set(false);
        this.errorMessage.set('No fue posible cargar los contactos.');
      },
    });
  }
}
