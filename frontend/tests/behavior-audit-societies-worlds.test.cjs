'use strict';
// Regressões estruturais complementares à suíte de API isolada.
// O build Angular continua exigindo dependências do ambiente corporativo.
const test=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const ts=require('typescript');
const postcss=require('postcss');
const root=path.resolve(__dirname,'..');
const read=file=>fs.readFileSync(path.join(root,file),'utf8');

test('A trilha didática mostra antes/depois, fontes, contexto e distinção IA/demonstração',()=>{
  const view=read('src/app/behavioral-lab/behavioral-lab-page.component.html');
  const logic=read('src/app/behavioral-lab/behavioral-lab-page.component.ts');
  const api=read('src/app/behavioral-lab/behavioral-lab-api.service.ts');
  for(const token of ['lab-decision-audit','Por que a posição mudou?','Por que a posição permaneceu?',
    'trace.peer_signals','trace.scheduled_changes','trace.calculation','trace.interpretation',
    'lab-chat-audit-summary','Expandir auditoria']) assert.ok(view.includes(token),`Auditoria ausente: ${token}`);
  assert.ok(logic.includes('inspectedDecisionEvent()'));
  assert.ok(api.includes('export interface DecisionTrace'));
  assert.ok(!view.includes('[innerHTML]'), 'Não injetar conteúdo do modelo como HTML');
});

test('Sociedades permitem inclusão, criação, edição e retirada sem destruir histórico',()=>{
  const view=read('src/app/behavioral-lab/behavioral-lab-page.component.html');
  const logic=read('src/app/behavioral-lab/behavioral-lab-page.component.ts');
  const api=read('src/app/behavioral-lab/behavioral-lab-api.service.ts');
  for(const token of ["tab==='sociedades'",'Novo agente para esta sociedade'.toLowerCase(),
    'Editar perfil','Retirar','Salvar sociedade','societyMemberSearch','availableSocietyMembers()',
    'viewVersions(\'societies\'']) {
    assert.ok(view.toLowerCase().includes(token.toLowerCase()),`Controle ausente: ${token}`);
  }
  assert.ok(logic.includes('creatingSocietyMember'));
  assert.ok(logic.includes('this.toggleSocietyAgent(agent.id,true)'));
  assert.ok(api.includes('/sociedades'));
});

test('Mundos e tipos de entidade personalizados possuem UI, contrato e API persistente',()=>{
  const view=read('src/app/behavioral-lab/behavioral-lab-page.component.html');
  const logic=read('src/app/behavioral-lab/behavioral-lab-page.component.ts');
  const api=read('src/app/behavioral-lab/behavioral-lab-api.service.ts');
  const css=read('src/behavioral-lab.scss');
  for(const token of ['Tipo de mundo (livre)','environmentDraft.world_type','Criar qualquer tipo de mundo',
    'Cadastrar novo tipo de entidade','newEntityLabel','entityTypes'])assert.ok(view.includes(token));
  assert.ok(logic.includes('addCustomEntityType()'));
  assert.ok(api.includes('/tipos-entidade'));
  assert.ok(api.includes('world_type:string'));
  assert.doesNotThrow(()=>postcss.parse(css));
  for(const file of ['src/app/behavioral-lab/behavioral-lab-page.component.ts',
    'src/app/behavioral-lab/behavioral-lab-api.service.ts']){
    const parsed=ts.createSourceFile(file,read(file),ts.ScriptTarget.Latest,true,ts.ScriptKind.TS);
    assert.equal(parsed.parseDiagnostics.length,0,`Sintaxe inválida: ${file}`);
  }
});

test('Checagem externa usa o mesmo padrão visual e valida os campos agregados',()=>{
  const view=read('src/app/behavioral-lab/behavioral-lab-page.component.html');
  const css=read('src/behavioral-lab.scss');
  const logic=read('src/app/behavioral-lab/behavioral-lab-page.component.ts');
  for(const token of ['lab-external-check','lab-external-intro','lab-external-form',
    'lab-external-history','lab-external-result','Registrar comparação'])assert.ok(view.includes(token));
  assert.ok(css.includes('@media(max-width:760px)'));
  assert.ok(logic.includes('this.calibrationMean<0||this.calibrationMean>100'));
});
