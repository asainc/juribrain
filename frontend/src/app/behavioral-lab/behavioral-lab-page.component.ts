/** Behavior: jornada de projeto, execução e replay visual. */
import {CommonModule} from '@angular/common';
import {ChangeDetectorRef, Component, OnDestroy, OnInit, inject} from '@angular/core';
import {FormsModule} from '@angular/forms';
import {Subscription, forkJoin, interval} from 'rxjs';
import {BehavioralLabApiService, AgentDraft, SyntheticAgent, EntityType, Environment, EnvironmentDraft, Society, SocietyDraft,
  LabRun, LabEvent, LabConfiguration, SimulationConfiguration, EnvironmentChange, MetricDefinition, Experiment, ExperimentVariant, Calibration, Revision, DriftCheck} from './behavioral-lab-api.service';

type Tab = 'painel'|'agentes'|'ambientes'|'simulacoes'|'resultados'|'intelligence';
interface GraphNode {id:string;name:string;group:string;type:EntityType;x:number;y:number;stance:number;hasReaction:boolean}
interface GraphEdge {source:string;target:string;weight:number;active:boolean}

@Component({selector:'app-behavioral-lab-page',standalone:true,imports:[CommonModule,FormsModule],
  templateUrl:'./behavioral-lab-page.component.html'})
export class BehavioralLabPageComponent implements OnInit, OnDestroy {
  private readonly api=inject(BehavioralLabApiService);
  private readonly cdr=inject(ChangeDetectorRef);
  private readonly subscriptions=new Subscription();
  private graphCacheKey='';
  private graphCacheNodes:GraphNode[]=[];
  private graphCacheIndex=new Map<string,GraphNode>();
  private edgeCacheKey='';
  private edgeCache:GraphEdge[]=[];
  tab:Tab='painel';
  showAdvanced=false;selectedRepetition=1;followLive=true;playing=false;feedFilter:'all'|'conversations'|'environment'='all';filterSelectedAgent=false;
  sampleType:'comunidade'|'mercado'|'organizacao'='comunidade';
  generatorDescription='';generatorCount=6;
  experiments:Experiment[]=[];selectedExperiment:Experiment|null=null;calibrations:Calibration[]=[];
  experimentName='Comparação de cenários';experimentHypothesis='Avaliar mudanças sintéticas entre cenário base e alternativas, mantendo perfis e sementes.';
  variantDrafts:{name:string;parameter:string;value:number;variable:string;variableValue:string;impact:number}[]=[
    {name:'Alternativa A',parameter:'uncertainty',value:.35,variable:'',variableValue:'',impact:0}];
  sensitivityParameter:'uncertainty'|'social_pressure'|'shock_probability'|'network_density'='uncertainty';
  sensitivityMinimum=0.1;sensitivityMaximum=0.9;sensitivitySteps=3;
  metricDraft:MetricDefinition={key:'',label:'',kind:'number',description:'Indicador sintético do cenário',minimum:0,maximum:100,categories:[]};
  metricCategories='';actionKey='';actionOptions='';
  calibrationMean=50;calibrationSource='';calibrationSampleSize:number|null=null;calibrationReviewer='';
  selectedConversationSequence=0;itemRevisions:Revision[]=[];versionedName='';driftThreshold=10;driftResult:DriftCheck|null=null;
  readonly parameters=[{key:'uncertainty',label:'Incerteza'}, {key:'social_pressure',label:'Pressão social'},
    {key:'shock_probability',label:'Probabilidade de choque'}, {key:'shock_intensity',label:'Intensidade do choque'},
    {key:'network_density',label:'Densidade da rede'}, {key:'temperature',label:'Temperatura da IA'}];
  readonly tabs:{key:Tab;label:string;number:string}[]=[
    {key:'painel',label:'Studio · Criar',number:'01'}, {key:'agentes',label:'Agentes',number:'02'},
    {key:'ambientes',label:'Cenários',number:'03'}, {key:'simulacoes',label:'Observatory',number:'04'},
    {key:'resultados',label:'Resultados',number:'05'}, {key:'intelligence',label:'Intelligence',number:'06'}
  ];
  agents:SyntheticAgent[]=[];environments:Environment[]=[];societies:Society[]=[];runs:LabRun[]=[];
  configuration:LabConfiguration|null=null;
  selectedRun:LabRun|null=null;
  selectedAgentId='';selectedRound=1;busy=false;loading=true;pollBusy=false;notice='';error='';
  editAgentId='';editEnvironmentId='';editSocietyId='';
  agentDraft:AgentDraft=this.blankAgent();
  environmentDraft:EnvironmentDraft=this.blankEnvironment();
  societyDraft:SocietyDraft=this.blankSociety();
  characteristicKey='';characteristicValue='';variableKey='';variableValue='';
  eventDraft:EnvironmentChange={round:2,name:'',description:'',impact:0,variable_updates:{}};
  eventKey='';eventValue='';
  sim:SimulationConfiguration={environment_id:'',society_id:'',mode:'demo',rounds:3,repetitions:1,seed:42,
    temperature:0.2,uncertainty:0.2,social_pressure:0.55,shock_probability:0.15,shock_intensity:0.35,
    network_density:0.45,max_tokens_per_reaction:420,memory_window:4};
  readonly kinds:{value:EntityType;label:string}[]=[
    {value:'CLIENTE',label:'Cliente'}, {value:'PESSOA',label:'Pessoa'}, {value:'EMPRESA',label:'Empresa'},
    {value:'GOVERNO',label:'Entidade pública'}, {value:'AGENTE_IA',label:'Agente de IA'},
    {value:'ORGANIZACAO',label:'Organização / grupo'}, {value:'OUTRO',label:'Outra entidade'}];
  
