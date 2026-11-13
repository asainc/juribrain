/** Painel de demandas: filtros explícitos e permissões sempre validadas novamente pela API. */
import {CommonModule} from '@angular/common';
import {Component,inject,OnInit,signal} from '@angular/core';
import {FormsModule} from '@angular/forms';
import {RouterLink} from '@angular/router';
import {firstValueFrom} from 'rxjs';
import {BjnDemandApiService,DemandConfiguration,DemandSummary} from '../../core/bjn-demand-api.service';
import {demandStatusLabels,friendlyApiError,readableDate,selectableStatuses} from './demand-ui';
import {BjnSearchableSelectComponent} from './searchable-select.component';

@Component({selector:'app-bjn-demand-list',standalone:true,imports:[CommonModule,FormsModule,RouterLink,BjnSearchableSelectComponent],template:`
<main class="demand-shell demand-management-page">
  <nav class="demand-crumb" aria-label="Navegação"><a routerLink="/bjn">BJN</a><span aria-hidden="true">/</span><strong>Demandas</strong></nav>
  <header class="demand-heading demand-management-header">
    <div><span class="eyebrow">BJN / CENTRAL DE ATENDIMENTO JURÍDICO</span>
      <h1>Gestão de demandas</h1>
      <p>Uma visão organizada das solicitações, pendências e responsáveis pelo atendimento.</p>
    </div>
    <a routerLink="/bjn/demandas/nova" class="primary demand-new-action"><span aria-hidden="true">+</span> Nova demanda</a>
  </header>

  <section class="demand-overview" aria-label="Indicadores dos resultados exibidos">
    <article class="surface demand-overview-card">
      <span class="demand-overview-icon" aria-hidden="true">01</span>
      <div><small>Demandas nesta consulta</small><strong>{{loaded()?items().length:'—'}}</strong><span>Resultado dos filtros aplicados</span></div>
    </article>
    <article class="surface demand-overview-card">
      <span class="demand-overview-icon" aria-hidden="true">02</span>
      <div><small>Não concluídas</small><strong>{{loaded()?pendingCount():'—'}}</strong><span>Incluindo em atendimento e triagem</span></div>
    </article>
    <article class="surface demand-overview-card">
      <span class="demand-overview-icon" aria-hidden="true">03</span>
      <div><small>Sem advogado designado</small><strong>{{loaded()?unassignedCount():'—'}}</strong><span>Entre as demandas consultadas</span></div>
    </article>
    <article class="surface demand-overview-card">
      <span class="demand-overview-icon" aria-hidden="true">04</span>
      <div><small>Em análise</small><strong>{{loaded()?inAnalysisCount():'—'}}</strong><span>Entre as demandas consultadas</span></div>
    </article>
  </section>

  <section class="surface demand-list-card" aria-labelledby="demand-list-title">
    <div class="demand-panel-heading">
      <div><span class="eyebrow">PAINEL DE ACOMPANHAMENTO</span><h2 id="demand-list-title">Solicitações jurídicas</h2>
        <p>{{configuration()?.actor?.role==='admin'?'Visão de gestão: demandas de todos os responsáveis.':'Visão do advogado: solicitações disponíveis para o seu perfil.'}}</p>
      </div>
      <span class="demand-scope-tag">{{configuration()?.actor?.role==='admin'?'Visão gestor':'Visão advogado'}}</span>
    </div>
    <div class="bjn-demand-tabs" role="tablist" aria-label="Visualização das demandas">
      <button role="tab" type="button" [attr.aria-selected]="tab()==='all'" (click)="switchTab('all')">Todas as demandas</button>
      <button role="tab" type="button" [attr.aria-selected]="tab()==='pending'" (click)="switchTab('pending')">Pendentes <span class="demand-tab-hint">Não concluídas</span></button>
    </div>

    <div class="demand-search-section">
      <form class="demand-search-primary" (submit)="onSearchSubmit($event)">
        <label class="demand-search-input-group" for="search-demands"><span>Pesquisar demanda</span>
          <input id="search-demands" placeholder="Número, título ou área de consulta" [(ngModel)]="search" name="search" maxlength="160" />
        </label>
        <label class="demand-search-input-group demand-search-status" for="filter-status"><span>Status</span>
          <select id="filter-status" [(ngModel)]="status" name="status"><option value="">Todos os status</option>
            @for(value of statuses;track value){<option [value]="value">{{labels[value]}}</option>}
          </select>
        </label>
        <label class="demand-search-input-group demand-search-nature" for="filter-nature"><span>Assunto / natureza</span>
          <select id="filter-nature" [(ngModel)]="nature" name="nature"><option value="">Todas as naturezas</option>
            @for(value of configuration()?.available_natures||[];track value){<option [value]="value">{{value}}</option>}
          </select>
        </label>
        <button type="submit" class="primary demand-search-submit" [disabled]="busy()">{{busy()?'Buscando…':'Buscar'}}</button>
        <button type="button" class="demand-filter-trigger" [attr.aria-expanded]="advancedFilters()" aria-controls="demand-advanced-filters" (click)="advancedFilters.set(!advancedFilters())">
          Filtros avançados @if(activeFilterCount()){<span class="demand-filter-counter">{{activeFilterCount()}}</span>}
          <span aria-hidden="true">{{advancedFilters()?'−':'+'}}</span>
        </button>
      </form>
      @if(activeFilterCount() || search.trim() || status){
        <div class="demand-active-filters"><span>Filtros preenchidos: {{activeFilterCount() + (search.trim()?1:0) + (status?1:0)}}</span>
          <button type="button" (click)="clearFilters()" [disabled]="busy()">Limpar filtros</button>
        </div>
      }
      @if(advancedFilters()){
        <div class="bjn-search-extra bjn-filters-extended" id="demand-advanced-filters" aria-label="Filtros avançados">
          <label>Data inicial <input type="date" [(ngModel)]="fromDate" /></label>
          <label>Data final <input type="date" [(ngModel)]="toDate" /></label>
          <label>Advogado responsável
            <input maxlength="120" [(ngModel)]="lawyer" list="bjn-lawyer-options" placeholder="Nome ou e-mail" />
            <datalist id="bjn-lawyer-options">@for(option of configuration()?.lawyer_options||[];track option.email){<option [value]="option.name">{{option.email}}</option>}</datalist>
          </label>
          <div class="bjn-filter-field"><label for="bjn-agency-options">Agência</label>
            <app-bjn-searchable-select inputId="bjn-agency-options" ariaLabel="Filtrar por agência"
              [options]="configuration()?.agency_options || []" [value]="branch" (valueChange)="branch=$event"
              [allowCustomValue]="true" placeholder="Código ou nome da agência" />
          </div>
          <label>Usuário solicitante <input maxlength="120" [(ngModel)]="registeredEmail" placeholder="Nome ou e-mail" /></label>
          <label>CPF do cliente <input maxlength="14" inputmode="numeric" [(ngModel)]="clientCPF" placeholder="Busca protegida" /></label>
          <div class="demand-filter-actions"><button type="button" class="primary" (click)="load()" [disabled]="busy()">Aplicar filtros</button><button type="button" (click)="clearFilters()" [disabled]="busy()">Limpar tudo</button></div>
        </div>
      }
    </div>

    @if(configuration()?.actor?.role==='admin' && tab()==='all'){
      <div class="bjn-bulk-panel" aria-label="Distribuição de demandas em lote">
        <div class="bjn-bulk-copy"><strong>Distribuição em lote <span class="demand-selection-chip">{{selectedIds().length}} selecionadas</span></strong>
          <p>Marque até 50 demandas elegíveis na tabela e escolha o advogado que receberá o lote. A operação é registrada no histórico.</p>
        </div>
        <label class="bjn-bulk-field">Advogado de destino
          <select [(ngModel)]="assignedLawyer" aria-label="Advogado de destino"><option value="">Selecione o responsável</option>
            @for(option of configuration()?.lawyer_options||[];track option.email){<option [value]="option.email">{{option.name}} · {{option.email}}</option>}
          </select>
        </label>
        <button class="primary" type="button" [disabled]="!selectedIds().length||!assignedLawyer||assigning()" (click)="assignSelected()">
          {{assigning()?'Distribuindo…':'Distribuir '+selectedIds().length+' demanda(s)'}}
        </button>
      </div>
      @if(scopeExclusionId()){
        <div class="bjn-scope-exclusion bjn-list-exclusion" role="region" aria-label="Confirmar exclusão por fora do escopo">
          <strong>Excluir do fluxo: {{scopeExclusionName()}}</strong>
          <p>A demanda ficará identificada como “Excluída — fora do escopo” em “Todas as demandas”, inclusive ao selecionar “Todos os status”, mas não será exibida em “Pendentes”. A justificativa, o protocolo e os documentos serão preservados para auditoria.</p>
          <label for="list-scope-reason">Justificativa obrigatória (10–300 caracteres)</label>
          <textarea id="list-scope-reason" [(ngModel)]="scopeExclusionReason" maxlength="300" rows="3" placeholder="Por que esta demanda está fora do escopo?"></textarea>
          <div class="bjn-exclusion-actions">
            <button type="button" (click)="cancelExclusion()" [disabled]="excluding()">Cancelar</button>
            <button type="button" class="bjn-exclusion-confirm" [disabled]="excluding()||scopeExclusionReason.trim().length<10" (click)="confirmExclusion()">{{excluding()?'Registrando…':'Confirmar exclusão'}}</button>
          </div>
        </div>
      }
      @if(bulkSuccess()){<p class="bjn-bulk-feedback" role="status">{{bulkSuccess()}}</p>}
    }
    <div class="demand-table-heading">
      <div><strong>{{tab()==='pending'?'Demandas pendentes':'Lista de demandas'}}</strong><span>{{items().length}} registro(s) na consulta</span></div>
      @if(tab()==='pending'){<span class="demand-scope-tag">{{configuration()?.actor?.role==='advogado'?'Somente minhas pendências':'Pendências da equipe'}}</span>}
    </div>
    @if(error()){<p class="demand-error" role="alert">{{error()}} <button type="button" (click)="load()">Tentar novamente</button></p>}
    @if(busy()){<p class="demand-loading" role="status">Carregando demandas…</p>}
    @else if(!items().length){<div class="demand-empty"><span aria-hidden="true" class="demand-empty-icon">▤</span><h3>Nenhuma demanda encontrada</h3>
      <p>{{tab()==='pending'?'Não há pendências para os filtros e o perfil atual.':'Ajuste os filtros ou cadastre uma nova solicitação.'}}</p>
      <button type="button" class="demand-outlined" (click)="clearFilters()">Limpar filtros</button></div>}
    @else {<div class="demand-table-scroll"><table class="demand-table"><thead><tr>
      @if(configuration()?.actor?.role==='admin' && tab()==='all'){
        <th scope="col" class="bjn-select-cell"><label class="sr-only" for="select-all-bjn">Selecionar todas as elegíveis</label>
        <input id="select-all-bjn" type="checkbox" [checked]="allEligibleSelected()" (change)="toggleAll($any($event.target).checked)" /></th>}
      <th scope="col">Demanda</th><th scope="col">Área</th><th scope="col">Assunto / natureza</th><th scope="col">Status</th><th scope="col">Responsável</th><th scope="col">Cadastro</th><th scope="col">Atualização</th><th scope="col"><span class="sr-only">Ações</span></th></tr></thead>
      <tbody>@for(item of items();track item.id){<tr>
        @if(configuration()?.actor?.role==='admin' && tab()==='all'){
          <td class="bjn-select-cell"><input type="checkbox" [disabled]="!eligible(item)" [checked]="selectedIds().includes(item.id)" [attr.aria-label]="'Selecionar '+item.id" (change)="toggle(item.id,$any($event.target).checked)" /></td>
        }
        <td class="demand-title-cell"><a class="demand-strong-link" [routerLink]="['/bjn/demandas',item.id]">{{item.title}}</a><small>Protocolo {{item.id}}</small></td>
        <td>{{item.consult_area}}</td><td>{{item.service_nature}}</td><td><span class="demand-pill" [attr.data-status]="item.status">{{labels[item.status]}}</span></td>
        <td><span class="demand-lawyer"><span class="demand-avatar" aria-hidden="true">{{initials(item.lawyer_name||item.lawyer_email||'—')}}</span><span>{{item.lawyer_name || item.lawyer_email || 'Aguardando distribuição'}}</span></span></td>
        <td class="demand-date-cell">{{date(item.created_at)}}</td><td class="demand-date-cell">{{date(item.updated_at)}}</td>
        <td><div class="bjn-row-actions"><a class="demand-table-link" [routerLink]="['/bjn/demandas',item.id]" [attr.aria-label]="'Acompanhar '+item.id">Abrir <span aria-hidden="true">↗</span></a>
          @if(configuration()?.actor?.role==='admin' && tab()==='all' && canExclude(item)){
            <button type="button" class="bjn-row-exclude" (click)="startExclusion(item)" [attr.aria-label]="'Excluir demanda fora do escopo: '+item.id">Excluir</button>
          }
        </div></td></tr>}
      </tbody></table></div>}
    <footer class="demand-table-footer"><span>Os indicadores refletem somente os registros retornados pelos filtros atuais.</span><span>Atualize a consulta para ver alterações recentes.</span></footer>
  </section>
</main>`})
export class BjnDemandListComponent implements OnInit {
  private readonly api=inject(BjnDemandApiService);
  readonly items=signal<DemandSummary[]>([]);
  readonly configuration=signal<DemandConfiguration|null>(null);
  readonly busy=signal(true);
  readonly loaded=signal(false);
  readonly maxBulkSelection=50;
  readonly assigning=signal(false);
  readonly error=signal('');
  readonly bulkSuccess=signal('');
  readonly selectedIds=signal<string[]>([]);
  readonly scopeExclusionId=signal('');
  readonly scopeExclusionName=signal('');
  readonly excluding=signal(false);
  scopeExclusionReason='';
  readonly tab=signal<'all'|'pending'>('all');
  readonly advancedFilters=signal(false);
  readonly statuses=selectableStatuses;
  readonly labels=demandStatusLabels;
  readonly date=readableDate;
  search='';status='';nature='';fromDate='';toDate='';branch='';registeredEmail='';clientCPF='';lawyer='';assignedLawyer='';

