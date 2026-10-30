const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const root = path.resolve(__dirname, '..');

function read(relativePath) {
  return fs.readFileSync(path.join(root, relativePath), 'utf8');
}

test('a navegação principal oferece três aplicações, homepage e alias do AI Ready', () => {
  const routes = read('src/app/app.routes.ts');
  assert.equal(routes.includes("path: 'ai-ready'"), true);
  assert.equal(routes.includes("path: 'bjn'"), true);
  assert.equal(routes.includes("path: 'auditoria-pagamentos'"), true);
  assert.equal(routes.includes("path: 'chatbot'"), true);
  assert.equal(routes.includes("redirectTo: 'chatbot'"), true);
  assert.equal(routes.includes("path: ''"), true);
});

test('AI Ready possui upload, linha do tempo e chat flutuante', () => {
  const component = read('src/app/ai-ready/ai-ready-page.component.ts');
  assert.equal(component.includes('Adicionar PDFs'), true);
  assert.equal(component.includes('Linha do tempo dos fatos'), true);
  assert.equal(component.includes('chat-launcher'), true);
  assert.equal(component.includes('gpt_bradesco.agente_informacional'), true);
});

test('o frontend executável contém BJN, auditoria, chatbot e página inicial', () => {
  const appEntries = fs.readdirSync(path.join(root, 'src/app'), {withFileTypes: true}).map(item => item.name).sort();
  assert.deepEqual(appEntries, ['ai-ready', 'app.component.ts', 'app.routes.ts', 'auditoria', 'bjn', 'chatbot', 'core', 'home', 'shared', 'templates'].sort());
});


test('contratos de evidência usam documento em português em todo o template', () => {
  const component = read('src/app/ai-ready/ai-ready-page.component.ts');
  assert.equal(component.includes('event.document +'), false);
  assert.equal(component.includes('source.document +'), false);
  assert.equal(component.includes('{{ source.document }}'), false);
  assert.equal(component.includes('event.documento +'), true);
  assert.equal(component.includes('{{ event.documento }}'), true);
});

test('orquestrador local aguarda a versão atual da API', () => {
  const startDev = read('../scripts/start-dev.mjs');
  assert.equal(startDev.includes('/api/v2/saude'), false);
  assert.equal(startDev.includes('/api/v3/saude'), true);
  assert.equal(startDev.includes("join(root, 'src')"), false);
});


test('chatbot fica à direita e usa a API Q&A sem depender do workspace', () => {
  const component = read('src/app/ai-ready/ai-ready-page.component.ts');
  const api = read('src/app/core/ai-ready-api.service.ts');
  const workspaceStyles = read('src/workspace-layout.scss');

  assert.equal(workspaceStyles.includes('.chat-launcher{position:fixed;right:22px'), true);
  assert.equal(workspaceStyles.includes('.chat-window{position:fixed;right:22px'), true);
  assert.equal(component.includes('gpt_bradesco.agente_informacional'), true);
  assert.equal(component.includes('if (!workspaceId || !question'), false);
  assert.equal(component.includes('this.api.chat(question)'), true);
  assert.equal(component.includes('response.resposta'), true);
  assert.equal(api.includes('/ai-ready/chat'), true);
  assert.equal(api.includes('chat(workspaceId'), false);
});
