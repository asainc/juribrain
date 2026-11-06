'use strict';
// Regressão de contratos das três novas funções sem depender do Angular em rede.
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const ts = require('typescript');
const root = path.resolve(__dirname, '..');
const read = file => fs.readFileSync(path.join(root, file), 'utf8');

test('filtro de natureza usa o catálogo servido pela API e combina com a pesquisa', () => {
  const view = read('src/app/bjn/demands/demand-list.component.ts');
  const api = read('src/app/core/bjn-demand-api.service.ts');
  assert.ok(view.includes('Assunto / natureza'));
  assert.ok(view.includes("configuration()?.available_natures||[]"));
  assert.ok(view.includes('nature:this.nature'));
  assert.ok(view.includes("this.nature='';"));
  assert.ok(api.includes('nature?:string'));
});

test('gestor encontra exclusão na distribuição, com motivo e confirmação', () => {
  const list = read('src/app/bjn/demands/demand-list.component.ts');
  const detail = read('src/app/bjn/demands/demand-detail.component.ts');
  const api = read('src/app/core/bjn-demand-api.service.ts');
  for (const action of ['startExclusion(', 'confirmExclusion(', 'scopeExclusionReason', 'canExclude(item)']) {
    assert.ok(list.includes(action), `Ação não encontrada: ${action}`);
  }
  assert.ok(list.includes("configuration()?.actor?.role==='admin'"));
  assert.ok(detail.includes('demand.can_exclude_scope'));
  assert.ok(detail.includes('this.api.excludeScope(this.demandId,this.scopeExclusionReason.trim())'));
  assert.ok(api.includes('/exclusao-escopo'));
});

test('Todos os status inclui demandas excluídas, mas Pendentes segue operacional', () => {
  const list = read('src/app/bjn/demands/demand-list.component.ts');
  assert.ok(list.includes('<option value="">Todos os status</option>'));
  assert.ok(list.includes('pending_only:this.tab()===\'pending\''));
  assert.ok(list.includes("item.status!=='EXCLUIDA_ESCOPO' && !item.lawyer_email"));
  assert.ok(list.includes('mas não será exibida em “Pendentes”'));
});

test('anexos do parecer são enviados com publicação e consultáveis na Central', () => {
  const detail = read('src/app/bjn/demands/demand-detail.component.ts');
  const api = read('src/app/core/bjn-demand-api.service.ts');
  for (const action of ['selectOpinionAttachments(', 'removeOpinionAttachment(', 'opinionDocuments(', 'this.opinionFiles()', 'PARECER_COMPLEMENTAR']) {
    assert.ok(detail.includes(action), `Fluxo de anexos incompleto: ${action}`);
  }
  assert.ok(api.includes('/parecer/publicar-com-anexos'));
  assert.ok(api.includes("form.append('files',file,file.name)"));
  assert.ok(detail.includes('Documentos complementares publicados pelo advogado responsável.'));
});

test('componentes e contratos modificados têm sintaxe TypeScript válida', () => {
  for (const file of ['src/app/core/bjn-demand-api.service.ts', 'src/app/bjn/demands/demand-list.component.ts',
                      'src/app/bjn/demands/demand-detail.component.ts','src/app/bjn/demands/demand-ui.ts']) {
    const parsed=ts.createSourceFile(file, read(file), ts.ScriptTarget.Latest, true, ts.ScriptKind.TS);
    const problems=parsed.parseDiagnostics.map(problem=>ts.flattenDiagnosticMessageText(problem.messageText,' '));
    assert.deepEqual(problems, [], `${file}: ${problems.join('; ')}`);
  }
});
