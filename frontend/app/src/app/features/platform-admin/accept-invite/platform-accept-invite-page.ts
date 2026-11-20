import { Component, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';

import { AuthService } from '../../../core/services/auth.service';
import { SessionService } from '../../../core/services/session.service';
import { getPasswordChecks, strongPasswordValidator } from '../../../core/validators/password.validator';

@Component({selector:'app-platform-accept-invite-page',imports:[ReactiveFormsModule],templateUrl:'./platform-accept-invite-page.html',styleUrl:'./platform-accept-invite-page.scss'})
export class PlatformAcceptInvitePage{
  private readonly fb=inject(FormBuilder);private readonly auth=inject(AuthService);private readonly session=inject(SessionService);private readonly router=inject(Router);private readonly token=inject(ActivatedRoute).snapshot.queryParamMap.get('token')??'';
  protected readonly sending=signal(false);protected readonly error=signal('');protected readonly show=signal(false);protected readonly form=this.fb.nonNullable.group({password:['',[Validators.required,strongPasswordValidator]],confirmation:['',Validators.required]});
  protected checks(){return getPasswordChecks(this.form.controls.password.value)}protected mismatch(){const v=this.form.getRawValue();return !!v.confirmation&&v.password!==v.confirmation}
  protected submit(){if(!this.token){this.error.set('El enlace no contiene un token válido.');return}if(this.form.invalid||this.mismatch()){this.form.markAllAsTouched();this.error.set(this.mismatch()?'Las contraseñas no coinciden.':'Revisa los requisitos de la contraseña.');return}this.sending.set(true);this.auth.acceptPlatformInvitation(this.token,this.form.controls.password.value).subscribe({next:(x)=>{this.session.savePlatformAdminToken(x);void this.router.navigate(['/administracion-flowdesk'])},error:()=>{this.error.set('La invitación es inválida, venció o ya fue utilizada.');this.sending.set(false)}})}
}
