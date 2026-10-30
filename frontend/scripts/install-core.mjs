/**
 * Funções puras usadas pela instalação e pelos testes de regressão.
 *
 * O npm 10 pode falhar ao montar dependências opcionais com a mensagem
 * `edgesOut`. Limitamos a recuperação a esse erro específico para não
 * mascarar falhas de rede, credenciais, integridade ou conflitos reais.
 */
export function isPeerGraphCrash(output) {
  return /Cannot read properties of null\s*\(reading ['"]edgesOut['"]\)/i.test(String(output));
}

/**
 * Confere se a versão de Node.js pertence a uma linha suportada pelo projeto.
 * O intervalo é propositalmente menor que o suporte geral do Angular 21:
 * evitamos trocar de linha LTS sem revisão da equipe responsável.
 */
export function isSupportedNode(version) {
  const match = /^(\d+)\.(\d+)\.(\d+)$/.exec(String(version));
  if (!match) return false;
  const [major, minor] = match.slice(1).map(Number);
  return (major === 22 && minor >= 12) || major === 24;
}

/**
 * Constrói os argumentos sem interpolação em shell, evitando interpretar
 * nomes de arquivos ou parâmetros como comandos de sistema.
 */
export function installArguments({ hasLockFile, peerWorkaround = false } = {}) {
  return [
    hasLockFile ? 'ci' : 'install',
    '--include=dev',
    '--include=optional',
    '--no-audit',
    '--no-fund',
    ...(peerWorkaround ? ['--legacy-peer-deps'] : []),
  ];
}
