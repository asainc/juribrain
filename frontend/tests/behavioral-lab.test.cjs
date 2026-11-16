'use strict';
// Regressão estática do módulo novo enquanto dependências Angular não estiverem instaladas.
const test=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const ts=require('typescript');
const postcss=require('postcss');
const root=path.resolve(__dirname,'..');
const read=path=>fs.readFileSync(require('node:path').join(root,path),'utf8');

test('Behavior mantém rota, navegação, API e painel de interações reais da simulação',()=>{
  const routes=read('src/app/app.routes.ts');
  const shell=read('src/app/app.component.ts');
  const home=read('src/app/home/ecosystem-home.component.ts');
  const template=read('src/app/behavioral-lab/behavioral-lab-page.component.html');
  const service=read('src/app/behavioral-lab/behavioral-lab-api.service.ts');
  assert.ok(routes.includes("path: 'behavior'"));
  assert.ok(routes.includes("redirectTo: 'behavior'"));
  const registry=read('src/app/core/application-registry.ts');
  assert.ok(home.includes('APPLICATIONS.filter'));
  assert.ok(home.includes('[routerLink]="application.route"'));
  assert.ok(shell.includes('APPLICATIONS'));
  assert.ok(registry.includes("label:'Behavior'"));
  assert.ok(registry.includes("route:'/behavior'"));
  assert.ok(template.includes('<h1>Behavior</h1>'));
  assert.ok(template.includes('Áreas do Behavior'));
  assert.ok(template.includes('Behavior · Ecossistema jurídico'));
  assert.ok(service.includes('laboratorio-comportamental')); // API mantida por compatibilidade.
  for(const keyword of ['graphNodes()','graphEdges()','Reproduzir evolução','Importar CSV','Pressão social','Probabilidade de choque','Exportar JSON','Exportar CSV','Sociedades']){
    assert.ok(template.includes(keyword),`Elemento interativo ausente: ${keyword}`);
  }
  assert.ok(service.includes('this.http.post<LabRun>'));
  assert.ok(service.includes('this.http.get<LabRun>'));
});

test('TypeScript do laboratório é sintaticamente válido e estilos são globais',()=>{
  const angular=JSON.parse(read('angular.json'));
  const styles=angular.projects['ai-ready-legal'].architect.build.options.styles;
  assert.ok(styles.includes('src/behavioral-lab.scss'));
  assert.doesNotThrow(()=>postcss.parse(read('src/behavioral-lab.scss')));
  for(const file of ['src/app/behavioral-lab/behavioral-lab-page.component.ts','src/app/behavioral-lab/behavioral-lab-api.service.ts']){
    const parsed=ts.createSourceFile(file,read(file),ts.ScriptTarget.Latest,true,ts.ScriptKind.TS);
    assert.deepEqual(parsed.parseDiagnostics.map(e=>ts.flattenDiagnosticMessageText(e.messageText,' ')),[],`${file} contém erros de sintaxe`);
  }
});

