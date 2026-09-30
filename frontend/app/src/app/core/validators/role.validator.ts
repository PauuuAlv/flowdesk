import { AbstractControl, ValidationErrors, ValidatorFn } from '@angular/forms';

export const atLeastOnePermissionValidator: ValidatorFn = (
  control: AbstractControl
): ValidationErrors | null => {
  const value = control.value as Record<string, boolean> | null;
  return value && Object.values(value).some(Boolean) ? null : { permissionRequired: true };
};
