'use strict';
// Regressão do novo fluxo: valida sintaxe/contratos locais sem alegar build Angular.
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const ts = require('typescript');
const root = path.resolve(__dirname, '..');
const read = file => fs.readFileSync(path.join(root, file), 'utf8');

test('Behavior 3.0 apresenta Studio, Observatory e Intelligence com ações reais', () => {
  const view = read('src/app/behavioral-lab/behavioral-lab-page.component.html');
  const component = read('src/app/behavioral-lab/behavioral-lab-page.component.ts');
  const api = read('src/app/behavioral-lab/behavioral-lab-api.service.ts');
  for (const label of ['Studio · Criar','Observatory','Intelligence','Comparar cenários','Ações com efeitos','Experimentos comparativos']) {
    assert.ok(view.toLowerCase().includes(label.toLowerCase()) || component.includes(label), `Rótulo ausente: ${label}`);
  }
  for (const method of ['startExperiment()','startSensitivity()','submitCalibration()','inspectDrift()','downloadReport()','addMetric()','addAllowedEffect()']) {
    assert.ok(view.includes(method), `Controle não conectado: ${method}`);
    assert.ok(component.includes(method), `Função inexistente: ${method}`);
  }
  for (const route of ['/experimentos', '/calibracoes', '/drift', '/relatorio', '/versoes']) {
    assert.ok(api.includes(route), `API ausente: ${route}`);
  }
  assert.ok(view.includes('lab-intelligence-grid'));
  assert.ok(view.includes('lab-chat-dialogue'));
  assert.ok(!view.includes('[innerHTML]'), 'Conteúdo gerado por agentes não deve ser injetado como HTML.');
});

test('Contratos TypeScript, editor de métricas e classes responsivas mantêm sintaxe', () => {
  for (const file of ['src/app/behavioral-lab/behavioral-lab-page.component.ts','src/app/behavioral-lab/behavioral-lab-api.service.ts']) {
    const parsed = ts.createSourceFile(file, read(file), ts.ScriptTarget.Latest, true, ts.ScriptKind.TS);
    assert.deepEqual(parsed.parseDiagnostics.map(d => ts.flattenDiagnosticMessageText(d.messageText, ' ')), []);
  }
  const css = read('src/behavioral-lab.scss');
  assert.ok(css.includes('.lab-intelligence-grid'));
  assert.ok(css.includes('.lab-metric-results'));
  assert.ok(css.includes('@media(max-width:600px)'));
  const template = read('src/app/behavioral-lab/behavioral-lab-page.component.html');
  assert.ok(template.includes('environmentDraft.metrics'));
  assert.ok(template.includes('environmentDraft.allowed_agent_effects'));
  assert.ok(template.includes('selectedConversationSequence'));
});
