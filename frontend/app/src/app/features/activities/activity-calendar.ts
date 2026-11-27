import { Component, computed, effect, input, output, signal } from '@angular/core';

import { Activity } from '../../core/models/activity.models';

/** Color de las actividades sin oportunidad (y por tanto sin pipeline). */
export const NO_PIPELINE_COLOR = '#64748b';

/** Clave AAAA-MM-DD en la hora local del navegador. */
export function localDateKey(value: Date | string): string {
  const d = new Date(value);
  const month = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${d.getFullYear()}-${month}-${day}`;
}

interface CalendarDay {
  key: string;
  date: Date;
  inMonth: boolean;
  isToday: boolean;
  items: Activity[];
}

const MAX_CHIPS = 3;

/**
 * Calendario mensual de actividades. Cada actividad toma el color del pipeline
 * de su oportunidad. Al elegir un día se muestra su agenda debajo; al elegir
 * una actividad se emite `open` para enfocarla en la lista.
 */
@Component({
  selector: 'app-activity-calendar',
  templateUrl: './activity-calendar.html',
  styleUrl: './activity-calendar.scss',
})
export class ActivityCalendar {
  readonly activities = input.required<Activity[]>();
  /** Fecha (AAAA-MM-DD) a mostrar, p. ej. el inicio del filtro de fechas. */
  readonly anchorDate = input<string | null>(null);
  readonly open = output<string>();

  protected readonly weekdays = ['Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb', 'Dom'];
  protected readonly maxChips = MAX_CHIPS;
  protected readonly month = signal(this.firstOfMonth(new Date()));
  protected readonly selectedKey = signal(localDateKey(new Date()));

  protected readonly monthLabel = computed(() => {
    const label = new Intl.DateTimeFormat('es-MX', { month: 'long', year: 'numeric' }).format(this.month());
    return label.charAt(0).toUpperCase() + label.slice(1);
  });

  private readonly byDay = computed(() => {
    const map = new Map<string, Activity[]>();
    for (const item of [...this.activities()].sort((a, b) => a.scheduled_at.localeCompare(b.scheduled_at))) {
      const key = localDateKey(item.scheduled_at);
      map.set(key, [...(map.get(key) ?? []), item]);
    }
    return map;
  });

  protected readonly days = computed<CalendarDay[]>(() => {
    const first = this.month();
    // La semana empieza en lunes.
    const offset = (first.getDay() + 6) % 7;
    const start = new Date(first.getFullYear(), first.getMonth(), 1 - offset);
    const todayKey = localDateKey(new Date());
    const days: CalendarDay[] = [];
    for (let i = 0; i < 42; i++) {
      const date = new Date(start.getFullYear(), start.getMonth(), start.getDate() + i);
      const key = localDateKey(date);
      days.push({
        key,
        date,
        inMonth: date.getMonth() === first.getMonth(),
        isToday: key === todayKey,
        items: this.byDay().get(key) ?? [],
      });
    }
    // Si la última semana queda completa fuera del mes, se omite.
    return days.slice(35).every((day) => !day.inMonth) ? days.slice(0, 35) : days;
  });

  protected readonly selectedItems = computed(() => this.byDay().get(this.selectedKey()) ?? []);
  protected readonly selectedLabel = computed(() => {
    const [y, m, d] = this.selectedKey().split('-').map(Number);
    return new Intl.DateTimeFormat('es-MX', { weekday: 'long', day: 'numeric', month: 'long' }).format(new Date(y, m - 1, d));
  });

  /** Pipelines presentes en las actividades filtradas, para la leyenda. */
  protected readonly legend = computed(() => {
    const map = new Map<string, { name: string; color: string }>();
    for (const item of this.activities()) {
      const key = item.pipeline_id ?? '';
      if (!map.has(key)) {
        map.set(key, { name: item.pipeline_name ?? 'Sin oportunidad', color: this.color(item) });
      }
    }
    return [...map.values()].sort((a, b) => a.name.localeCompare(b.name));
  });

  constructor() {
    effect(() => {
      const anchor = this.anchorDate();
      if (!anchor) return;
      const [y, m] = anchor.split('-').map(Number);
      this.month.set(new Date(y, m - 1, 1));
      this.selectedKey.set(anchor);
    });
  }

  protected move(months: number): void {
    const current = this.month();
    this.month.set(new Date(current.getFullYear(), current.getMonth() + months, 1));
  }

  protected goToday(): void {
    this.month.set(this.firstOfMonth(new Date()));
    this.selectedKey.set(localDateKey(new Date()));
  }

  protected selectDay(day: CalendarDay): void {
    this.selectedKey.set(day.key);
    if (!day.inMonth) this.month.set(this.firstOfMonth(day.date));
  }

  protected color(item: Activity): string {
    return item.pipeline_color ?? NO_PIPELINE_COLOR;
  }

  protected time(item: Activity): string {
    return new Intl.DateTimeFormat('es-MX', { hour: 'numeric', minute: '2-digit' }).format(new Date(item.scheduled_at));
  }

  protected overdue(item: Activity): boolean {
    return item.status === 'pending' && new Date(item.scheduled_at) < new Date();
  }

  protected typeLabel(item: Activity): string {
    return { call: 'Llamada', email: 'Correo', meeting: 'Reunión', task: 'Tarea' }[item.activity_type];
  }

  protected statusLabel(item: Activity): string {
    if (this.overdue(item)) return 'Vencida';
    return { pending: 'Pendiente', completed: 'Completada', cancelled: 'Cancelada' }[item.status];
  }

  private firstOfMonth(date: Date): Date {
    return new Date(date.getFullYear(), date.getMonth(), 1);
  }
}
