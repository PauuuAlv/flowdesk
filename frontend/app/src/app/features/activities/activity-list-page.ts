import { Component, computed, DestroyRef, effect, inject, signal, untracked } from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';
import { NonNullableFormBuilder } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { map } from 'rxjs';
import { Activity, ActivityStatus, ActivityType } from '../../core/models/activity.models';
import { PERMISSIONS } from '../../core/models/permission.models';
import { ActivityService } from '../../core/services/activity.service';
import { SessionService } from '../../core/services/session.service';
import { ComboOption } from '../../shared/ui/combobox/combobox';
import { MultiSelect } from '../../shared/ui/multi-select/multi-select';
import { ActivityCalendar, localDateKey, NO_PIPELINE_COLOR } from './activity-calendar';
import { ActivityRemindersEditor, loadReminders, ReminderGroup, reminderPayload } from './activity-reminders-editor';
import { DataTransfer } from '../../shared/ui/data-transfer/data-transfer';

@Component({
  selector: 'app-activity-list-page',
  imports: [RouterLink, ActivityRemindersEditor, ActivityCalendar, DataTransfer, MultiSelect],
  templateUrl: './activity-list-page.html',
  styleUrl: './activity-list-page.scss',
})
export class ActivityListPage {
  private readonly service = inject(ActivityService);
  private readonly user = inject(SessionService).getUser();
  private readonly fb = inject(NonNullableFormBuilder);
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly destroyRef = inject(DestroyRef);
  /** `?actividad=<id>`: viene de una notificación; se desplaza a ella y parpadea. */
  private readonly focusId = toSignal(this.route.queryParamMap.pipe(map((params) => params.get('actividad'))), {
    initialValue: null,
  });
  protected readonly highlighted = signal<string | null>(null);
  private highlightTimer: ReturnType<typeof setTimeout> | undefined;
  protected readonly items = signal<Activity[]>([]);
  protected readonly loading = signal(true);
  protected readonly error = signal('');
  /** Vista activa: lista o calendario (se recuerda en este navegador). */
  protected readonly view = signal<'list' | 'calendar'>(this.storedView());
  protected readonly noPipelineColor = NO_PIPELINE_COLOR;
  // --- Filtros (aplican a la lista y al calendario) ---
  protected readonly search = signal('');
  // Cada filtro admite varios valores; vacío = todos.
  protected readonly status = signal<(ActivityStatus | 'overdue')[]>([]);
  protected readonly type = signal<ActivityType[]>([]);
  protected readonly client = signal<string[]>([]);
  protected readonly owner = signal<string[]>([]);
  /** Fechas AAAA-MM-DD; con una sola se filtra desde/hasta ese día. */
  protected readonly dateFrom = signal('');
  protected readonly dateTo = signal('');
  protected readonly typeOptions: ComboOption[] = [
    { value: 'call', label: 'Llamadas' },
    { value: 'email', label: 'Correos' },
    { value: 'meeting', label: 'Reuniones' },
    { value: 'task', label: 'Tareas' },
  ];
  protected readonly statusOptions: ComboOption[] = [
    { value: 'pending', label: 'Pendientes' },
    { value: 'overdue', label: 'Vencidas' },
    { value: 'completed', label: 'Completadas' },
    { value: 'cancelled', label: 'Canceladas' },
  ];
  protected readonly clientOptions = computed<ComboOption[]>(() =>
    this.distinct(this.items().map((x) => ({ value: x.client_id, label: x.client_name }))),
  );
  protected readonly ownerOptions = computed<ComboOption[]>(() =>
    this.distinct(this.items().map((x) => ({ value: x.owner_user_id, label: x.owner_name }))),
  );
  protected readonly activeFilters = computed(
    () =>
      [
        this.search().trim(),
        this.status().length,
        this.type().length,
        this.client().length,
        this.owner().length,
        this.dateFrom(),
        this.dateTo(),
      ].filter(Boolean).length,
  );
  protected readonly canCreate = this.has(PERMISSIONS.activitiesCreate);
  protected readonly canUpdate = this.has(PERMISSIONS.activitiesUpdate);
  protected readonly canComplete = this.has(PERMISSIONS.activitiesComplete);
  /** Actividad cuyo panel de recordatorios está abierto. */
  protected readonly remindersOpen = signal<string | null>(null);
  protected readonly remindersSaving = signal(false);
  protected readonly remindersError = signal('');
  protected readonly reminderForm = this.fb.array<ReminderGroup>([]);
  protected readonly filtered = computed(() => {
    const q = this.search().trim().toLowerCase();
    const status = this.status();
    let from = this.dateFrom();
    let to = this.dateTo();
    if (from && to && from > to) [from, to] = [to, from];
    return this.items().filter((x) => {
      const day = localDateKey(x.scheduled_at);
      return (
        (!status.length || status.some((s) => (s === 'overdue' ? this.overdue(x) : x.status === s))) &&
        (!this.type().length || this.type().includes(x.activity_type)) &&
        (!this.client().length || this.client().includes(x.client_id)) &&
        (!this.owner().length || this.owner().includes(x.owner_user_id)) &&
        (!from || day >= from) &&
        (!to || day <= to) &&
        (!q ||
          `${x.title} ${x.description ?? ''} ${x.client_name} ${x.opportunity_name ?? ''} ${x.owner_name}`
            .toLowerCase()
            .includes(q))
      );
    });
  });
  constructor() {
    this.load();
    effect(() => {
      const id = this.focusId();
      if (!id || this.loading()) return;
      untracked(() => this.focusActivity(id));
    });
    this.destroyRef.onDestroy(() => clearTimeout(this.highlightTimer));
  }

