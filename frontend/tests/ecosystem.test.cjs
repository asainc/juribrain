/** Testes da navegação integrada sem presumir disponibilidade da API externa. */
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const root = path.resolve(__dirname, '..');
function read(relativePath) { return fs.readFileSync(path.join(root, relativePath), 'utf8'); }

test('a home acessa todas as aplicações por rotas reais', () => {
  const home = read('src/app/home/ecosystem-home.component.ts');
  for (const route of ['/bjn','/auditoria-pagamentos/calculo','/chatbot']) {
    assert.match(home, new RegExp(`routerLink="${route}"`));
  }
});

test('a configuração e o proxy compartilham o mesmo host e separam as versões', () => {
  const config = JSON.parse(read('public/app-config.json'));
  const proxy = JSON.parse(read('proxy.conf.json'));
  assert.equal(config.apiBaseUrl, '/api/v3');
  assert.equal(config.auditApiBaseUrl, '/services/auditoria/api/v2');
  assert.equal(config.chatbotApiBaseUrl, '/services/chatbot/api/v3');
  assert.ok(proxy['/api'] && proxy['/services']);
});

test('os três módulos mantêm seus próprios contratos e navegação', () => {
  const shell = read('src/app/app.component.ts');
  const audit = read('src/app/auditoria/calculation/calculation-page.component.ts');
  const chat = read('src/app/chatbot/chatbot-page.component.ts');
  const bjn = read('src/app/bjn/bjn-page.component.ts');
  assert.match(shell, /'auditoria'/);
  assert.match(shell, /'chatbot'/);
  assert.match(audit, /CalculationPageComponent/);
  assert.match(chat, /ChatbotPageComponent/);
  assert.match(bjn, /BjnPageComponent/);
});
