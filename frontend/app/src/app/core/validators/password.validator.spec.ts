import { FormControl } from '@angular/forms';

import { getPasswordChecks, strongPasswordValidator } from './password.validator';

describe('strongPasswordValidator', () => {
  it('should reject a password without the required character groups', () => {
    const control = new FormControl('tiburoncinuaa', { nonNullable: true });
    expect(strongPasswordValidator(control)).toEqual({ weakPassword: true });
  });

  it('should accept a password with uppercase, lowercase, number and special character', () => {
    const control = new FormControl('Tiburon!2026', { nonNullable: true });
    expect(strongPasswordValidator(control)).toBeNull();
  });

  it('should report each password requirement independently', () => {
    const checks = getPasswordChecks('Flowdesk!2026');
    expect(Object.values(checks).every(Boolean)).toBeTrue();
  });
});
