import { HttpErrorResponse } from '@angular/common/http';
import { Component, computed, effect, inject, signal, untracked } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';

import { PlatformMember } from '../../../core/models/auth.models';
import {
  PLATFORM_PERMISSION_MODULES,
  PLATFORM_PERMISSIONS,
  PlatformPermissionCode,
  PlatformRole,
} from '../../../core/models/platform-access.models';
import { PlatformAccessService } from '../../../core/services/platform-access.service';
import { PlatformTeamService } from '../../../core/services/platform-team.service';
import { Combobox, ComboOption } from '../../../shared/ui/combobox/combobox';
import { MultiSelect } from '../../../shared/ui/multi-select/multi-select';

type Tab = 'members' | 'roles';
type MemberFilter = 'active' | 'pending' | 'inactive';

const ALL_PERMISSIONS: PlatformPermissionCode[] = PLATFORM_PERMISSION_MODULES.flatMap((module) =>
  module.permissions.map((permission) => permission.code),
);

@Component({
  selector: 'app-platform-team-page',
  imports: [ReactiveFormsModule, Combobox, MultiSelect],
  templateUrl: './platform-team-page.html',
  styleUrl: './platform-team-page.scss',
})
export class PlatformTeamPage {
  private readonly team = inject(PlatformTeamService);
  private readonly fb = inject(FormBuilder);
  protected readonly access = inject(PlatformAccessService);
  protected readonly P = PLATFORM_PERMISSIONS;
  protected readonly modules = PLATFORM_PERMISSION_MODULES;

  protected readonly tab = signal<Tab>('members');
  protected readonly members = signal<PlatformMember[]>([]);
  protected readonly roles = signal<PlatformRole[]>([]);
  protected readonly roleSelectOptions = computed<ComboOption[]>(() =>
    this.roles().map((role) => ({ value: role.id, label: role.name })),
  );
  protected readonly loading = signal(true);
  protected readonly error = signal('');
  protected readonly success = signal('');
  protected readonly busyMember = signal<string | null>(null);
  protected readonly search = signal('');
  protected readonly memberFilter = signal<MemberFilter[]>([]); // vacío = todos

  // Invitación
  protected readonly inviteOpen = signal(false);
  protected readonly sending = signal(false);
  protected readonly inviteError = signal('');
  protected readonly invitation = signal<PlatformMember | null>(null);
  protected readonly copied = signal(false);
  protected readonly inviteForm = this.fb.nonNullable.group({
    full_name: ['', [Validators.required, Validators.minLength(3)]],
    email: ['', [Validators.required, Validators.email]],
    role_id: ['', Validators.required],
  });

  // Confirmaciones
  protected readonly memberToToggle = signal<PlatformMember | null>(null);
  protected readonly roleToDelete = signal<PlatformRole | null>(null);
  protected readonly processing = signal(false);
  protected readonly dialogError = signal('');

  // Editor de roles
  protected readonly roleEditorOpen = signal(false);
  protected readonly editingRole = signal<PlatformRole | null>(null);
  protected readonly selectedPermissions = signal<Set<PlatformPermissionCode>>(new Set());
  protected readonly savingRole = signal(false);
  protected readonly roleError = signal('');
  protected readonly roleForm = this.fb.nonNullable.group({
    name: ['', [Validators.required, Validators.minLength(3), Validators.maxLength(50)]],
    description: ['', [Validators.required, Validators.minLength(10), Validators.maxLength(160)]],
  });

  protected readonly currentMemberId = computed(() => this.access.member()?.id ?? null);
  protected readonly filteredMembers = computed(() => {
    const term = this.search().trim().toLowerCase();
    const filter = this.memberFilter();
    return this.members().filter((member) => {
      const content = `${member.full_name ?? ''} ${member.email} ${member.role_name}`.toLowerCase();
      return (!term || content.includes(term)) && (!filter.length || filter.includes(this.memberState(member) as MemberFilter));
    });
  });
  protected readonly stats = computed(() => {
    const members = this.members();
    return {
      total: members.length,
      active: members.filter((m) => this.memberState(m) === 'active').length,
      pending: members.filter((m) => this.memberState(m) === 'pending').length,
      superadmins: members.filter((m) => m.role === 'superadmin' && this.memberState(m) === 'active').length,
    };
  });

