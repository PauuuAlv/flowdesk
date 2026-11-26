import { Component, computed, DestroyRef, effect, inject, signal, untracked } from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';
import { NonNullableFormBuilder } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { map } from 'rxjs';
import { Activity, ActivityStatus, ActivityType } from '../../core/models/activity.models';
import { PERMISSIONS } from '../../core/models/permission.models';
import { ActivityService } from '../../core/services/activity.service';
import { SessionService } from '../../core/services/session.service';
import { Combobox } from '../../shared/ui/combobox/combobox';
import { ActivityRemindersEditor, loadReminders, ReminderGroup, reminderPayload } from './activity-reminders-editor';

@Component({
  selector: 'app-activity-list-page',
  imports: [RouterLink, Combobox, ActivityRemindersEditor],
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
  protected readonly search = signal('');
  protected readonly status = signal<ActivityStatus | 'all'>('all');
  protected readonly type = signal<ActivityType | 'all'>('all');
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
    return this.items().filter(
      (x) =>
        (this.status() === 'all' || x.status === this.status()) &&
        (this.type() === 'all' || x.activity_type === this.type()) &&
        (!q ||
          `${x.title} ${x.client_name} ${x.opportunity_name ?? ''} ${x.owner_name}`
            .toLowerCase()
            .includes(q)),
    );
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
    if (!this.filtered().some((x) => x.id === id)) {
      this.search.set('');
      this.status.set('all');
      this.type.set('all');
    }
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
  protected setStatus(value: string) {
    this.status.set(value as ActivityStatus | 'all');
  }
  protected setType(value: string) {
    this.type.set(value as ActivityType | 'all');
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
