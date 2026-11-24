import { Pipeline } from '../models/opportunity.models';

const STORAGE_KEY = 'flowdesk.selected_pipeline';

/**
 * Último pipeline elegido en el tablero o en "Pipelines y etapas", para abrir
 * siempre el mismo y proponerlo en "Nueva oportunidad". Es solo una comodidad
 * del navegador: si no hay o ya no existe, se usa el predeterminado.
 */
export function rememberPipeline(id: string): void {
  try {
    localStorage.setItem(STORAGE_KEY, id);
  } catch {
    // Almacenamiento no disponible (modo privado): no pasa nada.
  }
}

export function preferredPipeline(pipelines: Pipeline[], requested?: string | null): Pipeline | null {
  let stored: string | null = null;
  try {
    stored = localStorage.getItem(STORAGE_KEY);
  } catch {
    stored = null;
  }
  return (
    pipelines.find((p) => p.id === requested) ??
    pipelines.find((p) => p.id === stored) ??
    pipelines.find((p) => p.is_default) ??
    pipelines[0] ??
    null
  );
}
