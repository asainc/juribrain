'use strict';
// Verificações estruturais sem depender de uma instalação npm bem-sucedida.
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const ts = require('typescript');
const root = path.resolve(__dirname, '..');
function read(relativePath) { return fs.readFileSync(path.join(root, relativePath), 'utf8'); }

test('hub mantém seis abas funcionais e acesso à página original', () => {
  const source = read('src/app/chatbot/chatbot-page.component.ts');
  for (const tab of ['panorama', 'cronologia', 'agenda', 'provas', 'documentos', 'perguntas']) {
    assert.ok(source.includes(`id: '${tab}'`));
    assert.ok(source.includes(`activeTab() === '${tab}'`));
  }
  for (const name of ['openSource', 'exportDossier', 'searchDocuments', 'askDocuments', 'endSession']) {
    assert.ok(source.includes(`${name}(`));
  }
  assert.ok(source.includes('selectedArea'));
  assert.ok(source.includes('status_verificacao') === false); // Essa decisão pertence ao contrato backend.
});

test('contratos e cliente têm API contextual sem retirar Q&A genérico', () => {
  const api = read('src/app/chatbot/core/ai-ready-api.service.ts');
  const contracts = read('src/app/chatbot/core/contracts.ts');
  for (const path of ['/perguntar-autos', '/buscar', '/chat', '/analisar']) assert.ok(api.includes(path));
  for (const name of ['DocketAnswer', 'DocketAgendaItem', 'DocketEvidenceItem', 'DocketSearchHit']) assert.ok(contracts.includes(`type ${name}`));
  assert.ok(api.includes("data.append('tipo_processo', tipoProcesso)"));
});

test('código TypeScript novo preserva sintaxe sintática sem importar Angular', () => {
  for (const file of [
    'src/app/chatbot/chatbot-page.component.ts',
    'src/app/chatbot/core/ai-ready-api.service.ts',
    'src/app/chatbot/core/contracts.ts',
  ]) {
    const source = read(file);
    const parsed = ts.createSourceFile(file, source, ts.ScriptTarget.Latest, true, ts.ScriptKind.TS);
    assert.deepEqual(parsed.parseDiagnostics.map(item => ts.flattenDiagnosticMessageText(item.messageText, ' ')), []);
  }
});
