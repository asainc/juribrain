# Instalação, configuração e suporte

## Ambiente homologável

Recomenda-se Python 3.12, Node.js e npm conforme `frontend/package.json`, um ambiente virtual dedicado, acesso autorizado ao registry npm e PyPI/Nexus corporativo. Arquivos `.env` são **locais** e não devem estar presentes no ZIP de entrega.

### Passo a passo (Windows)

```powershell
py -3.12 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.lock
python -m pip install --no-deps -e .
Copy-Item .env.example .env
cd frontend
npm run setup
npm run doctor
npm run build
cd ..
node scripts/start-dev.mjs
```

No Linux, use `python3.12 -m venv .venv` e `source .venv/bin/activate`; substitua `Copy-Item` por `cp`. Instale pacotes corporativos somente a partir de fontes permitidas.

### Recuperação rápida do frontend

Na pasta `frontend`:

```powershell
node --version
npm --version
npm config get registry
npm run setup
npm run doctor
npm run build
npm start
```

O instalador não altera automaticamente as configurações npm globais nem faz atualização de versões. A segunda tentativa com `--legacy-peer-deps` ocorre **somente** se a falha tiver a assinatura `edgesOut`, devido a um defeito conhecido do npm 10. É uma medida de recuperação para desenvolvimento, não uma aprovação de dependências conflitantes. A compilação e os testes com o repositório autorizado são obrigatórios antes da homologação.

## Endpoints de saúde

- BJN `GET http://127.0.0.1:8000/api/v3/saude`
- Auditoria `GET http://127.0.0.1:8000/services/auditoria/api/v2/saude`
- Chatbot `GET http://127.0.0.1:8000/services/chatbot/api/v3/saude`
- Behavior `GET http://127.0.0.1:8000/api/v3/laboratorio-comportamental/configuracao` (informa configuração local, não disponibilidade externa)

**Observação:** responder 200 nesses endpoints atesta apenas roteamento e inicialização local; não comprova disponibilidade de modelo de IA, credenciais, homologação financeira ou segurança de produção.

### Ajuste das portas

Edite `config/runtime.json` ou exporte `BACKEND_PORT` e `FRONTEND_PORT` antes de chamar `node scripts/start-dev.mjs`. O script gera `frontend/.runtime-proxy.json` com ambos os prefixos; removerá o arquivo ao encerrar. A configuração da SPA `frontend/public/app-config.json` contém URLs relativas por padrão e não requer troca de porta.

### Configuração dos quatro produtos

- **Todos:** o único arquivo de ambiente é `.env` **na raiz**, ou um mesmo arquivo externo indicado por `APP_ENV_FILE`. `backend/central_environment.py` centraliza a leitura; `gpt_bradesco.py` existe somente na raiz. Configure identificador, senha, deployment e `BRADESCO_QA_WORKFLOW_CODE` uma única vez.
- **BJN:** também lê `config/app.settings.json`, com chaves `BJN_*` no mesmo `.env`.
- **Auditoria:** conserva somente `applications/auditoria/config/app.settings.json` e `AUDITORIA_CONFIG_PATH` para parâmetros operacionais. Índices/dados locais permanecem isolados sob `applications/auditoria/data`.
- **Chatbot:** conserva `applications/chatbot/config/app.settings.json` e `CHATBOT_CONFIG_PATH` para parâmetros de análise documental.
- **Behavior:** mantém agentes, cenários e simulações em `.runtime/behavioral_lab/` por padrão, configuráveis via `BEHAVIORAL_LAB_*` no `.env` da raiz. O modo de simulação fictícia é restrito a `APP_ENV=local`.

Em produção, considere obter segredos de um vault corporativo em vez de arquivos locais. Não use caminhos compartilhados nem repositórios Git para persistir documentos jurídicos, valores pessoais, tokens, chaves ou arquivos extraídos.

### Diagnóstico

1. **Homepage não aparece:** valide `frontend/public/app-config.json`, dependências npm, `frontend/angular.json` e logs de `npm start`.
2. **Erro 404 em `/services`:** confirme o proxy do Angular e o encaminhamento de `/services` no gateway de produção.
3. **Auditoria não calcula:** verifique os pacotes `judicial_calc`, `pandas`, `pypdf`, `openpyxl`, `xlrd` e as fontes de índices, executando testes de negócio homologados.
4. **Chatbot/IA indisponíveis:** verifique credenciais na origem autorizada, URL/ambiente, deployment e os endpoints específicos de cada produto; não imprima prompts ou tokens em logs.
5. **Erro `edgesOut` no npm 10:** execute `cd frontend` e `npm run setup`. O instalador tenta a instalação normal e aplica a recuperação `--legacy-peer-deps` somente se o erro específico for detectado. Depois rode `npm run doctor` e `npm run build` para verificar presença do builder Angular e compilação.
6. **`@angular/build:dev-server` ausente:** significa que o builder local não está completo. Execute `npm run doctor`, instale as dependências de desenvolvimento com `npm run setup` e não tente `npm start` antes do sucesso da instalação. Não use `npm install --omit=dev` ou `--production` para desenvolvimento.
7. **Erro de rede, Nexus, 401, integridade ou ERESOLVE:** não são corrigidos automaticamente pelo instalador. Confira `npm config get registry`, `node -v`, `npm -v` e o log local, mantendo segredos fora de tickets. Acione o suporte corporativo quando necessário; não desabilite o registry homologado.
8. **Ausência de package-lock.json:** a origem dos projetos não incluiu um lockfile, e o pacote entregue não inclui `node_modules`. Depois de obter dependências do registry homologado, revise e versione o lockfile para permitir instalações reproduzíveis. Não execute `npm ci` sem lockfile.

### Testes locais

```bash
python -m pytest -q tests
cd frontend
npm test
npm run build
```

O teste de backend considera arquivos sintéticos e saúde das aplicações. Não substitui testes reais dos fluxos de BJN, índices, cálculo, publicação de parecer ou integrações com IA homologados pelos responsáveis.
