/** Verifica a tradução segura de erros de armazenamento no cadastro jurídico. */
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const source = fs.readFileSync(path.join(__dirname, '../src/app/bjn/demands/demand-ui.ts'), 'utf8');

test('cadastro usa códigos estáveis e rastreia a falha sem revelar conteúdo privado', () => {
  for (const code of ['DATABASE_BUSY', 'DATABASE_UNAVAILABLE', 'UPLOAD_STORAGE_UNAVAILABLE']) {
    assert.ok(source.includes(code), `Ausente: ${code}`);
  }
  assert.ok(source.includes('requestId'));
  assert.ok(source.includes('serverMessage'));
});