  ngOnInit():void {
    this.refresh();
    // Polling curto apenas enquanto houver execução; a API retorna snapshots auditáveis.
    this.subscriptions.add(interval(1600).subscribe(()=>this.poll()));
    this.subscriptions.add(interval(1400).subscribe(()=>{if(this.playing)this.nextReplay();}));
    this.subscriptions.add(interval(3500).subscribe(()=>{if(this.selectedExperiment&&['QUEUED','RUNNING'].includes(this.selectedExperiment.status))this.loadExperiments();}));
  }
  ngOnDestroy():void{this.subscriptions.unsubscribe();}
  private blankAgent():AgentDraft{return {name:'',entity_type:'PESSOA',group:'Geral',goal:'',communication_style:'objetivo',initial_stance:50,influence:.5,susceptibility:.5,characteristics:{}};}
  private blankEnvironment():EnvironmentDraft{return {name:'',context:'',decision:'',success_criterion:'',target_behavior:'Apoiar a decisão apresentada',low_label:'Resistência',middle_label:'Em avaliação',high_label:'Adesão',low_threshold:40,high_threshold:65,variables:{},events:[],metrics:[],enable_agent_actions:false,allowed_agent_effects:{}};}
  private blankSociety():SocietyDraft{return {name:'',description:'Grupo de perfis sintéticos',agent_ids:[]};}

  refresh():void {
    this.loading=true;
    this.subscriptions.add(forkJoin({configuration:this.api.configuration(),agents:this.api.agents(),environments:this.api.environments(),societies:this.api.societies(),runs:this.api.runs(),experiments:this.api.experiments()})
      .subscribe({next:data=>{
        this.configuration=data.configuration;this.agents=data.agents;this.environments=data.environments;this.societies=data.societies;this.runs=data.runs;this.experiments=data.experiments;
        if (!this.sim.environment_id&&data.environments.length)this.sim.environment_id=data.environments[0].id;
        if (!this.sim.society_id&&data.societies.length)this.sim.society_id=data.societies[0].id;
        if(!data.configuration.demo_available)this.sim.mode='bridge';
        this.loading=false;this.error='';this.cdr.markForCheck();
        if(!this.selectedRun&&data.runs.length)this.openRun(data.runs[0].id);
      },error:err=>{this.loading=false;this.showError(err);}}));
  }
  private showError(err:unknown):void {
    const payload=err as {error?:{message?:string;detail?:string};message?:string};
    this.error=payload?.error?.message||payload?.error?.detail||payload?.message||'Não foi possível concluir a operação.';
    this.busy=false;this.cdr.markForCheck();
  }
  private saved(message:string):void {this.notice=message;this.error='';this.busy=false;this.refresh();this.cdr.markForCheck();}
  private poll():void {
    if(!this.selectedRun||!['QUEUED','RUNNING'].includes(this.selectedRun.status)||this.pollBusy)return;
    this.pollBusy=true;
    this.subscriptions.add(this.api.run(this.selectedRun.id).subscribe({next:run=>{
      const last=this.selectedRun?.status;
      this.selectedRun=run;
      if(this.followLive){this.selectedRepetition=this.maxAvailableRepetition();this.selectedRound=this.maxAvailableRound();}
      else if(this.selectedRound>this.maxAvailableRound())this.selectedRound=this.maxAvailableRound();
      this.pollBusy=false;this.cdr.markForCheck();
      if(last!==run.status&&!['QUEUED','RUNNING'].includes(run.status))this.api.runs().subscribe(rows=>{this.runs=rows;this.cdr.markForCheck();});
    },error:err=>{this.pollBusy=false;this.showError(err);}}));
  }
  setTab(tab:Tab):void{this.tab=tab;this.error='';}
  agentLabel(id:string):string{return this.agents.find(agent=>agent.id===id)?.name||'Agente excluído';}
  extraColumns():string[]{return Array.from(new Set(this.agents.flatMap(a=>Object.keys(a.characteristics)))).sort();}
  characteristicKeys():string[]{return Object.keys(this.agentDraft.characteristics);}
  variableKeys():string[]{return Object.keys(this.environmentDraft.variables);}
  addCharacteristic():void{
    const key=this.characteristicKey.trim();if(!key||key.length>60||this.characteristicValue.length>500)return;
    this.agentDraft.characteristics={...this.agentDraft.characteristics,[key]:this.characteristicValue};
    this.characteristicKey='';this.characteristicValue='';
  }
  removeCharacteristic(key:string):void{const next={...this.agentDraft.characteristics};delete next[key];this.agentDraft.characteristics=next;}
  addVariable():void{
    const key=this.variableKey.trim();if(!key||key.length>60||this.variableValue.length>300)return;
    this.environmentDraft.variables={...this.environmentDraft.variables,[key]:this.variableValue};this.variableKey='';this.variableValue='';
  }
  removeVariable(key:string):void{const next={...this.environmentDraft.variables};delete next[key];this.environmentDraft.variables=next;}