  /** Muestra la actividad aunque los filtros la ocultaran, la centra y la hace parpadear 3 veces. */
  private focusActivity(id: string): void {
    const item = this.items().find((x) => x.id === id);
    // Se quita el parámetro para que volver a abrir la misma notificación funcione de nuevo.
    void this.router.navigate([], {
      relativeTo: this.route,
      queryParams: { actividad: null },
      queryParamsHandling: 'merge',
      replaceUrl: true,
    });
    if (!item) {
      this.error.set('La actividad de la notificación ya no está disponible.');
      return;
    }
    this.setView('list');
    if (!this.filtered().some((x) => x.id === id)) this.clearFilters();
    clearTimeout(this.highlightTimer);
    this.highlighted.set(null);
    // Espera a que la lista se pinte (y se reinicie la animación si ya estaba resaltada).
    setTimeout(() => {
      const element = document.getElementById(`actividad-${id}`);
      element?.scrollIntoView({ behavior: 'smooth', block: 'center' });
      this.highlighted.set(id);
      this.highlightTimer = setTimeout(() => this.highlighted.set(null), 2600);
    }, 60);
  }
  protected load() {
    this.loading.set(true);
    this.service.list().subscribe({
      next: (x) => {
        this.items.set(x);
        this.loading.set(false);
      },
      error: () => {
        this.error.set('No fue posible consultar las actividades.');
        this.loading.set(false);
      },
    });
  }
  protected setSearch(e: Event) {
    this.search.set((e.target as HTMLInputElement).value);
  }
  protected setStatus(values: string[]) {
    this.status.set(values as (ActivityStatus | 'overdue')[]);
  }
  protected setDate(which: 'from' | 'to', event: Event) {
    const value = (event.target as HTMLInputElement).value;
    (which === 'from' ? this.dateFrom : this.dateTo).set(value);
  }
  /** Atajo: solo las actividades de hoy. */
  protected onlyToday() {
    const today = localDateKey(new Date());
    this.dateFrom.set(today);
    this.dateTo.set(today);
  }
  protected clearFilters() {
    this.search.set('');
    this.status.set([]);
    this.type.set([]);
    this.client.set([]);
    this.owner.set([]);
    this.dateFrom.set('');
    this.dateTo.set('');
  }
  protected setView(view: 'list' | 'calendar') {
    this.view.set(view);
    try {
      localStorage.setItem('flowdesk.activities.view', view);
    } catch {
      /* almacenamiento no disponible: solo no se recuerda */
    }
  }
  /** Desde el calendario: vuelve a la lista, se desplaza a la actividad y parpadea. */
  protected openFromCalendar(id: string) {
    this.focusActivity(id);
  }
  private storedView(): 'list' | 'calendar' {
    try {
      return localStorage.getItem('flowdesk.activities.view') === 'calendar' ? 'calendar' : 'list';
    } catch {
      return 'list';
    }
  }
  private distinct(options: ComboOption[]): ComboOption[] {
    const map = new Map(options.map((option) => [option.value, option]));
    return [...map.values()].sort((a, b) => a.label.localeCompare(b.label, 'es'));
  }
  protected setType(values: string[]) {
    this.type.set(values as ActivityType[]);
  }
  protected changeStatus(item: Activity, status: ActivityStatus) {
    this.service.updateStatus(item.id, status).subscribe({
      next: (x) => {
        this.items.update((all) => all.map((v) => (v.id === x.id ? x : v)));
        this.error.set('');
      },
      error: () => this.error.set('No fue posible actualizar la actividad.'),
    });
  }
  /** El responsable gestiona sus recordatorios aunque no tenga permiso de editar. */
  protected canManageReminders(item: Activity): boolean {
    return this.canUpdate || item.owner_user_id === this.user?.id;
  }
  protected toggleReminders(item: Activity) {
    this.remindersError.set('');
    if (this.remindersOpen() === item.id) {
      this.remindersOpen.set(null);
      return;
    }
    loadReminders(this.fb, this.reminderForm, item.reminders ?? []);
    this.remindersOpen.set(item.id);
  }
  protected saveReminders(item: Activity) {
    const reminders = reminderPayload(this.reminderForm, item.scheduled_at);
    if (!reminders || this.reminderForm.invalid) {
      this.reminderForm.markAllAsTouched();
      this.remindersError.set('Revisa los recordatorios marcados: deben ser antes de la actividad y con máximo 30 días de anticipación.');
      return;
    }
    this.remindersSaving.set(true);
    this.service.updateReminders(item.id, reminders).subscribe({
      next: (x) => {
        this.items.update((all) => all.map((v) => (v.id === x.id ? x : v)));
        this.remindersSaving.set(false);
        this.remindersOpen.set(null);
      },
      error: () => {
        this.remindersSaving.set(false);
        this.remindersError.set('No fue posible guardar los recordatorios.');
      },
    });
  }
  protected pendingReminders(item: Activity): number {
    return (item.reminders ?? []).filter((r) => !r.sent_at).length;
  }
  protected typeLabel(x: ActivityType) {
    return { call: 'Llamada', email: 'Correo', meeting: 'Reunión', task: 'Tarea' }[x];
  }
  protected statusLabel(x: ActivityStatus) {
    return { pending: 'Pendiente', completed: 'Completada', cancelled: 'Cancelada' }[x];
  }
  protected date(value: string) {
    return new Intl.DateTimeFormat('es-MX', { dateStyle: 'medium', timeStyle: 'short' }).format(
      new Date(value),
    );
  }
  protected overdue(item: Activity) {
    return item.status === 'pending' && new Date(item.scheduled_at) < new Date();
  }
  private has(p: (typeof PERMISSIONS)[keyof typeof PERMISSIONS]) {
    return Boolean(this.user?.permissions?.includes(p));
  }
}