  constructor() {
    // Los permisos de la sesión los carga el shell; se espera a tenerlos para
    // decidir qué secciones mostrar y qué consultar.
    let started = false;
    effect(() => {
      if (!this.access.loaded() || started) return;
      started = true;
      untracked(() => {
        if (!this.access.can(PLATFORM_PERMISSIONS.teamView)) this.tab.set('roles');
        this.load();
      });
    });
  }

  // --- Carga ---------------------------------------------------------------

  protected load(): void {
    this.loading.set(true);
    this.error.set('');
    const canTeam = this.access.can(PLATFORM_PERMISSIONS.teamView);
    // Sin permiso de roles, el selector de rol solo muestra los roles que ya tiene el equipo.
    const canRoles = this.access.can(PLATFORM_PERMISSIONS.rolesView);
    let pending = Number(canTeam) + Number(canRoles);
    const done = () => { if (--pending <= 0) this.loading.set(false); };
    if (!pending) { this.loading.set(false); return; }
    if (canTeam) {
      this.team.listMembers().subscribe({
        next: (members) => { this.members.set(members); done(); },
        error: () => { this.error.set('No fue posible consultar el equipo de plataforma.'); done(); },
      });
    }
    if (canRoles) {
      this.team.listRoles().subscribe({
        next: (roles) => { this.roles.set(roles); done(); },
        error: () => { this.error.set('No fue posible consultar los roles de plataforma.'); done(); },
      });
    }
  }

  protected setTab(tab: Tab): void {
    this.tab.set(tab);
    this.clearMessages();
  }

  protected setSearch(event: Event): void {
    this.search.set((event.target as HTMLInputElement).value);
  }

  protected setMemberFilter(values: string[]): void {
    this.memberFilter.set(values as MemberFilter[]);
  }

  // --- Integrantes ---------------------------------------------------------

  protected memberState(member: PlatformMember): 'active' | 'pending' | 'inactive' {
    if (!member.is_active) return 'inactive';
    return member.invitation_pending ? 'pending' : 'active';
  }

  protected memberStateLabel(member: PlatformMember): string {
    return { active: 'Activa', pending: 'Invitación pendiente', inactive: 'Desactivada' }[this.memberState(member)];
  }

  protected isSelf(member: PlatformMember): boolean {
    return member.id === this.currentMemberId();
  }

  /** La cuenta principal (.env) y la propia no se pueden cambiar de rol ni desactivar. */
  protected canEdit(member: PlatformMember): boolean {
    return this.access.can(PLATFORM_PERMISSIONS.teamUpdate) && !this.isSelf(member) && !member.is_owner;
  }

  protected openInvite(): void {
    this.clearMessages();
    this.inviteError.set('');
    const viewer = this.roles().find((role) => role.template_key === 'viewer');
    this.inviteForm.reset({ full_name: '', email: '', role_id: viewer?.id ?? '' });
    this.inviteOpen.set(true);
  }

  protected submitInvite(): void {
    if (this.inviteForm.invalid) {
      this.inviteForm.markAllAsTouched();
      return;
    }
    this.sending.set(true);
    this.inviteError.set('');
    this.team.invite(this.inviteForm.getRawValue()).subscribe({
      next: (member) => {
        this.members.update((all) => [...all, member]);
        this.bumpRoleCount(member.role_id, 1);
        this.invitation.set(member);
        this.copied.set(false);
        this.inviteOpen.set(false);
        this.sending.set(false);
      },
      error: (error: HttpErrorResponse) => {
        this.inviteError.set(
          error.status === 409
            ? 'Ese correo ya tiene una cuenta de plataforma.'
            : 'No fue posible enviar la invitación. Revisa los datos e intenta nuevamente.',
        );
        this.sending.set(false);
      },
    });
  }

