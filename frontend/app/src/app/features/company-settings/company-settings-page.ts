import { Component, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { PERMISSIONS } from '../../core/models/permission.models';
import { CompanySettingsService } from '../../core/services/company-settings.service';
import { SessionService } from '../../core/services/session.service';
@Component({
  selector: 'app-company-settings-page',
  imports: [ReactiveFormsModule],
  templateUrl: './company-settings-page.html',
  styleUrl: './company-settings-page.scss',
})
export class CompanySettingsPage {
  private readonly fb = inject(FormBuilder);
  private readonly service = inject(CompanySettingsService);
  private readonly session = inject(SessionService);
  protected readonly loading = signal(true);
  protected readonly saving = signal(false);
  protected readonly error = signal('');
  protected readonly success = signal('');
  protected readonly logoUrl = signal<string | null>(null);
  protected readonly uploadingLogo = signal(false);
  protected slug = '';
  protected readonly canUpdate =
    this.session.getUser()?.role === 'admin' ||
    Boolean(this.session.getUser()?.permissions?.includes(PERMISSIONS.settingsUpdate));
  protected readonly form = this.fb.nonNullable.group({
    name: ['', [Validators.required, Validators.minLength(2), Validators.maxLength(255)]],
    legal_name: ['', Validators.maxLength(255)],
    tax_id: ['', [Validators.maxLength(20), Validators.pattern(/^[A-Za-z0-9&Ññ-]*$/)]],
    contact_email: ['', [Validators.email, Validators.maxLength(255)]],
    contact_phone: ['', Validators.maxLength(30)],
    website: ['', Validators.maxLength(255)],
    logo_url: ['', Validators.maxLength(500)],
    address_line: ['', Validators.maxLength(255)],
    city: ['', Validators.maxLength(100)],
    state: ['', Validators.maxLength(100)],
    postal_code: ['', Validators.maxLength(12)],
    country: ['México', [Validators.required, Validators.minLength(2), Validators.maxLength(80)]],
    currency: ['MXN', [Validators.required, Validators.pattern(/^[A-Za-z]{3}$/)]],
    default_tax_rate: [16, [Validators.required, Validators.min(0), Validators.max(100)]],
    quote_validity_days: [15, [Validators.required, Validators.min(1), Validators.max(365)]],
    quote_prefix: [
      'COT',
      [Validators.required, Validators.pattern(/^[A-Za-z0-9-]+$/), Validators.maxLength(12)],
    ],
    payment_instructions: ['', Validators.maxLength(1500)],
  });
  constructor() {
    this.service.get().subscribe({
      next: (x) => {
        this.slug = x.slug;
        this.logoUrl.set(x.logo_url);
        this.form.setValue({
          name: x.name,
          legal_name: x.legal_name ?? '',
          tax_id: x.tax_id ?? '',
          contact_email: x.contact_email ?? '',
          contact_phone: x.contact_phone ?? '',
          website: x.website ?? '',
          logo_url: x.logo_url ?? '',
          address_line: x.address_line ?? '',
          city: x.city ?? '',
          state: x.state ?? '',
          postal_code: x.postal_code ?? '',
          country: x.country,
          currency: x.currency,
          default_tax_rate: Number(x.default_tax_rate),
          quote_validity_days: x.quote_validity_days,
          quote_prefix: x.quote_prefix,
          payment_instructions: x.payment_instructions ?? '',
        });
        if (!this.canUpdate) this.form.disable();
        this.loading.set(false);
      },
      error: () => {
        this.error.set('No fue posible cargar la configuración de la empresa.');
        this.loading.set(false);
      },
    });
  }
  protected selectLogo(event: Event) {
    if (!this.canUpdate) return;
    const input = event.target as HTMLInputElement;
    const file = input.files?.[0];
    input.value = '';
    if (!file) return;
    if (!['image/jpeg', 'image/png', 'image/webp'].includes(file.type)) {
      this.error.set('Selecciona una imagen JPG, PNG o WebP.');
      return;
    }
    if (file.size > 5 * 1024 * 1024) {
      this.error.set('El logotipo no puede superar 5 MB.');
      return;
    }
    this.uploadingLogo.set(true); this.error.set(''); this.success.set('');
    this.service.uploadLogo(file).subscribe({
      next: (company) => {
        this.uploadingLogo.set(false); this.logoUrl.set(company.logo_url);
        this.form.controls.logo_url.setValue(company.logo_url ?? '');
        this.updateSessionLogo(company.logo_url);
        this.success.set('El logotipo se actualizó correctamente.');
      },
      error: () => { this.uploadingLogo.set(false); this.error.set('No fue posible cargar el logotipo. Verifica el formato y tamaño.'); },
    });
  }
  protected removeLogo() {
    if (!this.canUpdate || !this.logoUrl()) return;
    this.uploadingLogo.set(true); this.error.set(''); this.success.set('');
    this.service.deleteLogo().subscribe({
      next: () => {
        this.uploadingLogo.set(false); this.logoUrl.set(null); this.form.controls.logo_url.setValue('');
        this.updateSessionLogo(null); this.success.set('El logotipo se eliminó correctamente.');
      },
      error: () => { this.uploadingLogo.set(false); this.error.set('No fue posible eliminar el logotipo.'); },
    });
  }
  private updateSessionLogo(logoUrl: string | null) {
    const user = this.session.getUser();
    if (user) this.session.saveUser({ ...user, tenant_logo_url: logoUrl });
  }
  protected submit() {
    if (!this.canUpdate || this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }
    const v = this.form.getRawValue();
    const optional = (value: string) => value.trim() || null;
    this.saving.set(true);
    this.error.set('');
    this.success.set('');
    this.service
      .update({
        name: v.name.trim(),
        legal_name: optional(v.legal_name),
        tax_id: optional(v.tax_id)?.toUpperCase() ?? null,
        contact_email: optional(v.contact_email),
        contact_phone: optional(v.contact_phone),
        website: optional(v.website),
        logo_url: optional(v.logo_url),
        address_line: optional(v.address_line),
        city: optional(v.city),
        state: optional(v.state),
        postal_code: optional(v.postal_code),
        country: v.country.trim(),
        currency: v.currency.trim().toUpperCase(),
        default_tax_rate: Number(v.default_tax_rate),
        quote_validity_days: Number(v.quote_validity_days),
        quote_prefix: v.quote_prefix.trim().toUpperCase(),
        payment_instructions: optional(v.payment_instructions),
      })
      .subscribe({
        next: (x) => {
          this.saving.set(false);
          this.success.set('La configuración de la empresa se guardó correctamente.');
          const user = this.session.getUser();
          if (user) {
            this.session.saveUser({ ...user, tenant_name: x.name });
          }
        },
        error: () => {
          this.saving.set(false);
          this.error.set('No fue posible guardar la configuración. Intenta nuevamente.');
        },
      });
  }
}