  ngOnInit():void{void this.initialize();}
  private async initialize():Promise<void>{
    try {this.configuration.set(await firstValueFrom(this.api.configuration()));}
    catch(error){this.busy.set(false);this.error.set(friendlyApiError(error));return;}
    await this.load();
  }
  switchTab(value:'all'|'pending'):void {
    this.tab.set(value);this.selectedIds.set([]);this.bulkSuccess.set('');this.cancelExclusion();
    if(value==='pending' && ['CONCLUIDA','CANCELADA','RESOLVIDA_IA','ENCAMINHADA_AREA','EXCLUIDA_ESCOPO'].includes(this.status)) this.status='';
    void this.load();
  }
  /** Só mostra a exclusão em protocolos ainda sem distribuição. */
  canExclude(item:DemandSummary):boolean {
    return !item.lawyer_email && ['RECEBIDA','EM_TRIAGEM','TRIAGEM_ADMINISTRATIVA'].includes(item.status);
  }
  startExclusion(item:DemandSummary):void {
    if(this.configuration()?.actor?.role!=='admin'||!this.canExclude(item))return;
    this.scopeExclusionId.set(item.id);this.scopeExclusionName.set(item.title);
    this.scopeExclusionReason='';this.error.set('');this.bulkSuccess.set('');
  }
  cancelExclusion():void {this.scopeExclusionId.set('');this.scopeExclusionName.set('');this.scopeExclusionReason='';}
  async confirmExclusion():Promise<void>{
    if(this.configuration()?.actor?.role!=='admin'||this.excluding()||!this.scopeExclusionId()||this.scopeExclusionReason.trim().length<10)return;
    this.excluding.set(true);this.error.set('');this.bulkSuccess.set('');
    const excludedId=this.scopeExclusionId();
    try{
      await firstValueFrom(this.api.excludeScope(excludedId,this.scopeExclusionReason.trim()));
      this.cancelExclusion();await this.load();
      this.bulkSuccess.set(`Demanda ${excludedId} excluída do fluxo. Justificativa preservada no histórico.`);
    }catch(cause){this.error.set(friendlyApiError(cause));}
    finally{this.excluding.set(false);}
  }
  eligible(item:DemandSummary):boolean {return !['CONCLUIDA','CANCELADA','RESOLVIDA_IA','ENCAMINHADA_AREA','EXCLUIDA_ESCOPO','TRIAGEM_ADMINISTRATIVA'].includes(item.status);}
  pendingCount():number {return this.items().filter(item=>!['CONCLUIDA','CANCELADA','RESOLVIDA_IA','ENCAMINHADA_AREA','EXCLUIDA_ESCOPO'].includes(item.status)).length;}
  unassignedCount():number {return this.items().filter(item=>item.status!=='EXCLUIDA_ESCOPO' && !item.lawyer_email && !item.lawyer_name).length;}
  inAnalysisCount():number {return this.items().filter(item=>item.status==='EM_ANALISE').length;}
  activeFilterCount():number {return [this.nature,this.fromDate,this.toDate,this.lawyer,this.branch,this.registeredEmail,this.clientCPF].filter(item=>item.trim()).length;}
  initials(name:string):string {return name==='—'?'?':name.trim().split(/\s+/).slice(0,2).map(part=>part[0]?.toUpperCase()||'').join('');}
  allEligibleSelected():boolean {
    const eligible=this.items().filter(item=>this.eligible(item)).slice(0,this.maxBulkSelection);
    return eligible.length>0&&eligible.every(item=>this.selectedIds().includes(item.id));
  }
  toggle(id:string,checked:boolean):void {
    if(checked && !this.selectedIds().includes(id) && this.selectedIds().length>=this.maxBulkSelection){
      this.error.set('O limite é de 50 demandas por lote. Conclua a distribuição atual antes de selecionar mais.');
      return;
    }
    this.error.set('');
    this.selectedIds.update(ids=>checked?[...new Set([...ids,id])]:ids.filter(item=>item!==id));
  }
  toggleAll(checked:boolean):void {
    this.error.set('');
    this.selectedIds.set(checked?this.items().filter(item=>this.eligible(item)).slice(0,this.maxBulkSelection).map(item=>item.id):[]);
  }
  onSearchSubmit(event:Event):void {event.preventDefault();void this.load();}
  clearFilters():void {this.search='';this.status='';this.nature='';this.fromDate='';this.toDate='';this.branch='';this.registeredEmail='';this.clientCPF='';this.lawyer='';void this.load();}
  async assignSelected():Promise<void>{
    if(!this.configuration() || this.configuration()!.actor.role!=='admin' || !this.assignedLawyer||!this.selectedIds().length||this.assigning())return;
    this.assigning.set(true);this.error.set('');this.bulkSuccess.set('');
    try{
      const result=await firstValueFrom(this.api.assignBulk(this.selectedIds(),this.assignedLawyer));
      this.bulkSuccess.set(`${result.assigned_count} demanda(s) atribuída(s) ao advogado selecionado. Operação registrada no histórico.`);
      this.selectedIds.set([]);
      await this.load();
    }catch(error){this.error.set(`Falha na distribuição em lote: ${friendlyApiError(error)}`);}
    finally{this.assigning.set(false);}
  }
  async load():Promise<void>{
    if(this.fromDate&&this.toDate&&this.fromDate>this.toDate){this.error.set('A data inicial deve ser anterior ou igual à data final.');return;}
    this.busy.set(true);this.loaded.set(false);this.error.set('');
    try{
      const result=await firstValueFrom(this.api.list(this.search,this.status,{
        from_date:this.fromDate,to_date:this.toDate,branch:this.branch,registered_email:this.registeredEmail,
        lawyer:this.lawyer,client_cpf:this.clientCPF,nature:this.nature,pending_only:this.tab()==='pending'
      }));
      this.items.set(result.items);
      this.loaded.set(true);
      this.selectedIds.set(this.selectedIds().filter(id=>result.items.some(item=>item.id===id&&this.eligible(item))));
    }catch(error){this.items.set([]);this.error.set(friendlyApiError(error));}
    finally{this.busy.set(false);}
  }
}
