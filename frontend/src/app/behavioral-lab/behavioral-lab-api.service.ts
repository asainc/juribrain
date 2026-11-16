/** Cliente HTTP do Behavior, isolado dos demais módulos. */
import {HttpClient} from '@angular/common/http';
import {inject, Injectable} from '@angular/core';
import {ApiConfiguration} from '../core/config';

export type EntityType = string;
export interface EntityTypeOption {value:string;label:string;is_builtin:boolean}
export interface SyntheticAgent {
  id:string;name:string;entity_type:EntityType;group:string;goal:string;
  communication_style:string;initial_stance:number;influence:number;susceptibility:number;
  characteristics:Record<string,string>;created_at?:string;updated_at?:string;
}
export type AgentDraft = Omit<SyntheticAgent,'id'|'created_at'|'updated_at'>;
export interface MetricDefinition {key:string;label:string;kind:'number'|'boolean'|'category';description:string;minimum:number;maximum:number;categories:string[]}
export interface ExperimentVariant {name:string;parameter_updates:Record<string,number>;variable_updates:Record<string,string>;impact:number}
export interface Experiment {id:string;status:string;payload:{name:string;hypothesis:string;baseline:SimulationConfiguration;variants:ExperimentVariant[];budget?:{model_reactions:number;maximum_output_tokens:number}};
  result:{comparison:{name:string;run_id:string|null;status:string;mean_stance:number|null;delta_to_base:number|null;distribution?:Record<string,number|null>;metrics?:MetricSummary[]}[];disclaimer:string}|null;created_at:string;updated_at:string}
export interface MetricSummary {key:string;label:string;kind:string;observations:number;mean?:number|null;minimum?:number|null;maximum?:number|null;true?:number;false?:number;counts?:Record<string,number>}
export interface Revision {version:number;payload:Record<string,unknown>;sha256:string;created_at:string}
export interface DriftCheck {run_id:string;previous_run_id:string|null;current_mean:number;previous_mean:number|null;absolute_difference:number|null;threshold:number;flagged:boolean|null;method_note:string}
export interface Calibration {id:string;run_id:string;observed_mean:number;simulated_mean:number;absolute_deviation:number;source_description:string;sample_size:number|null;validated_by:string;created_at:string;interpretation:string}
export interface EnvironmentChange {round:number;name:string;description:string;impact:number;variable_updates:Record<string,string>}
export interface Environment {id:string;name:string;world_type:string;context:string;decision:string;success_criterion:string;target_behavior:string;
  low_label:string;middle_label:string;high_label:string;low_threshold:number;high_threshold:number;variables:Record<string,string>;events:EnvironmentChange[];metrics:MetricDefinition[];enable_agent_actions:boolean;allowed_agent_effects:Record<string,string[]>}
export type EnvironmentDraft = Omit<Environment,'id'>;
export interface Society {id:string;name:string;description:string;agent_ids:string[]}
export type SocietyDraft = Omit<Society,'id'>;
export interface SimulationConfiguration {
  environment_id:string;society_id:string;mode:'bridge'|'demo';rounds:number;repetitions:number;seed:number;
  temperature:number;uncertainty:number;social_pressure:number;shock_probability:number;
  shock_intensity:number;network_density:number;max_tokens_per_reaction:number;memory_window:number;
}
export interface LabConfiguration {bridge_available:boolean;bridge_status:string;demo_available:boolean;max_agents:number;max_rounds:number;max_repetitions:number;max_model_calls:number;warning:string}
export interface DecisionTrace {previous_stance:number;current_stance:number;delta:number;changed:boolean;first_round:boolean;
  peer_signals:{agent_id:string;name:string;stance:number;weight:number;influence:number}[];
  scheduled_changes:{name:string;impact:number}[];shock:{label:string;direction:number;intensity:number}|null;
  source:'REGRAS_DEMO'|'JUSTIFICATIVA_IA';reason:string;calculation:{components:Record<string,number>;raw_stance:number;rounding_or_clipping:number}|null;interpretation:string}
