import { Component, computed, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { LossReason, Opportunity, OpportunityStage } from '../../core/models/opportunity.models';
import { PERMISSIONS } from '../../core/models/permission.models';
import { OpportunityService } from '../../core/services/opportunity.service';
import { SessionService } from '../../core/services/session.service';

@Component({selector:'app-opportunity-board-page',imports:[RouterLink],templateUrl:'./opportunity-board-page.html',styleUrl:'./opportunity-board-page.scss'})
export class OpportunityBoardPage {
  private readonly service=inject(OpportunityService); private readonly user=inject(SessionService).getUser();
  protected readonly stages:Array<{key:OpportunityStage;label:string}>=[{key:'prospecting',label:'Prospecto'},{key:'contact',label:'Contacto'},{key:'proposal',label:'Propuesta'},{key:'negotiation',label:'Negociación'},{key:'won',label:'Ganada'},{key:'lost',label:'Perdida'}];
  protected readonly openStages=this.stages.slice(0,4);
  protected readonly lossReasons:Array<{key:LossReason;label:string}>=[{key:'price',label:'Precio'},{key:'no_response',label:'Sin respuesta'},{key:'competitor',label:'Eligió a un competidor'},{key:'budget_cancelled',label:'Presupuesto cancelado'},{key:'not_qualified',label:'No era una oportunidad calificada'},{key:'other',label:'Otro'}];
  protected readonly items=signal<Opportunity[]>([]); protected readonly loading=signal(true); protected readonly error=signal(''); protected readonly search=signal(''); protected readonly showArchived=signal(false);
  protected readonly closing=signal<Opportunity|null>(null); protected readonly closingStage=signal<'won'|'lost'>('won'); protected readonly saving=signal(false);
  protected readonly canCreate=this.has(PERMISSIONS.opportunitiesCreate); protected readonly canUpdate=this.has(PERMISSIONS.opportunitiesUpdate); protected readonly canClose=this.has(PERMISSIONS.opportunitiesClose); protected readonly canArchive=this.has(PERMISSIONS.opportunitiesArchive);
  protected readonly visible=computed(()=>{const q=this.search().trim().toLowerCase();return this.items().filter(x=>(this.showArchived()||!x.archived)&&(!q||`${x.name} ${x.client_name} ${x.owner_name}`.toLowerCase().includes(q)));});
  constructor(){this.load()}
  protected load(){this.loading.set(true);this.service.list(true).subscribe({next:v=>{this.items.set(v);this.loading.set(false)},error:()=>{this.error.set('No fue posible consultar las oportunidades.');this.loading.set(false)}})}
  protected byStage(stage:OpportunityStage){return this.visible().filter(item=>item.stage===stage)}
  protected total(stage:OpportunityStage){return this.byStage(stage).reduce((sum,item)=>sum+Number(item.amount),0)}
  protected updateSearch(event:Event){this.search.set((event.target as HTMLInputElement).value)}
  protected changeStage(item:Opportunity,event:Event){const stage=(event.target as HTMLSelectElement).value as OpportunityStage;this.service.updateStage(item.id,stage).subscribe({next:value=>this.replace(value),error:()=>{this.error.set('No fue posible cambiar la etapa.');(event.target as HTMLSelectElement).value=item.stage}})}
  protected openClose(item:Opportunity,stage:'won'|'lost'){this.closing.set(item);this.closingStage.set(stage);this.error.set('')}
  protected cancelClose(){if(!this.saving())this.closing.set(null)}
  protected submitClose(event:Event){event.preventDefault();const form=new FormData(event.target as HTMLFormElement);const stage=this.closingStage();const reason=form.get('loss_reason') as LossReason|null;if(stage==='lost'&&!reason){this.error.set('Selecciona el motivo por el que se perdió la oportunidad.');return}const item=this.closing();if(!item)return;this.saving.set(true);this.service.close(item.id,stage,stage==='lost'?reason:null,stage==='lost'?String(form.get('loss_detail')||''):null).subscribe({next:value=>{this.replace(value);this.closing.set(null);this.saving.set(false)},error:()=>{this.error.set('No fue posible cerrar la oportunidad.');this.saving.set(false)}})}
  protected archive(item:Opportunity){if(!confirm(`¿Archivar la oportunidad “${item.name}”? Podrás restaurarla después.`))return;this.service.archive(item.id).subscribe({next:value=>this.replace(value),error:()=>this.error.set('No fue posible archivar la oportunidad.')})}
  protected restore(item:Opportunity){this.service.restore(item.id).subscribe({next:value=>this.replace(value),error:()=>this.error.set('No fue posible restaurar la oportunidad.')})}
  protected toggleArchived(event:Event){this.showArchived.set((event.target as HTMLInputElement).checked)}
  protected money(value:number){return new Intl.NumberFormat('es-MX',{style:'currency',currency:'MXN',maximumFractionDigits:0}).format(value)}
  private replace(item:Opportunity){this.items.update(values=>values.map(value=>value.id===item.id?item:value));this.error.set('')}
  private has(permission:(typeof PERMISSIONS)[keyof typeof PERMISSIONS]){return this.user?.role==='admin'||Boolean(this.user?.permissions?.includes(permission))}
}
