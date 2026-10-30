/**
 * Instala o frontend e recupera uma falha conhecida do Arborist no npm 10.
 *
 * Entrada: `npm run setup` dentro de frontend, registry npm já autorizado
 * pela organização e ferramentas Node/npm instaladas no computador.
 * Saída: `node_modules` validado ou erro objetivo de configuração.
 *
 * Decisão: primeiro executar a instalação padrão. Somente quando o npm
 * apresentar explicitamente o defeito `edgesOut`, tentar uma segunda vez
 * com `--legacy-peer-deps`. Esse parâmetro contorna o defeito do npm, mas
 * não dispensa testes de compilação ou aprovação de dependências.
 * Nenhum arquivo .env, cache ou lockfile preexistente é apagado automaticamente.
 */
import { spawnSync } from 'node:child_process';
import { existsSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { inspectInstallation } from './doctor.mjs';
import { installArguments, isPeerGraphCrash, isSupportedNode } from './install-core.mjs';

const projectRoot = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const npmCli = process.env.npm_execpath;

/**
 * Usa o mesmo npm que chamou `npm run setup`, sem depender de `npm.cmd`
 * ou da política de execução de scripts do PowerShell.
 */
function runInstall(args) {
  const result = spawnSync(process.execPath, [npmCli, ...args], {
    cwd: projectRoot,
    encoding: 'utf8',
    maxBuffer: 24 * 1024 * 1024,
    timeout: 20 * 60 * 1000,
    windowsHide: true,
    env: process.env,
  });
  return { ok: result.status === 0 && !result.error, log: `${result.stdout ?? ''}\n${result.stderr ?? ''}`, error: result.error };
}

/**
 * Mostra a categoria de falha, sem copiar logs que possam conter informações
 * internas de registries corporativos.
 */
function fail(message) {
  console.error(`Instalação não concluída: ${message}`);
  console.error('Consulte o log local do npm. Não compartilhe tokens nem URLs com credenciais.');
  process.exitCode = 1;
}

function main() {
  if (!npmCli || !npmCli.endsWith('.js') || !existsSync(npmCli)) {
    return fail('execute este processo pelo comando "npm run setup".');
  }
  if (!isSupportedNode(process.versions.node)) {
    return fail(`Node.js ${process.versions.node} incompatível. Use Node.js 22.12+ (linha 22) ou 24.x.`);
  }

  const hasLockFile = existsSync(resolve(projectRoot, 'package-lock.json'));
  console.log(`Instalando dependências pelo npm configurado (lockfile ${hasLockFile ? 'presente' : 'ainda não gerado'})...`);
  let attempt = runInstall(installArguments({ hasLockFile }));

  if (!attempt.ok && isPeerGraphCrash(attempt.log)) {
    console.warn('Falha conhecida do npm detectada: edgesOut. Repetindo com correção de resolução de peers.');
    console.warn('A recuperação é excepcional: valide a árvore e execute npm run build antes de homologar.');
    attempt = runInstall(installArguments({ hasLockFile, peerWorkaround: true }));
  }
  if (!attempt.ok) {
    const explanation = attempt.error?.code === 'ETIMEDOUT' ? 'tempo limite excedido; confira o Nexus e a conexão.'
      : isPeerGraphCrash(attempt.log) ? 'o npm ainda apresentou edgesOut; avalie a atualização homologada do npm.'
      : 'verifique no log do npm o acesso ao registry, as versões e as dependências conflitantes.';
    return fail(explanation);
  }

  const problems = inspectInstallation();
  if (problems.length) return fail(`pacotes essenciais não foram instalados corretamente: ${problems.join(' | ')}`);
  console.log('Dependências Angular principais encontradas nas versões declaradas.');
  console.log('Próximos passos: npm run doctor; npm run build; npm start.');
  console.log('O processo de instalação não substitui revisão de segurança, lockfile e homologação corporativa.');
}

main();