export interface LabEvent {sequence:number;round:number;event_type:'NETWORK'|'SHOCK'|'INTERACTION'|'REACTION'|'ENVIRONMENT_CHANGE'|'REPETITION_STARTED'|'REPETITION_COMPLETED'|'AGENT_ACTION'|'CONVERSATION'|'ROUND_SUMMARY'|'ENVIRONMENT_SNAPSHOT';agent_id:string|null;peer_id:string|null;payload:Record<string,any>;created_at:string}
export interface RoundSummary {round:number;mean_stance:number;support:number;undecided:number;resistance:number;agents:number}
export interface RunResult {repetitions_completed?:number;repetitions_planned?:number;repetitions?:{index:number;seed:number;final:RoundSummary|null;rounds:RoundSummary[]}[];final_score_distribution?:{minimum:number;maximum:number;mean:number;standard_deviation:number};interpretation?:string;total_agents:number;total_reactions:number;network_edges:number;rounds:RoundSummary[];final:RoundSummary|null;mean_stance_change?:number;
  groups?:{name:string;mean_stance:number;agents:number}[];metrics?:MetricSummary[];snapshot_sha256?:string;engine_version?:string;configured_model?:string|null;actual_token_usage?:{input_tokens:number|null;cached_input_tokens:number|null;output_tokens:number|null};scenario?:string;method_note?:string;limitations?:string[];prompt_sha256?:string|null}
export interface LabRun {id:string;status:'QUEUED'|'RUNNING'|'PAUSE_REQUESTED'|'PAUSED'|'COMPLETED'|'FAILED'|'CANCELLED'|'INTERRUPTED';mode:'bridge'|'demo';
  configuration:SimulationConfiguration;snapshot:{environment:Environment;society:Society;agents:SyntheticAgent[]};
  completed:number;total:number;cancel_requested:boolean;pause_requested:boolean;created_at:string;updated_at:string;result:RunResult|null;
  error_code:string|null;error_reason?:string|null;failure_stage?:string|null;
  started_at?:string|null;finished_at?:string|null;paused_at?:string|null;elapsed_seconds?:number|null;
  events?:LabEvent[]}

@Injectable({providedIn:'root'})
export class BehavioralLabApiService {
  private readonly http=inject(HttpClient);
  private readonly config=inject(ApiConfiguration);
  private get endpoint():string {return `${this.config.baseUrl}/laboratorio-comportamental`;}

