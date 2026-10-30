# Arquitetura e decisões técnicas do ecossistema

Data da integração: 29/10/2026. Responsable técnico: time mantenedor da aplicação (atribuição pela organização).

## ADR-001 — Um frontend Angular e um servidor ASGI

**Contexto**: as três fontes tinham `frontend/src/app/app.component.ts`, `backend/principal.py` e `backend/config.py` homônimos, versões de contrato HTTP distintas e folhas de estilo sobrepostas. Mesclar esses arquivos diretamente criaria colisões e risco de misturar contratos.

**Decisão**: BJN é a base visual e o host FastAPI. Auditoria e Chatbot foram preservados como aplicações FastAPI isoladas em `applications/`. O host as monta em `/services/auditoria` e `/services/chatbot`, mantendo `api/v2` e `api/v3` originais dentro de cada subapp. As rotas BJN seguem em `/api/v3`. Um único Angular possui rotas e página inicial para os três produtos.

**Justificativa**: mantém a compatibilidade com a lógica original, elimina portas e servidores independentes, reduz retrabalho e isola regras de cálculo e documentais.

**Trade-off**: um erro fatal do processo hospedeiro pode afetar todos os módulos; dimensionamento independente requer separar serviços em implantações futuras. Não é garantia de isolamento de processo nem sandbox de segurança.

## ADR-002 — Preservar visual e separar estilos

Reutilizados os tokens de estilo, navegação, tipografia e vermelho de destaque do BJN. A folha original de Auditoria é incluída em `frontend/src/audit-scoped.scss` com seletores sob `.module-audit`. A home usa `frontend/src/ecosystem.scss`. Os seletores de shell de auditoria foram excluídos dos estilos específicos para evitar sobrescrever a barra lateral comum.

**Trade-off**: futuras regras CSS globais de auditoria precisam ser adicionadas sob o mesmo escopo. Valide os breakpoints e o zoom em homologação antes de distribuir para os usuários finais.

## ADR-003 — Configuração em tempo de execução

`frontend/public/app-config.json` contém `apiBaseUrl`, `auditApiBaseUrl`, `chatbotApiBaseUrl` e `pollIntervalMs`. `ApiConfiguration.load()` exige URLs HTTP(S) válidas e carrega o JSON antes da renderização. No desenvolvimento, o proxy Angular encaminha `/api` e `/services` para o servidor FastAPI local. Em produção, o gateway deve encaminhar esses dois prefixos ao mesmo host, ou o arquivo deve ser atualizado para as URLs autorizadas.

**Justificativa**: uma compilação Angular serve aos três serviços; não há fallback silencioso para API incorreta.

## ADR-004 — Independência das configurações e segredos

BJN: `.env` e `config/app.settings.json`. Auditoria: `applications/auditoria/.env`, `AUDITORIA_ENV_FILE`, `AUDITORIA_CONFIG_PATH` e JSON específico. Chatbot: `applications/chatbot/.env`, `CHATBOT_ENV_FILE`, `CHATBOT_CONFIG_PATH` e JSON específico. Se as três integrações usam a mesma identidade corporativa, prefira injeção comum via secret manager, sem duplicar credenciais em código.

**Trade-off**: os nomes de variáveis corporativas do gateway mantêm o contrato original em cada produto. Variáveis de ambiente de sistema podem afetar mais de um serviço; revise o escopo ao publicar.

## ADR-005 — Preservação do motor financeiro e controles humanos

O código de `judicial_calc` foi mantido em `applications/auditoria/src/judicial_calc`, com alterações limitadas aos imports de namespace para permitir execução no mesmo processo. A origem de política e séries permanece sob o diretório `applications/auditoria`. A mera integração não revalida regras de juros, atualização, tributação ou interpretação jurídica; exija homologação funcional do responsável.

As rotas de BJN e Chatbot não substituem revisão jurídica humana. O frontend não simula métricas operacionais, quantidades de demandas nem disponibilidade de modelos.

## Fluxo de requisição e auditoria

1. O usuário abre `/`, escolhe o módulo e navega pela SPA.
2. O componente do módulo chama o respectivo serviço HTTP Angular.
3. O serviço usa o endpoint definido em `app-config.json`.
4. Angular proxy ou gateway encaminha a rota para o host FastAPI.
5. BJN responde diretamente, Auditoria/Chatbot passam para a subaplicação montada.
6. Cada serviço registra seu identificador de requisição e eventos técnicos, sem conteúdo sensível. O fluxo de dados e a persistência continuam separados por módulo.

### Limitações e verificações antes da produção

- Validar SSO, cabeçalhos de identidade, RBAC, gateway e princípio de menor privilégio.
- Auditar permissões de arquivos, logs, criptografia, bases locais e política de retenção.
- Homologar os parâmetros de cálculo, índices e taxas do motor com o time jurídico e financeiro.
- Verificar prompts, respostas de IA, mascaramento de dados, revisão humana e limites de uso.
- Compilar o Angular usando o registro npm homologado. Testar layout, zoom, teclado e versões de navegadores corporativos.
- Executar testes end-to-end e de contrato com payloads sintéticos, sem expor dados pessoais nem segredos.

## ADR-006 — Instalação npm resiliente e rastreável (30/10/2026)

**Contexto:** a primeira distribuição do ecossistema não continha `node_modules` nem `package-lock.json`. Em npm 10.9.x, o instalador pode interromper a resolução de peers com `Cannot read properties of null (reading 'edgesOut')`. Nesse estado, `npm start` falha por ausência de `@angular/build:dev-server`.

**Decisão:** `frontend/scripts/setup.mjs` sempre tenta primeiro `npm install` (ou `npm ci`, quando existe lockfile), incluindo dependências de desenvolvimento e opcionais. Apenas após detectar a assinatura exata `edgesOut`, realiza uma segunda tentativa com `--legacy-peer-deps`. Erros de autenticação, indisponibilidade do registry, integridade e conflitos diferentes não acionam a recuperação. A rotina preserva arquivos de configuração, lockfile e cache existentes e verifica os pacotes Angular principais ao terminar. `frontend/scripts/doctor.mjs` também é executado automaticamente antes de `npm start`.

**Compatibilidade:** `package.json` aceita Node.js 22.12+ na linha 22 ou Node.js 24.x, conforme versões compatíveis com Angular 21. O baseline corporativo de lockfile (`npm@10.9.0`) é mantido até decisão expressa de atualização; os scripts de Nexus que exigem esse baseline continuam independentes.

**Justificativa:** evita transformar um erro conhecido do gerenciador de dependências em falha opaca do servidor Angular. Não muda código, API, regras jurídicas, interfaces nem políticas de autenticação dos três módulos.

**Limites e riscos:** `--legacy-peer-deps` reduz a validação automática de peers: não é permitido tratar a instalação como homologação. Validar `npm run build`, lockfile, tree de dependências, permissões, licenças, origem dos artefatos e testes completos no ambiente autorizado. Não foi possível baixar pacotes e compilar Angular neste ambiente sem registry npm disponível. A responsabilidade de revisão técnica e de segurança permanece com o time mantenedor.
