import { Component, computed, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { Opportunity, OpportunityStage } from '../../core/models/opportunity.models';
import { PERMISSIONS } from '../../core/models/permission.models';
import { OpportunityService } from '../../core/services/opportunity.service';
import { SessionService } from '../../core/services/session.service';

@Component({selector:'app-opportunity-board-page',imports:[RouterLink],templateUrl:'./opportunity-board-page.html',styleUrl:'./opportunity-board-page.scss'})
export class OpportunityBoardPage {
  private readonly service=inject(OpportunityService); private readonly user=inject(SessionService).getUser();
  protected readonly stages:Array<{key:OpportunityStage;label:string}>=[{key:'prospecting',label:'Prospecto'},{key:'contact',label:'Contacto'},{key:'proposal',label:'Propuesta'},{key:'negotiation',label:'Negociación'},{key:'won',label:'Ganado'},{key:'lost',label:'Perdido'}];
  protected readonly items=signal<Opportunity[]>([]); protected readonly loading=signal(true); protected readonly error=signal(''); protected readonly search=signal('');
  protected readonly canCreate=this.has(PERMISSIONS.opportunitiesCreate); protected readonly canUpdate=this.has(PERMISSIONS.opportunitiesUpdate); protected readonly canClose=this.has(PERMISSIONS.opportunitiesClose);
  protected readonly visible=computed(()=>{const q=this.search().trim().toLowerCase();return this.items().filter(x=>!q||`${x.name} ${x.client_name} ${x.owner_name}`.toLowerCase().includes(q));});
  constructor(){this.load();}
  protected load(){this.loading.set(true);this.service.list().subscribe({next:v=>{this.items.set(v);this.loading.set(false)},error:()=>{this.error.set('No fue posible consultar las oportunidades.');this.loading.set(false)}})}
  protected byStage(stage:OpportunityStage){return this.visible().filter(x=>x.stage===stage)}
  protected total(stage:OpportunityStage){return this.byStage(stage).reduce((sum,x)=>sum+Number(x.amount),0)}
  protected updateSearch(e:Event){this.search.set((e.target as HTMLInputElement).value)}
  protected changeStage(item:Opportunity,e:Event){const stage=(e.target as HTMLSelectElement).value as OpportunityStage;if((stage==='won'||stage==='lost')&&!this.canClose){this.error.set('No tienes permiso para cerrar oportunidades.');(e.target as HTMLSelectElement).value=item.stage;return}this.service.updateStage(item.id,stage).subscribe({next:u=>this.items.update(v=>v.map(x=>x.id===u.id?u:x)),error:()=>{this.error.set('No fue posible cambiar la etapa.');(e.target as HTMLSelectElement).value=item.stage;}})}
  protected money(value:number){return new Intl.NumberFormat('es-MX',{style:'currency',currency:'MXN',maximumFractionDigits:0}).format(value)}
  private has(p:(typeof PERMISSIONS)[keyof typeof PERMISSIONS]){return this.user?.role==='admin'||Boolean(this.user?.permissions?.includes(p))}
}