  configuration(){return this.http.get<LabConfiguration>(`${this.endpoint}/configuracao`);}
  entityTypes(){return this.http.get<EntityTypeOption[]>(`${this.endpoint}/tipos-entidade`);}
  addEntityType(value:string,label:string){return this.http.post<EntityTypeOption>(`${this.endpoint}/tipos-entidade`,{value,label});}
  removeEntityType(value:string){return this.http.delete<void>(`${this.endpoint}/tipos-entidade/${encodeURIComponent(value)}`);}
  agents(){return this.http.get<SyntheticAgent[]>(`${this.endpoint}/agentes`);}
  environments(){return this.http.get<Environment[]>(`${this.endpoint}/ambientes`);}
  societies(){return this.http.get<Society[]>(`${this.endpoint}/sociedades`);}
  runs(){return this.http.get<LabRun[]>(`${this.endpoint}/simulacoes`);}
  experiments(){return this.http.get<Experiment[]>(`${this.endpoint}/experimentos`);}
  experiment(id:string){return this.http.get<Experiment>(`${this.endpoint}/experimentos/${encodeURIComponent(id)}`);}
  startExperiment(name:string,hypothesis:string,baseline:SimulationConfiguration,variants:ExperimentVariant[]){
    return this.http.post<Experiment>(`${this.endpoint}/experimentos`,{name,hypothesis,baseline,variants});
  }
  revisions(kind:'agents'|'environments'|'societies',id:string){return this.http.get<Revision[]>(`${this.endpoint}/versoes/${kind}/${encodeURIComponent(id)}`);}
  drift(id:string,threshold:number){return this.http.get<DriftCheck>(`${this.endpoint}/simulacoes/${encodeURIComponent(id)}/drift?threshold=${threshold}`);}
  calibrations(id:string){return this.http.get<Calibration[]>(`${this.endpoint}/simulacoes/${encodeURIComponent(id)}/calibracoes`);}
  calibrate(id:string,observed_mean:number,source_description:string,sample_size:number|null,validated_by:string){
    return this.http.post<Calibration>(`${this.endpoint}/simulacoes/${encodeURIComponent(id)}/calibracoes`,{observed_mean,source_description,sample_size,validated_by});
  }
  report(id:string){return this.http.get(`${this.endpoint}/simulacoes/${encodeURIComponent(id)}/relatorio`,{responseType:'blob'});}
  saveAgent(value:AgentDraft,id?:string){return id?this.http.put<SyntheticAgent>(`${this.endpoint}/agentes/${encodeURIComponent(id)}`,value):this.http.post<SyntheticAgent>(`${this.endpoint}/agentes`,value);}
  deleteAgent(id:string){return this.http.delete<void>(`${this.endpoint}/agentes/${encodeURIComponent(id)}`);}
  importCsv(file:File){const form=new FormData();form.append('file',file,file.name);return this.http.post<{imported:number}>(`${this.endpoint}/agentes/importar-csv`,form);}
  saveEnvironment(value:EnvironmentDraft,id?:string){return id?this.http.put<Environment>(`${this.endpoint}/ambientes/${encodeURIComponent(id)}`,value):this.http.post<Environment>(`${this.endpoint}/ambientes`,value);}
  deleteEnvironment(id:string){return this.http.delete<void>(`${this.endpoint}/ambientes/${encodeURIComponent(id)}`);}
  saveSociety(value:SocietyDraft,id?:string){return id?this.http.put<Society>(`${this.endpoint}/sociedades/${encodeURIComponent(id)}`,value):this.http.post<Society>(`${this.endpoint}/sociedades`,value);}
  deleteSociety(id:string){return this.http.delete<void>(`${this.endpoint}/sociedades/${encodeURIComponent(id)}`);}
  generateScenario(description:string,agent_count:number){return this.http.post<{environment:Environment;society:Society;agents:SyntheticAgent[]}>(`${this.endpoint}/assistente/criar-cenario`,{description,agent_count});}
  createExample(type:'comunidade'|'mercado'|'organizacao'='comunidade'){return this.http.post<{environment:Environment;society:Society;agents:SyntheticAgent[]}>(`${this.endpoint}/exemplos?tipo=${encodeURIComponent(type)}`,{});}
  start(config:SimulationConfiguration){return this.http.post<LabRun>(`${this.endpoint}/simulacoes`,config);}
  run(id:string){return this.http.get<LabRun>(`${this.endpoint}/simulacoes/${encodeURIComponent(id)}`);}
  pause(id:string){return this.http.post<{status:'PAUSE_REQUESTED'}>(`${this.endpoint}/simulacoes/${encodeURIComponent(id)}/pausar`,{});}
  resume(id:string){return this.http.post<{status:'RESUMED'}>(`${this.endpoint}/simulacoes/${encodeURIComponent(id)}/retomar`,{});}
  cancel(id:string){return this.http.post<{status:string}>(`${this.endpoint}/simulacoes/${encodeURIComponent(id)}/cancelar`,{});}
  exportAgents(){return this.http.get(`${this.endpoint}/agentes/exportar-csv`,{responseType:'blob'});}
  exportRun(id:string,format:'json'|'csv') {return this.http.get(`${this.endpoint}/simulacoes/${encodeURIComponent(id)}/exportar?format=${format}`,{responseType:'blob'});}
}
