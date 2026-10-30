'use strict';
// Regressão do painel BJN e da página inicial AI Ready sem dependência do registry npm.
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const ts = require('typescript');
const postcss = require('postcss');
const root = path.resolve(__dirname, '..');
const read = file => fs.readFileSync(path.join(root, file), 'utf8');

test('painéis visuais têm estilos globais e mantêm o limite por componente', () => {
  const angular = JSON.parse(read('angular.json'));
  const styles = angular.projects['ai-ready-legal'].architect.build.options.styles;
  const budget = angular.projects['ai-ready-legal'].architect.build.configurations.production.budgets;
  for (const file of ['src/demand-dashboard.scss','src/hub-home-dashboard.scss']) {
    assert.equal(styles.filter(item => item === file).length, 1);
    assert.doesNotThrow(() => postcss.parse(read(file)));
  }
  assert.equal(budget.find(item => item.type === 'anyComponentStyle').maximumError, '16kB');
});

test('gestão BJN conserva fluxos autorizados e apresenta informações reais dos resultados', () => {
  const source = read('src/app/bjn/demands/demand-list.component.ts');
  for (const method of ['switchTab','assignSelected','toggleAll','clearFilters','pendingCount','unassignedCount','inAnalysisCount']) {
    assert.ok(source.includes(`${method}(`), `Ação ausente: ${method}`);
  }
  for (const field of ['from_date:this.fromDate','to_date:this.toDate','lawyer:this.lawyer','pending_only:']) {
    assert.ok(source.includes(field),`Filtro ausente: ${field}`);
  }
  assert.ok(source.includes("configuration()?.actor?.role==='admin' && tab()==='all'"));
  assert.ok(source.includes('Resultado dos filtros aplicados'));
  assert.ok(source.includes('readonly maxBulkSelection=50'));
  assert.ok(source.includes('readonly loaded=signal(false)'));
  assert.ok(source.includes('Filtros avançados'));
  assert.ok(source.includes('{{items().length}}'));
});

test('AI Ready tem ferramentas acionáveis de preparação e navegação pós-análise', () => {
  const source = read('src/app/chatbot/chatbot-page.component.ts');
  for (const method of ['preflightTasks','togglePreflight','clearPreflight','selectGoal','focusUpload','exportReviewAgenda','qualityReviewCount']) {
    assert.ok(source.includes(`${method}(`), `Ação ausente: ${method}`);
  }
  for (const tab of ['panorama','cronologia','agenda','provas','documentos','perguntas']) {
    assert.ok(source.includes(`tab:'${tab}'`),`Objetivo ausente: ${tab}`);
  }
  assert.ok(source.includes("this.activeTab.set(this.plannedTab())"));
  assert.ok(source.includes('input type="checkbox" [checked]="preflightChecked().has(task.id)"'));
  assert.ok(source.includes("this.downloadText(lines, 'pauta-revisao-processual')"));
  assert.ok(source.includes('prepareQuestion(question: string)'));
  assert.ok(source.includes('this.questionDraft = this.plannedQuestion()'));
  assert.ok(source.includes('não calcula prazos legais'));
});

test('componentes alterados têm sintaxe TypeScript válida', () => {
  for (const file of ['src/app/chatbot/chatbot-page.component.ts','src/app/bjn/demands/demand-list.component.ts']) {
    const parsed = ts.createSourceFile(file, read(file), ts.ScriptTarget.Latest, true, ts.ScriptKind.TS);
    const problems = parsed.parseDiagnostics.map(item => ts.flattenDiagnosticMessageText(item.messageText,' '));
    assert.deepEqual(problems,[],`${file} contém erros: ${problems.join('; ')}`);
  }
});
