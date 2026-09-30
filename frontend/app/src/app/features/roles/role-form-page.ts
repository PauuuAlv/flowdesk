import { Component, inject, signal } from '@angular/core';
import { FormBuilder, FormControl, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';

import { PermissionCode, PERMISSION_MODULES } from '../../core/models/permission.models';
import { AccessControlPreviewService } from '../../core/services/access-control-preview.service';
import { atLeastOnePermissionValidator } from '../../core/validators/role.validator';

@Component({
  selector: 'app-role-form-page',
  imports: [ReactiveFormsModule, RouterLink],
  templateUrl: './role-form-page.html',
  styleUrl: './role-form-page.scss'
})
export class RoleFormPage {
  private readonly formBuilder = inject(FormBuilder);
  private readonly accessControl = inject(AccessControlPreviewService);
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);

  protected readonly permissionModules = PERMISSION_MODULES;
  protected readonly roleId = this.route.snapshot.paramMap.get('roleId');
  protected readonly editing = Boolean(this.roleId);
  protected readonly loading = signal(this.editing);
  protected readonly saving = signal(false);
  protected readonly errorMessage = signal('');
  protected readonly protectedRole = signal(false);
  private readonly allPermissionCodes = PERMISSION_MODULES.reduce<PermissionCode[]>(
    (codes, module) => [...codes, ...module.permissions.map((permission) => permission.code)],
    []
  );
  protected readonly permissionControls = Object.fromEntries(
    this.allPermissionCodes.map((permission) => [
      permission,
      new FormControl(false, { nonNullable: true })
    ])
  ) as Record<PermissionCode, FormControl<boolean>>;

  protected readonly roleForm = this.formBuilder.nonNullable.group({
    name: ['', [Validators.required, Validators.minLength(3), Validators.maxLength(50), Validators.pattern(/^[A-Za-zÁÉÍÓÚÜÑáéíóúüñ0-9 ]+$/)]],
    description: ['', [Validators.required, Validators.minLength(10), Validators.maxLength(160)]],
    permissions: this.formBuilder.group(this.permissionControls, { validators: atLeastOnePermissionValidator })
  });

  constructor() {
    if (this.roleId) this.loadRole(this.roleId);
  }

  protected toggleModule(moduleIndex: number): void {
    const module = this.permissionModules[moduleIndex];
    const selectAll = !module.permissions.every((permission) => this.permissionControls[permission.code].value);
    module.permissions.forEach((permission) => this.permissionControls[permission.code].setValue(selectAll));
    this.roleForm.controls.permissions.markAsTouched();
  }

  protected moduleSelected(moduleIndex: number): boolean {
    return this.permissionModules[moduleIndex].permissions.every(
      (permission) => this.permissionControls[permission.code].value
    );
  }

  protected submit(): void {
    this.errorMessage.set('');
    if (this.roleForm.invalid) {
      this.roleForm.markAllAsTouched();
      return;
    }

    const raw = this.roleForm.getRawValue();
    const permissions = Object.entries(raw.permissions)
      .filter(([, selected]) => selected)
      .map(([permission]) => permission as PermissionCode);

    this.saving.set(true);
    this.accessControl
      .saveRole(
        { name: raw.name.trim(), description: raw.description.trim(), permissions },
        this.roleId ?? undefined
      )
      .subscribe({
        next: () => {
          this.saving.set(false);
          void this.router.navigate(['/panel/roles']);
        },
        error: (error: Error) => {
          this.saving.set(false);
          this.errorMessage.set(
            error.message === 'DUPLICATE_ROLE'
              ? 'Ya existe un rol con ese nombre en tu empresa.'
              : 'No fue posible guardar el rol. Intenta nuevamente.'
          );
        }
      });
  }

  private loadRole(roleId: string): void {
    this.accessControl.getRole(roleId).subscribe({
      next: (role) => {
        this.roleForm.patchValue({ name: role.name, description: role.description });
        role.permissions.forEach((permission) => this.permissionControls[permission].setValue(true));
        if (role.is_protected) {
          this.protectedRole.set(true);
          this.roleForm.controls.name.disable();
        }
        this.loading.set(false);
      },
      error: () => {
        this.loading.set(false);
        this.errorMessage.set('El rol solicitado no existe o no está disponible.');
      }
    });
  }
}
