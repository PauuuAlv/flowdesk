/**
 * Colores de las etapas (iguales a STAGE_PALETTE del backend). Se guarda el color
 * base y el tablero lo aclara con color-mix(), así el texto siempre se lee bien.
 */
export const STAGE_PALETTE: ReadonlyArray<{ value: string; name: string }> = [
  { value: '#3b82f6', name: 'Azul' },
  { value: '#06b6d4', name: 'Cian' },
  { value: '#8b5cf6', name: 'Violeta' },
  { value: '#f59e0b', name: 'Ámbar' },
  { value: '#ec4899', name: 'Rosa' },
  { value: '#14b8a6', name: 'Turquesa' },
  { value: '#6366f1', name: 'Índigo' },
  { value: '#f97316', name: 'Naranja' },
  { value: '#22c55e', name: 'Verde' },
  { value: '#ef4444', name: 'Rojo' },
  { value: '#64748b', name: 'Gris' },
];

export const WON_COLOR = '#22c55e';
export const LOST_COLOR = '#ef4444';

/** Color sugerido para una etapa nueva según su tipo y cuántas hay. */
export function suggestedStageColor(stageType: string, existing: number): string {
  if (stageType === 'won') return WON_COLOR;
  if (stageType === 'lost') return LOST_COLOR;
  return STAGE_PALETTE[existing % 8].value;
}