  editAgent(agent:SyntheticAgent):void{const {id,created_at,updated_at,...body}=agent;this.agentDraft={...body,characteristics:{...body.characteristics}};this.editAgentId=id;}
  clearAgent():void{this.agentDraft=this.blankAgent();this.editAgentId='';}
  saveAgent():void{
    this.busy=true;this.subscriptions.add(this.api.saveAgent(this.agentDraft,this.editAgentId||undefined).subscribe({
      next:()=>{this.clearAgent();this.saved('Perfil sintético salvo.');},error:err=>this.showError(err)}));
  }
  removeAgent(agent:SyntheticAgent):void{
    if(!confirm(`Excluir o perfil sintético "${agent.name}"? Sociedades existentes podem precisar de atualização.`))return;
    this.busy=true;this.subscriptions.add(this.api.deleteAgent(agent.id).subscribe({next:()=>this.saved('Perfil removido.'),error:err=>this.showError(err)}));
  }
  importAgents(event:Event):void{
    const target=event.target as HTMLInputElement;const file=target.files?.[0];if(!file)return;
    this.busy=true;this.subscriptions.add(this.api.importCsv(file).subscribe({next:r=>this.saved(`${r.imported} agentes importados do CSV.`),error:err=>this.showError(err)}));target.value='';
  }
  downloadAgents():void{this.api.exportAgents().subscribe({next:blob=>this.download(blob,'agentes_sinteticos.csv'),error:err=>this.showError(err)});}

