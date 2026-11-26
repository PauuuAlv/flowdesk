import { Component, computed, DestroyRef, inject, input, OnInit, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormArray, FormControl, FormGroup, NonNullableFormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { startWith } from 'rxjs';

import { ActivityReminder, ActivityReminderInput } from '../../core/models/activity.models';

export type ReminderUnit = 'minutes' | 'hours' | 'days';
/** `before`: X tiempo antes de la actividad. `fixed`: fecha y hora exacta. */
export type ReminderMode = 'before' | 'fixed';
export type ReminderGroup = FormGroup<{
  id: FormControl<string | null>;
  mode: FormControl<ReminderMode>;
  amount: FormControl<number>;
  unit: FormControl<ReminderUnit>;
  /** Valor de `<input type="datetime-local">` (hora local, sin zona). */
  at: FormControl<string>;
}>;
export type ReminderArray = FormArray<ReminderGroup>;

const UNIT_MINUTES: Record<ReminderUnit, number> = { minutes: 1, hours: 60, days: 1440 };
export const MAX_REMINDERS = 10;
export const MAX_REMINDER_MINUTES = 30 * 1440;

function bestUnit(minutes: number): ReminderUnit {
  return minutes > 0 && minutes % 1440 === 0 ? 'days' : minutes > 0 && minutes % 60 === 0 ? 'hours' : 'minutes';
}

/** Fecha → valor de `datetime-local` en la hora local del navegador. */
export function toLocalInput(value: Date | string): string {
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return '';
  d.setMinutes(d.getMinutes() - d.getTimezoneOffset());
  return d.toISOString().slice(0, 16);
}

export function reminderGroup(
  fb: NonNullableFormBuilder,
  id: string | null,
  options: { minutes?: number; at?: string },
): ReminderGroup {
  const minutes = options.minutes ?? 15;
  const unit = bestUnit(minutes);
  return fb.group({
    id: fb.control<string | null>(id),
    mode: fb.control<ReminderMode>(options.at !== undefined ? 'fixed' : 'before'),
    amount: fb.control(minutes / UNIT_MINUTES[unit], [Validators.min(0), Validators.max(MAX_REMINDER_MINUTES)]),
    unit: fb.control<ReminderUnit>(unit),
    at: fb.control(options.at ?? ''),
  });
}

/** Llena el arreglo con los recordatorios guardados de una actividad. */
export function loadReminders(fb: NonNullableFormBuilder, array: ReminderArray, reminders: ActivityReminder[]): void {
  array.clear();
  reminders.forEach((item) =>
    array.push(
      item.fixed_at
        ? reminderGroup(fb, item.id, { at: toLocalInput(item.fixed_at) })
        : reminderGroup(fb, item.id, { minutes: item.minutes_before ?? 0 }),
    ),
  );
}

export function toMinutes(amount: number, unit: ReminderUnit): number {
  return Math.round(Number(amount) * UNIT_MINUTES[unit]);
}

type ReminderValue = ReturnType<ReminderGroup['getRawValue']>;

/** Fecha efectiva de envío, o un mensaje de error si el recordatorio no es válido. */
function evaluate(item: ReminderValue, scheduled: Date | null): { at: Date | null; error: string | null } {
  if (item.mode === 'fixed') {
    const at = item.at ? new Date(item.at) : null;
    if (!at || Number.isNaN(at.getTime())) return { at: null, error: 'Elige la fecha y hora del aviso.' };
    if (scheduled && at.getTime() > scheduled.getTime()) return { at, error: 'Debe ser antes de la actividad.' };
    if (scheduled && scheduled.getTime() - at.getTime() > MAX_REMINDER_MINUTES * 60_000) {
      return { at, error: 'Máximo 30 días antes de la actividad.' };
    }
    return { at, error: null };
  }
  const minutes = toMinutes(item.amount ?? 0, item.unit);
  if (!(minutes >= 0)) return { at: null, error: 'Indica cuánto tiempo antes.' };
  if (minutes > MAX_REMINDER_MINUTES) return { at: null, error: 'Máximo 30 días de anticipación.' };
  return { at: scheduled ? new Date(scheduled.getTime() - minutes * 60_000) : null, error: null };
}

function parseScheduled(value: string | null): Date | null {
  const date = value ? new Date(value) : null;
  return date && !Number.isNaN(date.getTime()) ? date : null;
}

/**
 * Convierte el arreglo del formulario al cuerpo que espera la API.
 * Devuelve null si algún recordatorio no es válido.
 */
export function reminderPayload(array: ReminderArray, scheduledAt: string | null): ActivityReminderInput[] | null {
  const scheduled = parseScheduled(scheduledAt);
  const items: ActivityReminderInput[] = [];
  for (const item of array.getRawValue()) {
    const result = evaluate(item, scheduled);
    if (result.error) return null;
    items.push(
      item.mode === 'fixed'
        ? { id: item.id, fixed_at: result.at!.toISOString() }
        : { id: item.id, minutes_before: toMinutes(item.amount, item.unit) },
    );
  }
  return items;
}

/**
 * Editor de recordatorios de una actividad: "X tiempo antes" o una fecha y hora
 * exacta. Se usa en el formulario de actividad y en la lista, para que el
 * responsable los gestione aunque no pueda editar la actividad.
 */
@Component({
  selector: 'app-activity-reminders-editor',
  imports: [ReactiveFormsModule],
  templateUrl: './activity-reminders-editor.html',
  styleUrl: './activity-reminders.scss',
})
export class ActivityRemindersEditor implements OnInit {
  private readonly fb = inject(NonNullableFormBuilder);
  private readonly destroyRef = inject(DestroyRef);

  readonly reminders = input.required<ReminderArray>();
  /** Fecha de la actividad: ISO o valor de un `datetime-local`. */
  readonly scheduledAt = input<string | null>(null);
  readonly showHeader = input(true);

  protected readonly maxReminders = MAX_REMINDERS;
  protected readonly units: { value: ReminderUnit; label: string }[] = [
    { value: 'minutes', label: 'minutos' },
    { value: 'hours', label: 'horas' },
    { value: 'days', label: 'días' },
  ];
  protected readonly presets: { label: string; minutes: number }[] = [
    { label: 'A la hora', minutes: 0 },
    { label: '15 min antes', minutes: 15 },
    { label: '1 hora antes', minutes: 60 },
    { label: '1 día antes', minutes: 1440 },
  ];
  private readonly values = signal<ReminderValue[]>([]);

  protected readonly summaries = computed(() => {
    const scheduled = parseScheduled(this.scheduledAt());
    const now = Date.now();
    return this.values().map((item) => {
      const { at, error } = evaluate(item, scheduled);
      if (error) return { text: error, past: true };
      if (!at) return { text: 'Define la fecha de la actividad.', past: false };
      const label = new Intl.DateTimeFormat('es-MX', { dateStyle: 'medium', timeStyle: 'short' }).format(at);
      return at.getTime() <= now
        ? { text: `${label} · ya pasó, no se enviará`, past: true }
        : { text: `Se avisará el ${label}`, past: false };
    });
  });

  ngOnInit(): void {
    const array = this.reminders();
    array.valueChanges
      .pipe(startWith(null), takeUntilDestroyed(this.destroyRef))
      .subscribe(() => this.values.set(array.getRawValue()));
  }

  protected get controls(): ReminderGroup[] {
    return this.reminders().controls;
  }

  /** Recordatorio "X tiempo antes" desde los botones rápidos. */
  protected addBefore(minutes: number): void {
    if (this.reminders().length >= MAX_REMINDERS) return;
    this.reminders().push(reminderGroup(this.fb, null, { minutes }));
  }

  /** Recordatorio con fecha y hora exacta; propone una hora antes de la actividad. */
  protected addFixed(): void {
    if (this.reminders().length >= MAX_REMINDERS) return;
    const scheduled = parseScheduled(this.scheduledAt());
    const suggestion = scheduled ? toLocalInput(new Date(scheduled.getTime() - 60 * 60_000)) : '';
    this.reminders().push(reminderGroup(this.fb, null, { at: suggestion }));
  }

  /** Cambia una fila entre "X tiempo antes" y "fecha exacta" conservando la hora equivalente. */
  protected switchMode(group: ReminderGroup): void {
    const scheduled = parseScheduled(this.scheduledAt());
    const value = group.getRawValue();
    if (value.mode === 'before') {
      const minutes = toMinutes(value.amount ?? 0, value.unit);
      group.patchValue({
        mode: 'fixed',
        at: scheduled ? toLocalInput(new Date(scheduled.getTime() - minutes * 60_000)) : '',
      });
      return;
    }
    const at = value.at ? new Date(value.at) : null;
    const minutes = scheduled && at && !Number.isNaN(at.getTime())
      ? Math.max(0, Math.round((scheduled.getTime() - at.getTime()) / 60_000))
      : 15;
    const unit = bestUnit(minutes);
    group.patchValue({ mode: 'before', amount: minutes / UNIT_MINUTES[unit], unit });
  }

  protected remove(index: number): void {
    this.reminders().removeAt(index);
  }
}