  protected changeRole(member: PlatformMember, roleId: string, combo: Combobox): void {
    if (roleId === member.role_id) return;
    this.clearMessages();
    this.busyMember.set(member.id);
    this.team.updateRole(member.id, roleId).subscribe({
      next: (updated) => {
        this.replaceMember(updated);
        this.bumpRoleCount(member.role_id, -1);
        this.bumpRoleCount(updated.role_id, 1);
        this.busyMember.set(null);
        this.success.set(`${updated.full_name || updated.email} ahora tiene el rol ${updated.role_name}.`);
      },
      error: (error: HttpErrorResponse) => {
        combo.writeValue(member.role_id); // vuelve a mostrar el rol que conserva
        this.busyMember.set(null);
        this.error.set(this.conflictMessage(error, 'No fue posible cambiar el rol del integrante.'));
      },
    });
  }

  protected resendInvitation(member: PlatformMember): void {
    this.clearMessages();
    this.busyMember.set(member.id);
    this.team.resendInvitation(member.id).subscribe({
      next: (updated) => {
        this.replaceMember(updated);
        this.invitation.set(updated);
        this.copied.set(false);
        this.busyMember.set(null);
      },
      error: () => {
        this.busyMember.set(null);
        this.error.set('No fue posible generar una nueva invitación.');
      },
    });
  }

  protected confirmToggleMember(): void {
    const member = this.memberToToggle();
    if (!member) return;
    this.processing.set(true);
    this.dialogError.set('');
    this.team.updateStatus(member.id, !member.is_active).subscribe({
      next: (updated) => {
        this.replaceMember(updated);
        this.closeDialogs();
        this.success.set(
          `La cuenta de ${updated.full_name || updated.email} quedó ${updated.is_active ? 'activa' : 'desactivada'}.`,
        );
      },
      error: (error: HttpErrorResponse) => {
        this.processing.set(false);
        this.dialogError.set(this.conflictMessage(error, 'No fue posible cambiar el estado de la cuenta.'));
      },
    });
  }

  protected async copyInvitation(): Promise<void> {
    const link = this.invitation()?.invitation_link;
    if (!link) return;
    try {
      await navigator.clipboard.writeText(link);
      this.copied.set(true);
    } catch {
      this.error.set('No fue posible copiar el enlace. Selecciónalo y cópialo manualmente.');
    }
  }

  // --- Roles -----------------------------------------------------------------

  protected roleOriginLabel(role: PlatformRole): string {
    return role.origin === 'template' ? 'Rol inicial' : 'Personalizado';
  }

  protected permissionSummary(role: PlatformRole): string[] {
    const codes = new Set(role.permissions);
    return this.modules
      .filter((module) => module.permissions.some((permission) => codes.has(permission.code)))
      .map((module) => {
        const granted = module.permissions.filter((permission) => codes.has(permission.code));
        return granted.length === module.permissions.length
          ? `${module.label}: todo`
          : `${module.label}: ${granted.map((p) => p.label.toLowerCase()).join(', ')}`;
      });
  }

  protected openRoleEditor(role: PlatformRole | null): void {
    this.clearMessages();
    this.roleError.set('');
    this.editingRole.set(role);
    this.roleForm.reset({ name: role?.name ?? '', description: role?.description ?? '' });
    if (role?.origin === 'template') this.roleForm.controls.name.disable();
    else this.roleForm.controls.name.enable();
    this.selectedPermissions.set(new Set(role?.is_protected ? ALL_PERMISSIONS : role?.permissions ?? []));
    this.roleEditorOpen.set(true);
  }

  protected isSelected(code: PlatformPermissionCode): boolean {
    return this.selectedPermissions().has(code);
  }

  protected togglePermission(code: PlatformPermissionCode): void {
    if (this.editingRole()?.is_protected) return;
    this.selectedPermissions.update((current) => {
      const next = new Set(current);
      if (next.has(code)) next.delete(code);
      else next.add(code);
      return next;
    });
  }

  protected moduleFullySelected(moduleKey: string): boolean {
    const module = this.modules.find((item) => item.key === moduleKey);
    return !!module && module.permissions.every((permission) => this.isSelected(permission.code));
  }

  protected toggleModule(moduleKey: string): void {
    if (this.editingRole()?.is_protected) return;
    const module = this.modules.find((item) => item.key === moduleKey);
    if (!module) return;
    const selectAll = !this.moduleFullySelected(moduleKey);
    this.selectedPermissions.update((current) => {
      const next = new Set(current);
      module.permissions.forEach((permission) =>
        selectAll ? next.add(permission.code) : next.delete(permission.code),
      );
      return next;
    });
  }

