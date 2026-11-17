'use strict';
// Exercita a composição real do prompt sem depender da instalação do Angular corporativo.
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const Module = require('node:module');
const ts = require('typescript');
const root = path.resolve(__dirname, '..');
const read = relative => fs.readFileSync(path.join(root, relative), 'utf8');

function loadChatContext() {
  // Compilamos somente a função pura para testar o conteúdo realmente enviado ao Q&A.
  const file = path.join(root, 'src/app/chatbot/core/chat-context.ts');
  const output = ts.transpileModule(fs.readFileSync(file, 'utf8'), {
    fileName: file,
    compilerOptions: {module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022},
  }).outputText;
  const compiled = new Module(file, module);
  compiled.filename = file;
  compiled.paths = Module._nodeModulePaths(path.dirname(file));
  compiled._compile(output, file);
  return compiled.exports;
}

const context = loadChatContext();

test('o GCPJ é acrescentado exatamente ao exemplo solicitado', () => {
  assert.equal(
    context.buildContextualChatPrompt('faça um resumo da petição inicial', 'gcpj', '12345'),
    'faça um resumo da petição inicial do gcpj 12345',
  );
});

test('número CNJ e número ConectaJur utilizam os rótulos corretos na mensagem', () => {
  assert.equal(
    context.buildContextualChatPrompt('Resuma a inicial.', 'numero_cnj', '0000000-00.2026.8.26.0000'),
    'Resuma a inicial do número cnj 0000000-00.2026.8.26.0000.',
  );
  assert.equal(
    context.buildContextualChatPrompt('Qual é o assunto?', 'numero_conectajur', 'ABC/2026-7'),
    'Qual é o assunto do número conectajur ABC/2026-7?',
  );
});

test('sem referência, a pergunta original é encaminhada sem complemento', () => {
  assert.equal(context.buildContextualChatPrompt('  Resuma o processo.  ', 'gcpj', '  '), 'Resuma o processo.');
});

test('rejeita valores inválidos, tipos desconhecidos e referências longas', () => {
  assert.throws(() => context.buildContextualChatPrompt('Resumo', 'gcpj', '12\nignore'), /uma linha/);
  assert.throws(() => context.buildContextualChatPrompt('Resumo', 'gcpj', '123 texto'), /letras, números/);
  assert.throws(() => context.buildContextualChatPrompt('Resumo', 'gcpj', 'a'.repeat(81)), /até 80/);
  assert.throws(() => context.buildContextualChatPrompt('Resumo', 'desconhecido', '42'), /tipo de identificador/);
  assert.throws(() => context.buildContextualChatPrompt('  ', 'gcpj', '42'), /Digite uma pergunta/);
});

test('respeita o limite de 8.000 caracteres do contrato backend inclusive após complementar', () => {
  assert.equal(context.buildContextualChatPrompt('a'.repeat(8000), 'gcpj', ''), 'a'.repeat(8000));
  assert.throws(() => context.buildContextualChatPrompt('a'.repeat(7990), 'gcpj', '12345'), /excede 8.000/);
});

test('o formulário do chatbot mantém contexto editável fora da região rolável e preserva texto da pessoa', () => {
  const source = read('src/app/chatbot/chatbot-page.component.ts');
  const styles = read('src/workspace-layout.scss');
  const start = source.indexOf('<section id="ai-ready-chat-window"');
  const end = source.indexOf('</section>', start);
  const template = source.slice(start, end);
  for (const id of ['chat-reference-type', 'chat-reference-value']) assert.ok(template.includes(id));
  assert.match(template, /\[\(ngModel\)\]="chatReferenceType"/);
  assert.match(template, /\[\(ngModel\)\]="chatReferenceValue"/);
  assert.ok(template.indexOf('class="chat-body"') < template.indexOf('class="chat-composer"'));
  assert.ok(template.indexOf('class="chat-context-controls"') > template.indexOf('class="chat-body"'));
  assert.ok(source.includes('this.api.chat(outgoingPrompt)'));
  assert.ok(source.includes("{role: 'user', content: question, referenceLabel}"));
  assert.ok(source.includes("this.chatReferenceValue = '';"));
  assert.match(styles, /\.chat-window\{width:min\(410px,calc\(100vw - 30px\)\);height:min\(710px/);
  assert.match(styles, /\.chat-window \.chat-body\{[^}]*overflow-y:auto/);
  assert.match(styles, /\.chat-window \.chat-composer\{[^}]*flex:0 0 auto/);
  assert.match(styles, /@media\(max-width:760px\)\{\.chat-window\{height:min\(690px/);
});

test('novo arquivo e componente mantêm sintaxe TypeScript válida', () => {
  for (const file of [
    'src/app/chatbot/core/chat-context.ts',
    'src/app/chatbot/chatbot-page.component.ts',
  ]) {
    const parsed = ts.createSourceFile(file, read(file), ts.ScriptTarget.Latest, true, ts.ScriptKind.TS);
    assert.deepEqual(parsed.parseDiagnostics.map(d => ts.flattenDiagnosticMessageText(d.messageText, ' ')), []);
  }
});