  editEnvironment(env:Environment):void{this.editEnvironmentId=env.id;this.environmentDraft={
    name:env.name,context:env.context,decision:env.decision,success_criterion:env.success_criterion,
    target_behavior:env.target_behavior||'Apoiar a decisão apresentada',low_label:env.low_label||'Resistência',
    middle_label:env.middle_label||'Em avaliação',high_label:env.high_label||'Adesão',
    low_threshold:env.low_threshold??40,high_threshold:env.high_threshold??65,
    variables:{...env.variables},events:(env.events||[]).map(event=>({...event,variable_updates:{...event.variable_updates}})),
    metrics:(env.metrics||[]).map(metric=>({...metric,categories:[...metric.categories]})),
    enable_agent_actions:env.enable_agent_actions||false,allowed_agent_effects:{...(env.allowed_agent_effects||{})}};}
  clearEnvironment():void{this.editEnvironmentId='';this.environmentDraft=this.blankEnvironment();}
  addEventVariable():void{
    if(!this.eventKey.trim()||this.eventKey.length>60||this.eventValue.length>300)return;
    this.eventDraft.variable_updates={...this.eventDraft.variable_updates,[this.eventKey.trim()]:this.eventValue};this.eventKey='';this.eventValue='';
  }
  addEnvironmentEvent():void{
    if(!this.eventDraft.name.trim()||this.eventDraft.name.trim().length<3||this.eventDraft.description.trim().length<5||this.environmentDraft.events.length>=12)return;
    this.environmentDraft.events=[...this.environmentDraft.events,{...this.eventDraft,variable_updates:{...this.eventDraft.variable_updates}}];
    this.eventDraft={round:2,name:'',description:'',impact:0,variable_updates:{}};
  }
  removeEnvironmentEvent(index:number):void{this.environmentDraft.events=this.environmentDraft.events.filter((_,i)=>i!==index);}
  addAllowedEffect():void {
    const key=this.actionKey.trim();const options=this.actionOptions.split(',').map(value=>value.trim()).filter(Boolean);
    if(!key||!(key in this.environmentDraft.variables)||!options.length||options.length>8||new Set(options).size!==options.length){
      this.error='A variável da ação deve existir no ambiente e ter até 8 valores distintos separados por vírgula.';return;
    }
    this.environmentDraft.allowed_agent_effects={...this.environmentDraft.allowed_agent_effects,[key]:options};
    this.actionKey='';this.actionOptions='';this.error='';
  }
  removeAllowedEffect(key:string):void{const next={...this.environmentDraft.allowed_agent_effects};delete next[key];this.environmentDraft.allowed_agent_effects=next;}
  addMetric():void {
    const key=this.metricDraft.key.trim().toLowerCase();
    const categories=this.metricCategories.split(',').map(value=>value.trim()).filter(Boolean);
    if(!/^[a-z][a-z0-9_]{1,44}$/.test(key)||!this.metricDraft.label.trim()||
       this.environmentDraft.metrics.some(metric=>metric.key===key)||this.environmentDraft.metrics.length>=12){
      this.error='Informe identificador único (letras minúsculas, números e _) e nome da métrica.';return;
    }
    if(this.metricDraft.kind==='number'&&!(this.metricDraft.minimum<this.metricDraft.maximum)){
      this.error='O valor máximo da métrica deve ser maior que o mínimo.';return;
    }
    if(this.metricDraft.kind==='category'&&(categories.length<2||new Set(categories).size!==categories.length)){
      this.error='Informe pelo menos duas categorias distintas separadas por vírgula.';return;
    }
    this.environmentDraft.metrics=[...this.environmentDraft.metrics,{...this.metricDraft,key,categories:this.metricDraft.kind==='category'?categories:[]}];
    this.metricDraft={key:'',label:'',kind:'number',description:'Indicador sintético do cenário',minimum:0,maximum:100,categories:[]};
    this.metricCategories='';this.error='';
  }
  removeMetric(key:string):void{this.environmentDraft.metrics=this.environmentDraft.metrics.filter(item=>item.key!==key);}
  viewVersions(kind:'agents'|'environments'|'societies',id:string,name:string):void{
    this.api.revisions(kind,id).subscribe({next:versions=>{this.itemRevisions=versions;this.versionedName=name;this.cdr.markForCheck();},error:err=>this.showError(err)});
  }
  inspectDrift():void{
    if(!this.selectedRun)return;
    this.api.drift(this.selectedRun.id,this.driftThreshold).subscribe({next:result=>{this.driftResult=result;this.cdr.markForCheck();},error:err=>this.showError(err)});
  }
  duplicateEnvironment(env:Environment):void{
    this.editEnvironment(env);this.editEnvironmentId='';this.environmentDraft.name=`${env.name} · Cópia`;
    this.notice='Cenário duplicado no editor. Revise e salve como novo ambiente.';this.tab='ambientes';
  }
  duplicateAgent(agent:SyntheticAgent):void{
    this.editAgent(agent);this.editAgentId='';this.agentDraft.name=`${agent.name} · Cópia`;
    this.notice='Perfil duplicado no editor. Revise e salve.';this.tab='agentes';
  }
  loadAgentTemplate(type:'pessoa'|'empresa'|'instituicao'|'digital'):void{
    const presets:{[key:string]:AgentDraft}={
      pessoa:{name:'Pessoa simulada',entity_type:'PESSOA',group:'Público',goal:'Conseguir um resultado com segurança e clareza',communication_style:'questionador',initial_stance:50,influence:.4,susceptibility:.6,characteristics:{prioridade:'custo-benefício',experiencia:'intermediária'}},
      empresa:{name:'Empresa simulada',entity_type:'EMPRESA',group:'Mercado',goal:'Equilibrar custo, qualidade e continuidade',communication_style:'analítico',initial_stance:58,influence:.7,susceptibility:.3,characteristics:{segmento:'fictício',porte:'pequeno'}},
      instituicao:{name:'Entidade fictícia',entity_type:'ORGANIZACAO',group:'Instituições',goal:'Representar interesses coletivos e reduzir impactos negativos',communication_style:'formal',initial_stance:45,influence:.8,susceptibility:.3,characteristics:{papel:'observação',restrição:'sem autoridade real'}},
      digital:{name:'Agente virtual fictício',entity_type:'AGENTE_IA',group:'Tecnologia',goal:'Explicar o cenário e colaborar com respostas consistentes',communication_style:'objetivo',initial_stance:60,influence:.5,susceptibility:.4,characteristics:{canal:'chat',limitação:'simulado'}}
    };this.clearAgent();this.agentDraft={...presets[type],characteristics:{...presets[type].characteristics}};
  }
  saveEnvironment():void{this.busy=true;this.subscriptions.add(this.api.saveEnvironment(this.environmentDraft,this.editEnvironmentId||undefined).subscribe({next:()=>{this.clearEnvironment();this.saved('Ambiente salvo.');},error:err=>this.showError(err)}));}
  removeEnvironment(env:Environment):void{if(!confirm(`Excluir ambiente "${env.name}"?`))return;this.api.deleteEnvironment(env.id).subscribe({next:()=>this.saved('Ambiente excluído.'),error:err=>this.showError(err)});}
  editSociety(society:Society):void{this.editSocietyId=society.id;this.societyDraft={name:society.name,description:society.description,agent_ids:[...society.agent_ids]};}
  clearSociety():void{this.editSocietyId='';this.societyDraft=this.blankSociety();}
  societyHas(id:string):boolean{return this.societyDraft.agent_ids.includes(id);}
  toggleSocietyAgent(id:string,checked:boolean):void{
    this.societyDraft.agent_ids=checked?[...this.societyDraft.agent_ids.filter(x=>x!==id),id]:this.societyDraft.agent_ids.filter(x=>x!==id);
  }
  selectAllAgents():void{this.societyDraft.agent_ids=this.agents.slice(0,30).map(a=>a.id);}
  saveSociety():void{this.busy=true;this.subscriptions.add(this.api.saveSociety(this.societyDraft,this.editSocietyId||undefined).subscribe({next:()=>{this.clearSociety();this.saved('Sociedade salva.');},error:err=>this.showError(err)}));}
  removeSociety(society:Society):void{if(!confirm(`Excluir sociedade "${society.name}"?`))return;this.api.deleteSociety(society.id).subscribe({next:()=>this.saved('Sociedade excluída.'),error:err=>this.showError(err)});}
  createExample():void{this.busy=true;this.subscriptions.add(this.api.createExample(this.sampleType).subscribe({next:r=>{
    this.sim.environment_id=r.environment.id;this.sim.society_id=r.society.id;this.clearActiveRun();this.saved('Cenário fictício de exemplo criado.');this.tab='simulacoes';
  },error:err=>this.showError(err)}));}

