import { Component, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';

import { PlatformMember } from '../../../core/models/auth.models';
import { AuthService } from '../../../core/services/auth.service';

@Component({
  selector: 'app-platform-team-page',
  imports: [ReactiveFormsModule],
  templateUrl: './platform-team-page.html',
  styleUrl: './platform-team-page.scss',
})
export class PlatformTeamPage {
  private readonly service = inject(AuthService);
  private readonly fb = inject(FormBuilder);
  protected readonly members = signal<PlatformMember[]>([]);
  protected readonly loading = signal(true);
  protected readonly sending = signal(false);
  protected readonly error = signal('');
  protected readonly created = signal<PlatformMember | null>(null);
  protected readonly form = this.fb.nonNullable.group({
    full_name: ['', [Validators.required, Validators.minLength(3)]],
    email: ['', [Validators.required, Validators.email]],
    role: ['viewer' as const],
  });
  constructor(){this.load()}
  protected submit():void{if(this.form.invalid){this.form.markAllAsTouched();return}this.sending.set(true);this.error.set('');this.created.set(null);this.service.invitePlatformMember(this.form.getRawValue()).subscribe({next:(x)=>{this.members.update((all)=>[...all,x]);this.created.set(x);this.form.reset({full_name:'',email:'',role:'viewer'});this.sending.set(false)},error:(e)=>{this.error.set(e.status===409?'Ese correo ya tiene una cuenta de plataforma.':'No fue posible enviar la invitación.');this.sending.set(false)}})}
  protected role(value:string):string{return value==='superadmin'?'Superadministrador':'Consulta de plataforma'}
  protected date(value:string):string{return new Intl.DateTimeFormat('es-MX',{dateStyle:'medium'}).format(new Date(value))}
  protected async copy():Promise<void>{const link=this.created()?.invitation_link;if(link)await navigator.clipboard.writeText(link)}
  private load():void{this.service.listPlatformTeam().subscribe({next:(x)=>{this.members.set(x);this.loading.set(false)},error:()=>{this.error.set('No fue posible consultar el equipo de plataforma.');this.loading.set(false)}})}
}