test('Estúdio mantém três painéis funcionais, repetições e alterações do mundo',()=>{
  const template=read('src/app/behavioral-lab/behavioral-lab-page.component.html');
  const controller=read('src/app/behavioral-lab/behavioral-lab-page.component.ts');
  const css=read('src/behavioral-lab.scss');
  const api=read('src/app/behavioral-lab/behavioral-lab-api.service.ts');
  for (const name of ['lab-control-panel','lab-stage-column','lab-conversation-panel','lab-chat-feed','lab-world-state']) {
    assert.ok(template.includes(name),`Painel obrigatório ausente: ${name}`);
  }
  for (const name of ['sim.repetitions','eventDraft','environmentDraft.target_behavior','feedEvents()','setRepetition($event)','togglePlayback()','filterSelectedAgent','Criar cenário e agentes']) {
    assert.ok(template.includes(name),`Controle de experimento ausente: ${name}`);
  }
  for (const method of ['availableRepetitions()','maxAvailableRepetition()','activeEnvironmentEvents()','environmentVariables()','viewRepetition(index:number)','loadAgentTemplate(type:']) {
    assert.ok(controller.includes(method),`Método do observatório ausente: ${method}`);
  }
  assert.match(css,/\.lab-sim-layout\{grid-template-columns:minmax\(255px,285px\) minmax\(0,1fr\) minmax\(290px,350px\)/);
  assert.ok(css.includes('.lab-chat-message'));
  assert.ok(css.includes('@media(prefers-reduced-motion:reduce)'));
  assert.ok(api.includes('repetitions:number'));
  assert.ok(api.includes('EnvironmentChange'));
  assert.ok(!template.includes('[innerHTML]'), 'Conteúdo de agentes não deve ser injetado como HTML.');
});


test('Criador assistido mantém Bridge opcional, instruções fictícias e edição antes de simular',()=>{
  const view=read('src/app/behavioral-lab/behavioral-lab-page.component.html');
  const logic=read('src/app/behavioral-lab/behavioral-lab-page.component.ts');
  const api=read('src/app/behavioral-lab/behavioral-lab-api.service.ts');
  for(const token of ['lab-generator','generatorDescription','generatorCount','generateScenario()','não informe'.toLowerCase()]){
    assert.ok([view.toLowerCase(),logic.toLowerCase()].some(source=>source.includes(token.toLowerCase())),`Campo ausente: ${token}`);
  }
  assert.ok(api.includes('/assistente/criar-cenario'));
  assert.ok(logic.includes('Revise os perfis e o ambiente antes de simular'));
  assert.ok(logic.includes('Number.isInteger(this.sim.repetitions)'));
});


test('Limiares obrigatórios do cenário não acionam warning NG8102 no template',()=>{
  // O backend fornece os dois limites e o contrato TypeScript os declara como number.
  // Usar ?? nesses campos gera NG8102 em compilação estrita, sem adicionar proteção real.
  const template=read('src/app/behavioral-lab/behavioral-lab-page.component.html');
  const api=read('src/app/behavioral-lab/behavioral-lab-api.service.ts');
  for (const field of ['low_threshold','high_threshold']) {
    assert.match(api,new RegExp(`\\b${field}:number\\b`),`Contrato obrigatório ausente: ${field}`);
    assert.ok(template.includes(`run.snapshot.environment.${field}`),`Exibição ausente: ${field}`);
    assert.doesNotMatch(template,new RegExp(`run\\.snapshot\\.environment\\.${field}\\s*\\?\\?`),`NG8102 em ${field}`);
  }
});

test('Feed de conversas preserva altura de mensagens longas e permite rolagem independente',()=>{
  // Evita regressão: flex-shrink comprimia centenas de mensagens ao mínimo e sobrepunha falas.
  const css=read('src/behavioral-lab.scss');
  const html=read('src/app/behavioral-lab/behavioral-lab-page.component.html');
  assert.match(css,/\.lab-chat-feed>\.lab-chat-message[^\{]*\{[^}]*flex:0 0 auto/);
  assert.match(css,/\.lab-chat-feed\{[^}]*overflow-y:auto/);
  assert.match(css,/\.lab-chat-bubble\{[^}]*white-space:pre-wrap/);
  assert.match(css,/\.lab-chat-event p\{[^}]*overflow-wrap:anywhere/);
  assert.ok(html.includes('aria-label="Histórico de mensagens e acontecimentos"'));
});

test('Pausa, retomada e reset de parâmetros estão conectados ao backend',()=>{
  // Pausar replay não equivale a suspender geração: exigimos endpoints e estado explícitos.
  const view=read('src/app/behavioral-lab/behavioral-lab-page.component.html');
  const service=read('src/app/behavioral-lab/behavioral-lab-api.service.ts');
  const controller=read('src/app/behavioral-lab/behavioral-lab-page.component.ts');
  for(const token of ['Pausar experimento','Retomar experimento','Resetar configurações de simulação','pauseRun()','resumeRun()','resetSimulationConfiguration()']){
    assert.ok(view.includes(token),`Controle ausente: ${token}`);
  }
  assert.ok(view.includes('Pausar replay'), 'Replay deve ser distinguido da execução real');
  assert.ok(service.includes('/pausar') && service.includes('/retomar'));
  assert.ok(service.includes("'PAUSE_REQUESTED'|'PAUSED'"));
  assert.ok(controller.includes('this.api.pause(') && controller.includes('this.api.resume('));
  assert.ok(controller.includes('defaultSimulationConfiguration()'));
  assert.ok(controller.includes('this.configuration?.demo_available'));
});

test('Mapa reposicionável responde a pointer e teclado, conserva coordenadas e permite restaurar layout',()=>{
  const view=read('src/app/behavioral-lab/behavioral-lab-page.component.html');
  const logic=read('src/app/behavioral-lab/behavioral-lab-page.component.ts');
  const style=read('src/behavioral-lab.scss');
  for(const binding of ['(pointerdown)="onNodePointerDown($event,n.id)"', '(pointermove)="onNodePointerMove($event)"',
    '(pointerup)="onNodePointerEnd($event)"', '(keydown)="onNodeKeyDown($event,n.id)"', 'resetNodePositions()', 'Reorganizar mapa']) {
    assert.ok(view.includes(binding),`Controle ausente: ${binding}`);
  }
  assert.ok(logic.includes('getScreenCTM()'), 'Transformação deve respeitar viewBox e redimensionamento');
  assert.ok(logic.includes('matrixTransform(matrix.inverse())'), 'Não usar coordenadas brutas do mouse');
  assert.ok(logic.includes('behavior:network-layout:v1:'), 'Persistir layout por sociedade no navegador');
  assert.ok(logic.includes('value.x/900') || logic.includes('x:Math.max(46,Math.min(854,x))/900'));
  assert.ok(style.includes('touch-action:none'), 'Arraste em telas touch deve estar disponível');
});

test('Status e duração distinguem falha, conclusão, andamento e pausa',()=>{
  const view=read('src/app/behavioral-lab/behavioral-lab-page.component.html');
  const logic=read('src/app/behavioral-lab/behavioral-lab-page.component.ts');
  const api=read('src/app/behavioral-lab/behavioral-lab-api.service.ts');
  for(const token of ['lab-run-state', 'Tempo de execução:', 'runStateDescription(run)', 'Finalizada:', 'Iniciada:', 'run.failure_stage','run.error_code']){
    assert.ok(view.includes(token),`Diagnóstico ausente: ${token}`);
  }
  for(const status of ['QUEUED', 'RUNNING', 'COMPLETED', 'FAILED', 'PAUSED', 'INTERRUPTED']){
    assert.ok(logic.includes(`case '${status}'`),`Descrição ausente: ${status}`);
  }
  assert.ok(api.includes('elapsed_seconds?:number|null'));
  assert.ok(api.includes('error_reason?:string|null'));
});
