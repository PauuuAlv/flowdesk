import {Component,computed,inject,signal} from '@angular/core';
import {RouterLink} from '@angular/router';
import {DashboardPipelineStage,DashboardSummary} from '../../core/models/dashboard.models';
import {PERMISSIONS} from '../../core/models/permission.models';
import {DashboardService} from '../../core/services/dashboard.service';
import {SessionService} from '../../core/services/session.service';

@Component({selector:'app-dashboard-page',imports:[RouterLink],templateUrl:'./dashboard-page.html',styleUrl:'./dashboard-page.scss'})
export class DashboardPage {
  private readonly service=inject(DashboardService);
  private readonly session=inject(SessionService);
  protected readonly user=this.session.getUser();
  protected readonly summary=signal<DashboardSummary|null>(null);
  protected readonly loading=signal(true);
  protected readonly error=signal('');
  protected readonly maxPipelineValue=computed(()=>Math.max(...(this.summary()?.pipeline.map(x=>Number(x.value))??[]),1));
  protected readonly canCreateClient=this.has(PERMISSIONS.clientsCreate);
  protected readonly canCreateOpportunity=this.has(PERMISSIONS.opportunitiesCreate);
  protected readonly canCreateActivity=this.has(PERMISSIONS.activitiesCreate);
  protected readonly canCreateQuote=this.has(PERMISSIONS.quotesCreate);
  constructor(){this.load()}
  protected load(){this.loading.set(true);this.error.set('');this.service.getSummary().subscribe({next:x=>{this.summary.set(x);this.loading.set(false)},error:()=>{this.error.set('No fue posible cargar el resumen de tu empresa.');this.loading.set(false)}})}
  protected money(value:number){return new Intl.NumberFormat('es-MX',{style:'currency',currency:'MXN',maximumFractionDigits:2}).format(value)}
  protected date(value:string){return new Intl.DateTimeFormat('es-MX',{dateStyle:'medium',timeStyle:'short'}).format(new Date(value))}
  protected pipelineWidth(item:DashboardPipelineStage){return Math.max((Number(item.value)/this.maxPipelineValue())*100,item.count?7:0)}
  protected stageLabel(stage:DashboardPipelineStage['stage']){return{prospecting:'Prospección',qualification:'Calificación',proposal:'Propuesta',negotiation:'Negociación'}[stage]}
  protected activityType(type:string){return{call:'Llamada',email:'Correo',meeting:'Reunión',task:'Tarea'}[type]??type}
  protected quoteStatus(status:string){return{draft:'Borrador',sent:'Enviada',accepted:'Aceptada',rejected:'Rechazada',expired:'Vencida'}[status]??status}
  private has(permission:(typeof PERMISSIONS)[keyof typeof PERMISSIONS]){return this.user?.role==='admin'||Boolean(this.user?.permissions?.includes(permission))}
}