  protected saveRole(): void {
    if (this.roleForm.invalid) {
      this.roleForm.markAllAsTouched();
      return;
    }
    const permissions = ALL_PERMISSIONS.filter((code) => this.isSelected(code));
    if (!permissions.length) {
      this.roleError.set('Selecciona al menos un permiso.');
      return;
    }
    const role = this.editingRole();
    const raw = this.roleForm.getRawValue();
    this.savingRole.set(true);
    this.roleError.set('');
    this.team
      .saveRole({ name: raw.name.trim(), description: raw.description.trim(), permissions }, role?.id)
      .subscribe({
        next: (saved) => {
          this.roles.update((all) =>
            role ? all.map((item) => (item.id === saved.id ? saved : item)) : [...all, saved],
          );
          this.savingRole.set(false);
          this.roleEditorOpen.set(false);
          this.success.set(role ? `Se actualizó el rol ${saved.name}.` : `Se creó el rol ${saved.name}.`);
        },
        error: (error: HttpErrorResponse) => {
          this.savingRole.set(false);
          const detail = error.error?.detail;
          const ownRole = String(detail ?? '').includes('own role');
          this.roleError.set(
            error.status !== 409
              ? 'No fue posible guardar el rol. Revisa los datos e intenta nuevamente.'
              : detail?.code === 'duplicate_permissions'
                ? `El rol ${detail.role_name} ya tiene exactamente estos permisos. Usa ese rol o ajusta los permisos.`
                : ownRole
                ? 'No puedes modificar el rol que tienes asignado.'
                : 'Ya existe un rol de plataforma con ese nombre.',
          );
        },
      });
  }

  protected confirmDeleteRole(): void {
    const role = this.roleToDelete();
    if (!role) return;
    this.processing.set(true);
    this.dialogError.set('');
    this.team.deleteRole(role.id).subscribe({
      next: () => {
        this.roles.update((all) => all.filter((item) => item.id !== role.id));
        this.closeDialogs();
        this.success.set(`Se eliminó el rol ${role.name}.`);
      },
      error: (error: HttpErrorResponse) => {
        this.processing.set(false);
        this.dialogError.set(
          error.status === 409
            ? 'No se puede eliminar: es un rol inicial o tiene integrantes asignados.'
            : 'No fue posible eliminar el rol.',
        );
      },
    });
  }

  // --- Utilidades ------------------------------------------------------------

  protected closeDialogs(): void {
    this.processing.set(false);
    this.dialogError.set('');
    this.memberToToggle.set(null);
    this.roleToDelete.set(null);
    this.inviteOpen.set(false);
    this.roleEditorOpen.set(false);
  }

  protected initials(member: PlatformMember): string {
    return (member.full_name || member.email).slice(0, 2).toUpperCase();
  }

  protected date(value: string): string {
    return new Intl.DateTimeFormat('es-MX', { dateStyle: 'medium' }).format(new Date(value));
  }

  /** Nadie puede modificar el rol que tiene asignado. */
  protected isOwnRole(role: PlatformRole): boolean {
    return role.id === this.access.member()?.role_id;
  }


  private conflictMessage(error: HttpErrorResponse, fallback: string): string {
    if (error.status !== 409) return fallback;
    const detail = String(error.error?.detail ?? '');
    if (detail.includes('superadmin')) return 'La plataforma debe conservar al menos un Superadministrador activo.';
    if (detail.includes('owner')) return 'La cuenta principal de la plataforma no se puede cambiar de rol ni desactivar.';
    if (detail.includes('own')) return 'No puedes cambiar tu propio rol ni desactivar tu propia cuenta.';
    return fallback;
  }

  private replaceMember(updated: PlatformMember): void {
    this.members.update((all) => all.map((item) => (item.id === updated.id ? updated : item)));
  }

  private bumpRoleCount(roleId: string, delta: number): void {
    this.roles.update((all) =>
      all.map((role) => (role.id === roleId ? { ...role, member_count: role.member_count + delta } : role)),
    );
  }

  private clearMessages(): void {
    this.success.set('');
    this.error.set('');
  }
}
