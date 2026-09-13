import { AbstractControl, ValidationErrors, ValidatorFn } from '@angular/forms';

export interface PasswordChecks {
  minLength: boolean;
  uppercase: boolean;
  lowercase: boolean;
  number: boolean;
  special: boolean;
}

export function getPasswordChecks(value: string): PasswordChecks {
  return {
    minLength: value.length >= 8,
    uppercase: /[A-Z]/.test(value),
    lowercase: /[a-z]/.test(value),
    number: /\d/.test(value),
    special: /[!@#$%^&*(),.?":{}|<>_\-+=\[\]\\/;'`~]/.test(value)
  };
}

export const strongPasswordValidator: ValidatorFn = (
  control: AbstractControl<string>
): ValidationErrors | null => {
  const checks = getPasswordChecks(control.value ?? '');
  return Object.values(checks).every(Boolean) ? null : { weakPassword: true };
};