  generateScenario():void {
    // Evita chamada remota quando o usuário ainda não explicou sua hipótese.
    const description=this.generatorDescription.trim();
    if(description.length<30||description.length>1600){this.error='Descreva o experimento com 30 a 1.600 caracteres.';return;}
    if(!Number.isInteger(this.generatorCount)||this.generatorCount<2||this.generatorCount>10){
      this.error='Escolha de 2 a 10 agentes fictícios para geração assistida.';return;
    }
    if(!this.configuration?.bridge_available){this.error='A criação com IA exige a Bridge configurada; use os modelos manuais ou CSV.';return;}
    if(this.busy)return;
    this.busy=true;this.error='';
    this.subscriptions.add(this.api.generateScenario(description,this.generatorCount).subscribe({next:result=>{
      this.sim.environment_id=result.environment.id;this.sim.society_id=result.society.id;
      this.clearActiveRun();this.tab='agentes';
      this.saved(`Cenário e ${result.agents.length} agentes fictícios criados. Revise os perfis e o ambiente antes de simular.`);
    },error:err=>this.showError(err)}));
  }

  clearActiveRun():void{this.selectedRun=null;this.selectedRepetition=1;this.selectedRound=1;this.selectedAgentId='';this.playing=false;this.followLive=false;}
  viewRepetition(index:number):void{this.tab='simulacoes';this.setRepetition(index);}
  start():void{
    this.error='';this.notice='';
    if(!this.sim.environment_id||!this.sim.society_id){this.error='Crie ou selecione um ambiente e uma sociedade com ao menos um agente.';return;}
    if(!Number.isInteger(this.sim.rounds)||this.sim.rounds<1||this.sim.rounds>6||
       !Number.isInteger(this.sim.repetitions)||this.sim.repetitions<1||this.sim.repetitions>10||
       !Number.isInteger(this.sim.seed)||this.sim.seed<0||this.sim.seed>2147483647){
      this.error='Confira rodadas (1–6), simulações (1–10) e semente inteira não negativa.';return;
    }
    const planned=this.selectedSocietyAgents().length*this.sim.rounds*this.sim.repetitions;
    if(!planned||planned>(this.configuration?.max_model_calls||120)){
      this.error='A quantidade de reações supera o limite configurado. Reduza agentes, rodadas ou simulações.';return;
    }
    const environment=this.environments.find(item=>item.id===this.sim.environment_id);
    if(environment?.events?.some(event=>event.round>this.sim.rounds)){
      this.error='O cenário tem eventos fora das rodadas escolhidas. Aumente o número de rodadas ou edite o cenário.';return;
    }
    if(this.sim.mode==='bridge'&&!this.configuration?.bridge_available){this.error='A IA corporativa não está configurada.';return;}
    if(this.sim.mode==='demo'&&!this.configuration?.demo_available){this.error='O modo demonstrativo só está disponível no ambiente local.';return;}
    if(this.busy)return;
    this.busy=true;this.subscriptions.add(this.api.start({...this.sim}).subscribe({next:run=>{
      this.busy=false;this.selectedRun=run;this.selectedRound=1;this.selectedRepetition=1;this.followLive=true;this.playing=false;this.selectedAgentId='';this.notice='Simulação iniciada. Acompanhe as reações em tempo real.';this.cdr.markForCheck();
      this.api.runs().subscribe(rows=>{this.runs=rows;this.cdr.markForCheck();});this.poll();
    },error:err=>this.showError(err)}));
  }
  cancel():void{if(!this.selectedRun)return;this.api.cancel(this.selectedRun.id).subscribe({next:()=>{this.notice='Cancelamento solicitado.';this.cdr.markForCheck();},error:err=>this.showError(err)});}
  openRun(id:string):void{this.api.run(id).subscribe({next:run=>{this.selectedRun=run;this.driftResult=null;this.api.calibrations(id).subscribe({next:rows=>{this.calibrations=rows;this.cdr.markForCheck();},error:()=>{this.calibrations=[];}});this.selectedRepetition=this.maxAvailableRepetition();this.selectedRound=this.maxAvailableRound();this.followLive=['QUEUED','RUNNING'].includes(run.status);this.playing=false;this.selectedAgentId='';this.error='';this.cdr.markForCheck();},error:err=>this.showError(err)});}
  openResult(id:string):void{this.openRun(id);this.tab='resultados';}
  showRunStatus(status:string):string{return ({QUEUED:'Na fila',RUNNING:'Executando',COMPLETED:'Concluída',FAILED:'Falhou',CANCELLED:'Cancelada',INTERRUPTED:'Interrompida'} as Record<string,string>)[status]||status;}
  progress():number{return this.selectedRun&&this.selectedRun.total?Math.round(100*this.selectedRun.completed/this.selectedRun.total):0;}
  maxAvailableRepetition():number{
    return Math.max(1,...(this.selectedRun?.events||[]).filter(e=>e.event_type==='NETWORK').map(e=>Number(e.payload['repetition']||1)));
  }
  availableRepetitions():number[]{return Array.from({length:this.maxAvailableRepetition()},(_,i)=>i+1);}
  maxAvailableRound():number{
    return Math.max(1,...(this.selectedRun?.events||[]).filter(e=>e.event_type==='REACTION'&&Number(e.payload['repetition']||1)===this.selectedRepetition).map(e=>e.round));
  }
  setRepetition(value:number):void{this.selectedRepetition=Number(value);this.selectedRound=1;this.followLive=false;this.playing=false;}
  setRound(value:number):void{this.selectedRound=Number(value);this.followLive=false;this.playing=false;}
  nextReplay():void{
    if(this.selectedRound<this.maxAvailableRound()){this.selectedRound++;this.followLive=false;return;}
    if(this.selectedRepetition<this.maxAvailableRepetition()){this.selectedRepetition++;this.selectedRound=1;this.followLive=false;return;}
    this.playing=false;
  }
  previousReplay():void{
    this.followLive=false;this.playing=false;
    if(this.selectedRound>1)this.selectedRound--;
    else if(this.selectedRepetition>1){this.selectedRepetition--;this.selectedRound=this.maxAvailableRound();}
  }
  togglePlayback():void{if(!this.selectedRun)return;this.followLive=false;
    if(this.selectedRepetition===this.maxAvailableRepetition()&&this.selectedRound===this.maxAvailableRound()){
      this.selectedRepetition=1;this.selectedRound=1;
    }this.playing=!this.playing;
  }
  followExecution():void{this.playing=false;this.followLive=true;this.selectedRepetition=this.maxAvailableRepetition();this.selectedRound=this.maxAvailableRound();}
  currentEnvironment():Environment|null{return this.selectedRun?.snapshot.environment||this.environments.find(e=>e.id===this.sim.environment_id)||null;}
  activeEnvironmentEvents():LabEvent[]{return (this.selectedRun?.events||[]).filter(e=>
    Number(e.payload['repetition']||1)===this.selectedRepetition&&e.round<=this.selectedRound&&
    ['SHOCK','ENVIRONMENT_CHANGE','AGENT_ACTION'].includes(e.event_type)).sort((a,b)=>b.sequence-a.sequence);}
  environmentVariables():{key:string;value:string}[]{
    const environment=this.currentEnvironment();if(!environment)return [];
    const variables={...(environment.variables||{})};
    for(const event of [...this.activeEnvironmentEvents()].reverse()){
      if(event.event_type==='ENVIRONMENT_CHANGE')Object.assign(variables,event.payload['variable_updates']||{});
      if(event.event_type==='AGENT_ACTION')variables[String(event.payload['key'])]=String(event.payload['new_value']);
    }
    return Object.entries(variables).map(([key,value])=>({key,value}));
  }
  feedEvents():LabEvent[]{
    return (this.selectedRun?.events||[]).filter(event=>{
      if(Number(event.payload['repetition']||1)!==this.selectedRepetition||event.round>this.selectedRound)return false;
      if(!['REACTION','INTERACTION','CONVERSATION','SHOCK','ENVIRONMENT_CHANGE','AGENT_ACTION'].includes(event.event_type))return false;
      if(this.feedFilter==='conversations'&&!['REACTION','INTERACTION','CONVERSATION'].includes(event.event_type))return false;
      if(this.feedFilter==='environment'&&!['SHOCK','ENVIRONMENT_CHANGE','AGENT_ACTION'].includes(event.event_type))return false;
      if(this.filterSelectedAgent&&this.selectedAgentId&&['REACTION','INTERACTION','CONVERSATION'].includes(event.event_type)
         &&event.agent_id!==this.selectedAgentId&&event.peer_id!==this.selectedAgentId)return false;
      return true;
    }).sort((a,b)=>b.sequence-a.sequence).slice(0,120);
  }
  messageTo(id:string|null):string{return (this.selectedRun?.snapshot.agents||[]).find(agent=>agent.id===id)?.name||'Agente';}
  reactions():LabEvent[]{return (this.selectedRun?.events||[]).filter(e=>e.event_type==='REACTION'&&e.round===this.selectedRound&&Number(e.payload['repetition']||1)===this.selectedRepetition).sort((a,b)=>b.sequence-a.sequence);}
  selectedAgent():SyntheticAgent|null{return this.selectedRun?.snapshot.agents.find(a=>a.id===this.selectedAgentId)||null;}
  agentReaction():LabEvent|null{return this.reactions().find(e=>e.agent_id===this.selectedAgentId)||null;}
  graphNodes():GraphNode[]{
    const agents=this.selectedRun?.snapshot.agents||this.selectedSocietyAgents();
    const events=this.selectedRun?.events||[];
    const key=[this.selectedRun?.id||'preview',this.selectedRun?.events?.length||0,
      this.selectedRepetition,this.selectedRound,agents.map(agent=>agent.id).join(',')].join(':');
    if(key===this.graphCacheKey)return this.graphCacheNodes;
    const reactions=events.filter(e=>e.event_type==='REACTION'&&e.round<=this.selectedRound&&Number(e.payload['repetition']||1)===this.selectedRepetition);
    const byId=new Map<string,LabEvent>();for(const event of reactions)byId.set(event.agent_id||'',event);
    const groups=Array.from(new Set(agents.map(agent=>agent.group)));
    const members=new Map<string,SyntheticAgent[]>();
    for(const group of groups)members.set(group,agents.filter(agent=>agent.group===group));
    const nodes=agents.map((agent,index)=>{
      const groupIndex=groups.indexOf(agent.group),groupMembers=members.get(agent.group)||[];
      const withinGroup=groupMembers.findIndex(item=>item.id===agent.id);
      const count=groupMembers.length;
      // Em redes maiores, distribuir em anéis evita sobrepor agentes e rótulos.
      // As posições permanecem estáveis durante a passagem das rodadas.
      let groupX=450,groupY=216,radius=155,angle=0;
      if(groups.length===1){
        const split=count>16?12:count;
        const outer=withinGroup>=split;
        const localIndex=outer?withinGroup-split:withinGroup;
        const localCount=outer?count-split:split;
        radius=outer?197:(count>16?108:Math.min(170,Math.max(90,count*12)));
        angle=2*Math.PI*localIndex/Math.max(localCount,1)-Math.PI/2;
      }else{
        if(groups.length===2){groupX=groupIndex===0?250:650;groupY=216;}
        else{const clusterAngle=2*Math.PI*groupIndex/groups.length-Math.PI/2;
          groupX=450+245*Math.cos(clusterAngle);groupY=216+132*Math.sin(clusterAngle);}
        radius=Math.min(groups.length===2?115:92,Math.max(50,count*10));
        angle=2*Math.PI*withinGroup/Math.max(count,1)-Math.PI/2;
      }
      const event=byId.get(agent.id);
      return {id:agent.id,name:agent.name,group:agent.group,type:agent.entity_type,
        x:Math.round(groupX+radius*Math.cos(angle)),y:Math.round(groupY+radius*.77*Math.sin(angle)),
        stance:event?Number(event.payload['stance']):agent.initial_stance,hasReaction:!!event};
    });
    this.graphCacheKey=key;this.graphCacheNodes=nodes;this.graphCacheIndex=new Map(nodes.map(node=>[node.id,node]));
    return nodes;
  }
  selectedSocietyAgents():SyntheticAgent[]{const society=this.societies.find(s=>s.id===this.sim.society_id);return society? society.agent_ids.map(id=>this.agents.find(a=>a.id===id)).filter((a):a is SyntheticAgent=>!!a):[];}
  graphEdges():GraphEdge[]{
    const events=this.selectedRun?.events||[];
    const key=[this.selectedRun?.id||'empty',events.length,this.selectedRepetition,this.selectedRound].join(':');
    if(key===this.edgeCacheKey)return this.edgeCache;
    const event=events.find(e=>e.event_type==='NETWORK'&&Number(e.payload['repetition']||1)===this.selectedRepetition);
    const network=(event?.payload['edges']||[]) as {source:string;target:string;weight:number}[];
    const recent=events.filter(e=>['INTERACTION','CONVERSATION'].includes(e.event_type)&&e.round===this.selectedRound&&Number(e.payload['repetition']||1)===this.selectedRepetition);
    const connected=new Set(recent.map(inter=>[inter.agent_id,inter.peer_id].sort().join('|')));
    this.edgeCache=network.map(edge=>({...edge,active:connected.has([edge.source,edge.target].sort().join('|'))}));
    this.edgeCacheKey=key;return this.edgeCache;
  }
  node(id:string):GraphNode|undefined{this.graphNodes();return this.graphCacheIndex.get(id);}
  selectNode(id:string):void{this.selectedAgentId=id;}
  stanceLabel(value:number):string{const env=this.currentEnvironment();return value>=(env?.high_threshold??65)?(env?.high_label||'Alta'):value>=(env?.low_threshold??40)?(env?.middle_label||'Intermediária'):(env?.low_label||'Baixa');}
  stanceClass(value:number):string{const env=this.currentEnvironment();return value>=(env?.high_threshold??65)?'support':value>=(env?.low_threshold??40)?'undecided':'resistance';}
  latestMessages():LabEvent[]{return this.reactions().slice(0,12);}
  eventsCount(type:string):number{return (this.selectedRun?.events||[]).filter(e=>e.event_type===type).length;}
  selectedEvent():LabEvent|null{return (this.selectedRun?.events||[]).find(e=>e.sequence===this.selectedConversationSequence)||null;}
  inspectEvent(event:LabEvent):void{
    this.selectedConversationSequence=event.sequence;this.selectedAgentId=event.agent_id||'';
    this.selectedRound=event.round;this.selectedRepetition=Number(event.payload['repetition']||1);this.followLive=false;this.playing=false;
  }
  agentTimeline():LabEvent[]{return (this.selectedRun?.events||[]).filter(event=>event.agent_id===this.selectedAgentId&&
    Number(event.payload['repetition']||1)===this.selectedRepetition&&event.round<=this.selectedRound&&
    ['REACTION','CONVERSATION'].includes(event.event_type)).slice(-10);}
  addVariant():void{if(this.variantDrafts.length>=6)return;this.variantDrafts.push({name:`Alternativa ${this.variantDrafts.length+1}`,parameter:'uncertainty',value:.5,variable:'',variableValue:'',impact:0});}
  removeVariant(index:number):void{this.variantDrafts.splice(index,1);}
  buildVariants():ExperimentVariant[]{return this.variantDrafts.map(item=>({name:item.name.trim(),
    parameter_updates:item.variable.trim()?{}:{[item.parameter]:Number(item.value)},
    variable_updates:item.variable.trim()?{[item.variable.trim()]:item.variableValue}: {},impact:item.variable.trim()?Number(item.impact):0}));}
  experimentCost():number{return this.selectedSocietyAgents().length*this.sim.rounds*this.sim.repetitions*(this.variantDrafts.length+1);}
  startExperiment():void{
    if(this.busy)return;
    if(this.experimentName.trim().length<3||this.experimentHypothesis.trim().length<10||!this.sim.environment_id||!this.sim.society_id){
      this.error='Preencha o nome, a hipótese, o cenário e a sociedade.';return;
    }
    if(this.experimentCost()>(this.configuration?.max_model_calls||120)*3 ||
      this.selectedSocietyAgents().length*this.sim.rounds*this.sim.repetitions>(this.configuration?.max_model_calls||120)){
      this.error='Custo previsto ultrapassa o orçamento de reações. Diminua repetições, agentes ou variantes.';return;
    }
    if(this.variantDrafts.some(item=>!item.name.trim())){this.error='Todas as alternativas precisam de nome.';return;}
    this.busy=true;this.error='';
    this.api.startExperiment(this.experimentName.trim(),this.experimentHypothesis.trim(),{...this.sim},this.buildVariants()).subscribe({
      next:experiment=>{this.busy=false;this.selectedExperiment=experiment;this.notice='Experimento comparativo enviado para a fila.';this.loadExperiments();this.cdr.markForCheck();},
      error:err=>this.showError(err)});
  }
  startSensitivity():void{
    if(this.sensitivitySteps<2||this.sensitivitySteps>6||this.sensitivityMinimum<0||this.sensitivityMaximum>1||this.sensitivityMinimum>=this.sensitivityMaximum){
      this.error='Use de 2 a 6 pontos, valores entre 0 e 1 e mínimo inferior ao máximo.';return;
    }
    // O cenário-base é executado uma vez; cada ponto é outra variante auditável.
    this.variantDrafts=Array.from({length:this.sensitivitySteps},(_,index)=>{
      const value=Number((this.sensitivityMinimum+(this.sensitivityMaximum-this.sensitivityMinimum)*index/(this.sensitivitySteps-1)).toFixed(3));
      return {name:`${this.sensitivityParameter} = ${value}`,parameter:this.sensitivityParameter,value,variable:'',variableValue:'',impact:0};
    });
    this.experimentName=`Sensibilidade · ${this.sensitivityParameter}`;
    this.experimentHypothesis=`Avaliar a variação das saídas sintéticas ao alterar ${this.sensitivityParameter}, com agentes e semente comuns.`;
    this.startExperiment();
  }
  loadExperiments():void{
    this.api.experiments().subscribe({next:rows=>{this.experiments=rows;
      if(this.selectedExperiment){this.selectedExperiment=rows.find(row=>row.id===this.selectedExperiment?.id)||this.selectedExperiment;}
      this.cdr.markForCheck();},error:err=>this.showError(err)});
  }
  inspectExperiment(id:string):void{this.api.experiment(id).subscribe({next:item=>{this.selectedExperiment=item;this.cdr.markForCheck();},error:err=>this.showError(err)});}
  cloneRun():void{if(!this.selectedRun)return;this.sim={...this.selectedRun.configuration};this.tab='simulacoes';this.notice='Configuração carregada. Revise o cenário antes de executar novamente.';}
  submitCalibration():void{
    if(!this.selectedRun||!this.calibrationSource.trim()||!this.calibrationReviewer.trim()){
      this.error='Informe a fonte agregada e o responsável pela revisão.';return;
    }
    this.busy=true;this.api.calibrate(this.selectedRun.id,this.calibrationMean,this.calibrationSource,
      this.calibrationSampleSize,this.calibrationReviewer).subscribe({next:()=>{
      this.busy=false;this.notice='Referência agregada registrada. A diferença não valida o modelo.';
      this.api.calibrations(this.selectedRun!.id).subscribe(rows=>{this.calibrations=rows;this.cdr.markForCheck();});
    },error:err=>this.showError(err)});
  }
  downloadReport():void{if(!this.selectedRun)return;
    this.api.report(this.selectedRun.id).subscribe({next:blob=>this.download(blob,`behavior_${this.selectedRun!.id}.md`),error:err=>this.showError(err)});
  }
  downloadRun(format:'json'|'csv'):void{
    if(!this.selectedRun)return;
    this.api.exportRun(this.selectedRun.id,format).subscribe({next:blob=>this.download(blob,`simulacao_${this.selectedRun?.id}.${format}`),error:err=>this.showError(err)});
  }
  private download(blob:Blob,filename:string):void{
    const url=URL.createObjectURL(blob),anchor=document.createElement('a');anchor.href=url;anchor.download=filename;anchor.click();URL.revokeObjectURL(url);
  }
}
