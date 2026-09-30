import { FormControl } from '@angular/forms';

import { atLeastOnePermissionValidator } from './role.validator';

describe('atLeastOnePermissionValidator', () => {
  it('should require at least one selected permission', () => {
    expect(atLeastOnePermissionValidator(new FormControl({ one: false, two: false }))).toEqual({
      permissionRequired: true
    });
  });

  it('should accept a selected permission', () => {
    expect(atLeastOnePermissionValidator(new FormControl({ one: false, two: true }))).toBeNull();
  });
});
