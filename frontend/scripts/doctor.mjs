/**
 * Verificação local do ambiente Angular antes de iniciar o frontend.
 * Entrada: package.json e conteúdo da pasta node_modules.
 * Saída: diagnóstico explícito com exit code 0 ou 1, sem acessar a rede.
 *
 * Por que: a instalação interrompida pelo npm pode deixar o comando `ng`
 * presente, mas sem o builder `@angular/build:dev-server` necessário.
 */
import { existsSync, readFileSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { isSupportedNode } from './install-core.mjs';

const projectRoot = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const manifest = JSON.parse(readFileSync(join(projectRoot, 'package.json'), 'utf8'));
const required = [
  '@angular/cli',
  '@angular/build',
  '@angular/compiler-cli',
  '@angular/core',
  '@angular/common',
  'typescript',
];

/**
 * Lê somente metadados de dependências locais, sem executar código delas.
 * Retorna `null` quando o pacote ainda não foi instalado completamente.
 */
export function installedVersion(packageName, projectDir = projectRoot) {
  const packagePath = join(projectDir, 'node_modules', ...packageName.split('/'), 'package.json');
  if (!existsSync(packagePath)) return null;
  try {
    return JSON.parse(readFileSync(packagePath, 'utf8')).version ?? null;
  } catch {
    return null;
  }
}

/**
 * Detecta dependências ausentes ou divergentes de suas versões aprovadas.
 * A comparação usa os manifestos de topo; não tenta aprovar o grafo transitivo.
 */
export function inspectInstallation(projectDir = projectRoot, packageManifest = manifest) {
  return required.flatMap(packageName => {
    const actual = installedVersion(packageName, projectDir);
    const expected = packageManifest.dependencies?.[packageName]
      ?? packageManifest.devDependencies?.[packageName];
    if (!expected) return [`${packageName}: não declarado no projeto.`];
    if (actual === null) return [`${packageName}: não instalado.`];
    if (actual !== expected) return [`${packageName}: esperado ${expected}, encontrado ${actual}.`];
    return [];
  });
}

/**
 * Confere versão de Node e os pacotes essenciais antes de acionar `ng serve`.
 * Erros são tratados com mensagens de recuperação, não com stack traces.
 */
function main() {
  const problems = [];
  if (!isSupportedNode(process.versions.node)) {
    problems.push(`Node.js ${process.versions.node} fora do intervalo esperado: 22.12+ (linha 22) ou linha 24.`);
  }
  problems.push(...inspectInstallation());
  if (problems.length) {
    console.error('Frontend ainda não está pronto para executar:');
    for (const problem of problems) console.error(`  - ${problem}`);
    console.error('Correção: na pasta frontend, execute npm run setup e depois npm start.');
    process.exitCode = 1;
  } else {
    console.log('Ambiente Angular verificado: Node.js e dependências principais disponíveis.');
  }
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) main();
