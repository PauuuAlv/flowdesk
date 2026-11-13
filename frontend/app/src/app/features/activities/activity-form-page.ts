import { Component, computed, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { ActivityType, SaveActivityRequest } from '../../core/models/activity.models';
import { Client } from '../../core/models/client.models';
import { Opportunity, OpportunityAssignee } from '../../core/models/opportunity.models';
import { ActivityService } from '../../core/services/activity.service';
import { ClientService } from '../../core/services/client.service';
import { OpportunityService } from '../../core/services/opportunity.service';

@Component({selector:'app-activity-form-page',imports:[ReactiveFormsModule,RouterLink],templateUrl:'./activity-form-page.html',styleUrl:'./activity-form-page.scss'})
export class ActivityFormPage {
  private readonly fb=inject(FormBuilder); private readonly service=inject(ActivityService); private readonly clientsService=inject(ClientService); private readonly opportunitiesService=inject(OpportunityService); private readonly route=inject(ActivatedRoute); private readonly router=inject(Router);
  protected readonly id=this.route.snapshot.paramMap.get('activityId'); protected readonly clients=signal<Client[]>([]); protected readonly opportunities=signal<Opportunity[]>([]); protected readonly assignees=signal<OpportunityAssignee[]>([]); protected readonly selectedClient=signal(''); protected readonly loading=signal(true); protected readonly saving=signal(false); protected readonly error=signal('');
  protected readonly form=this.fb.nonNullable.group({client_id:['',Validators.required],opportunity_id:[''],owner_user_id:['',Validators.required],activity_type:['task' as ActivityType,Validators.required],title:['',[Validators.required,Validators.minLength(3),Validators.maxLength(140)]],description:['',Validators.maxLength(1000)],scheduled_at:['',Validators.required]});
  protected readonly availableOpportunities=computed(()=>this.opportunities().filter(x=>x.client_id===this.selectedClient()&&!x.archived));
  constructor(){let pending=3;const done=()=>{pending--;if(!pending)this.id?this.load(this.id):this.loading.set(false)};this.clientsService.list().subscribe({next:x=>{this.clients.set(x.filter(c=>c.status==='active'));done()},error:()=>this.fail()});this.opportunitiesService.list().subscribe({next:x=>{this.opportunities.set(x);done()},error:()=>this.fail()});this.opportunitiesService.assignees().subscribe({next:x=>{this.assignees.set(x);if(x.length&&!this.form.controls.owner_user_id.value)this.form.controls.owner_user_id.setValue(x[0].id);done()},error:()=>this.fail()});this.form.controls.client_id.valueChanges.subscribe(value=>{this.selectedClient.set(value);this.form.controls.opportunity_id.setValue('')})}
  protected submit(){if(this.form.invalid){this.form.markAllAsTouched();return}const v=this.form.getRawValue();const body:SaveActivityRequest={...v,opportunity_id:v.opportunity_id||null,description:v.description.trim()||null,title:v.title.trim(),scheduled_at:new Date(v.scheduled_at).toISOString()};this.saving.set(true);this.service.save(body,this.id??undefined).subscribe({next:()=>void this.router.navigate(['/panel/actividades']),error:()=>{this.error.set('No fue posible guardar la actividad. Revisa los datos e intenta nuevamente.');this.saving.set(false)}})}
  private load(id:string){this.service.get(id).subscribe({next:x=>{this.form.setValue({client_id:x.client_id,opportunity_id:'',owner_user_id:x.owner_user_id,activity_type:x.activity_type,title:x.title,description:x.description??'',scheduled_at:this.toLocal(x.scheduled_at)});this.selectedClient.set(x.client_id);this.form.controls.opportunity_id.setValue(x.opportunity_id??'');this.loading.set(false)},error:()=>this.fail()})}
  private toLocal(value:string){const d=new Date(value);d.setMinutes(d.getMinutes()-d.getTimezoneOffset());return d.toISOString().slice(0,16)}
  private fail(){this.loading.set(false);this.error.set('No fue posible cargar la información necesaria.')}
}
