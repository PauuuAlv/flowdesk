import { ComboOption } from '../../shared/ui/combobox/combobox';

/** Opciones compartidas por los combos del panel de plataforma. */
export const PLAN_OPTIONS: ComboOption[] = [
  { value: 'basic', label: 'Básico' },
  { value: 'professional', label: 'Profesional' },
  { value: 'enterprise', label: 'Empresarial' },
];

export const SUBSCRIPTION_STATUS_OPTIONS: ComboOption[] = [
  { value: 'trial', label: 'Prueba' },
  { value: 'active', label: 'Activo' },
  { value: 'suspended', label: 'Suspendido' },
  { value: 'cancelled', label: 'Cancelado' },
];
