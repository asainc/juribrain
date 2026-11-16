# Ecossistema Jurídico

## Behavior — mapa editável, tempo e diagnóstico da IA corporativa

O mapa do Behavior aceita arrastar agentes por mouse/toque ou usar as setas do teclado. As posições são coordenadas relativas e ficam salvas **neste navegador por sociedade**; **Reorganizar mapa** restaura a disposição padrão. A simulação não depende da posição visual do nó.

A execução apresenta estado, tempo efetivo sem pausas confirmadas, início, término e motivo seguro das falhas. O motor **IA corporativa** utiliza `text_generator` do `gpt_bradesco.py` centralizado, com `BRADESCO_TEXT_MODEL` e temperatura por experimento. O `BRADESCO_QA_WORKFLOW_CODE` é exclusivo do Q&A e não seleciona o modelo de geração. O `.env` permanece único na raiz.

Confira diagnóstico, roteiro de homologação e limitações em [`docs/BEHAVIOR_MAPA_STATUS_BRIDGE_2026-11-16.md`](docs/BEHAVIOR_MAPA_STATUS_BRIDGE_2026-11-16.md). A pasta `.runtime` contém dados e chaves de **cada instalação** e não acompanha os pacotes de código; preserve-a separadamente durante atualizações. O build Angular e a conexão real com a Bridge devem ser validados no ambiente corporativo.


Aplicação única que reúne **BJN**, **Auditoria de Pagamentos**, **Chatbot / AI Ready** e **Behavior**. A interface e seus módulos originais usam a mesma identidade visual: superfícies claras, navegação lateral, tipografia grafite e acento vermelho. A entrada padrão agora é uma página inicial que encaminha a cada aplicativo.

## Primeira execução (Windows / Python 3.12)

**Pré-requisitos:** Python 3.12 (64 bits), Node.js 22.12+ (linha 22) ou 24.x e npm compatível com `frontend/package.json`, conectividade ao repositório corporativo aprovado para instalar dependências. As APIs de IA precisam de credenciais corporativas e de homologação da integração.

1. Extraia este ZIP inteiro e abra um terminal na pasta `ecossistema-juridico`.
2. Crie o ambiente Python: `py -3.12 -m venv .venv`.
3. Ative-o: `.venv\Scripts\activate` (PowerShell: `.venv\Scripts\Activate.ps1`).
4. Instale: `python -m pip install -r requirements.lock` e depois `python -m pip install --no-deps -e .`.
5. Crie **somente** `.env` na raiz com `Copy-Item .env.example .env`; configure `BRADESCO_IDENTIFICADOR`, `BRADESCO_SENHA` e `BRADESCO_QA_WORKFLOW_CODE` nesse local ou via gerenciador corporativo de segredos. Todos os módulos usam a mesma configuração. Nunca versione o arquivo.
6. Na pasta `frontend`, execute `npm run setup` (utilize o registry Nexus corporativo homologado). O instalador tenta a instalação normal e **apenas** se ocorrer o erro `edgesOut` do npm, aplica a recuperação de resolução de dependências.
7. Ainda em `frontend`, execute `npm run doctor` e `npm run build`. Se a compilação concluir, retorne à raiz.
8. Rode `node scripts/start-dev.mjs`. Abra `http://127.0.0.1:4200/`.

**Linux/macOS**: use `python3.12 -m venv .venv`, `source .venv/bin/activate` e os comandos posteriores sem alteração. Se o Python estiver no PATH, também é possível executar o backend isoladamente com `python scripts/run_backend.py` e o frontend com `cd frontend && npm start`.

> Instalações sem acesso ao registro npm corporativo não conseguem compilar a interface. A entrega contém o **código-fonte completo** e seus manifestos, mas não inclui `node_modules`, pacotes npm, binários nativos ou segredos. O `package-lock.json` não pôde ser gerado sem acesso ao registro homologado: após a primeira instalação bem-sucedida, valide e versione o arquivo conforme a governança da organização.

### Recuperação de erros do npm / Angular

O erro `Cannot read properties of null (reading 'edgesOut')` ocorre durante a resolução de dependências no npm 10, antes de completar a instalação. Consequentemente, `npm start` pode relatar `Could not find the '@angular/build:dev-server' builder's node package`. **Não é necessário trocar o design nem a versão Angular** para tentar a correção. No PowerShell, execute:

```powershell
cd frontend
npm run setup
npm run doctor
npm run build
npm start
```

O comando `setup` instala as dependências de desenvolvimento, incluindo `@angular/build`, e repete a instalação com `--legacy-peer-deps` **somente após detectar** o defeito específico `edgesOut`. Esse modo alternativo evita uma falha de resolução do npm, mas pode deixar conflitos de peers sem detecção automática. Execute o build, revise o lockfile resultante e solicite validação ao responsável pelo registro corporativo antes de uso produtivo. Os comandos não apagam o `node_modules`, lockfile, cache, `.env` ou configurações corporativas existentes.

Se a instalação continuar falhando, consulte o log local do npm e execute `npm config get registry`, `node --version` e `npm --version`. Confirme que a URL do registry é aprovada e acessível; não divulgue tokens. Uma atualização do npm pode contornar o defeito, mas só deve ocorrer com autorização de infraestrutura e de acordo com as versões homologadas. Nunca execute `npm start` após uma instalação que terminou com erro.


## BJN Demandas — atualização de 13/11/2026

- **Parecer automático:** ao abrir uma demanda atribuída no perfil advogado, o rascunho é iniciado pelo `text_generator` sem o botão de preparação. Nenhuma resposta é publicada sem revisão humana. A ausência da IA não impede parecer manual.
- **Solicitante:** agora é uma lista suspensa alimentada pelo arquivo CSV de departamentos; o nome do campo não inclui mais “Departamento”.
- **Departamento consultado:** aparece como primeira tela de Nova demanda. A escolha **4040 - Jurídico** encaminha à triagem atual, com as opções de ofícios e intimações. Os demais departamentos aguardam configuração de encaminhamento.
- **Agência bancária:** a pesquisa aceita partes do número ou nome, e o autocomplete utiliza um CSV de duas colunas.
- **Catálogos:** `data/cadastros/departamentos.csv` inclui a opção 4040 fornecida na especificação. `data/cadastros/agencias.csv` contém somente o cabeçalho; a lista real deve ser preenchida pelo responsável autorizado. Para usar CSVs externos, configure `BJN_DEPARTMENTS_CSV` e `BJN_AGENCIES_CSV` no ambiente.
  - Para consultar e acrescentar departamentos, use `python scripts/manage_bjn_departments.py list` e `python scripts/manage_bjn_departments.py add --code 1234 --name "Unidade Exemplo"` (códigos fictícios). Após salvar, clique **Atualizar lista** na tela. Veja `docs/BJN_ATUALIZACAO_DEPARTAMENTOS_E_SELETORES.md`.

Documentação: `docs/BJN_CADASTROS_DEPARTAMENTOS_AGENCIAS_PARECER_AUTOMATICO.md`.

## Erro de cadastro BJN — versão de 16/11/2026

Ao receber uma falha `O servidor não conseguiu concluir o cadastro. Identificador: ...`, não envie novamente antes de consultar a lista de demandas e conferir se o protocolo já existe. O identificador correlaciona a resposta aos logs do backend, mas não explica sozinho a origem do erro.

A versão atual separa a criação do protocolo das análises auxiliares e informa falhas de persistência ou diretório de anexos com códigos específicos. Para verificar localmente os caminhos configurados, catálogos e esquema da base **sem acessar os dados jurídicos**, execute na raiz do projeto:

```powershell
python scripts/diagnose_bjn_registration.py
```

Roteiro de diagnóstico e limitações: `docs/BJN_DIAGNOSTICO_CADASTRO_5XX_2026-11-16.md`. Nunca exclua banco de dados para tentar resolver a falha sem backup e autorização do responsável pela implantação.

## Gestão de demandas BJN — melhorias de novembro de 2026

- O filtro **Assunto / natureza** combina-se com status, datas e advogado na lista de demandas.
- O gestor pode **excluir do fluxo** demandas **ainda não distribuídas** quando fora do escopo, com justificativa obrigatória. É uma exclusão **lógica e auditável**, recuperável pelo filtro de status correspondente.
- Ao publicar um parecer, o advogado responsável pode anexar documentos complementares PDF/PNG/JPEG, que ficam visíveis na consulta da demanda e na Central de documentos. A publicação e os metadados dos anexos são gravados na mesma transação.

Detalhes técnicos, critérios de autorização, decisões e roteiro de homologação: `docs/BJN_FILTRO_EXCLUSAO_ANEXOS_PARECER_2026-11-05.md`.

## Tela inicial e rotas

| Solução | Rota no navegador | Funções preservadas |
| --- | --- | --- |
| Portal | `/` | Acesso aos quatro aplicativos |
| BJN | `/bjn` | Minutas e questionário, prévia de cláusulas e chat BJN |
| Demandas BJN | `/bjn/demandas` | Cadastro, acompanhamento e tramitação |
| Auditoria de Pagamentos | `/auditoria-pagamentos/calculo` | Conferência documental e cálculo judicial |
| Histórico | `/auditoria-pagamentos/historico` | Histórico de versões |
| Qualidade IA | `/auditoria-pagamentos/qualidade-ia` | Monitoramento da qualidade |
| Lotes | `/auditoria-pagamentos/lotes` | Importação e execução em lote |
| Índices | `/auditoria-pagamentos/indices` | Gestão de índices |
| Chatbot / AI Ready | `/chatbot` | Análise de PDFs, síntese, linha do tempo e perguntas e respostas |
| Behavior | `/behavior` | Agentes, cenários, simulações multiagente e observatório |

O link antigo `/ai-ready` redireciona para `/chatbot` sem quebrar favoritos anteriores.

## Arquitetura em execução

```text
Navegador
  └─ Angular único (porta 4200)
     ├─ Home /  navegação e identidade visual compartilhadas
     ├─ BJN (minutas e demandas)  ─────────── /api/v3/*
     ├─ Auditoria de Pagamentos ──────────── /services/auditoria/api/v2/*
     ├─ Chatbot / AI Ready ───────────────── /services/chatbot/api/v3/*
     └─ Behavior ─────────────────────────── /api/v3/laboratorio-comportamental/*
                    │  proxy Angular /api + /services
                    ▼
            FastAPI único (porta 8000)
             ├─ backend/ (BJN e API v3 existente)
             ├─ applications/auditoria/backend/ (FastAPI isolado e motor judicial_calc)
             ├─ applications/chatbot/backend/ (FastAPI isolado e IA documental)
             └─ applications/behavior/backend/ (extensão da API principal)
```

Auditoria e Chatbot são **montados em um único processo ASGI** e compartilham somente a infraestrutura HTTP. Contratos Pydantic, configurações, conexões, persistência, endpoints e versões permanecem isolados. Não se misturam dados de auditoria com dados de demandas BJN. O servidor principal inicializa e encerra o ciclo de vida da auditoria explicitamente.

### Onde estão as funcionalidades

- `frontend/src/app/home/`: nova página inicial com links reais.
- `frontend/src/app/bjn/`: telas BJN originais.
- `frontend/src/app/auditoria/`: telas e serviços Angular de auditoria; `frontend/src/audit-scoped.scss` mantém seus estilos separados.
- `frontend/src/app/chatbot/`: tela original de Chatbot/AI Ready, com URL de API independente.
- `backend/`: BJN e host do ecossistema.
- `applications/auditoria/backend/` e `applications/auditoria/src/judicial_calc/`: API de auditoria e motor de cálculo sem mudanças nas regras matemáticas.
- `applications/chatbot/backend/`: API de IA processual independente.
- `frontend/public/app-config.json`: três URLs de API definidas uma única vez para o frontend.
- `config/runtime.json` e `scripts/start-dev.mjs`: startup e proxy na mesma porta, com observação de alterações nos quatro módulos.

Consulte `docs/ARQUITETURA_ECOSSISTEMA.md` e `docs/INSTALACAO.md` para limitações, parâmetros, teste e decisões técnicas. Os manuais de origem da Auditoria e do Chatbot estão em `applications/<aplicacao>/docs/`; o manual do Behavior está em `docs/BEHAVIOR_V3_GUIDE.md`.

## Testes

```bash
python -m pytest -q tests
cd frontend
npm test
npm run build
```

As verificações e limitações desta integração estão documentadas em `docs/VALIDACAO_INTEGRACAO_BEHAVIOR_2026_11_16.md`. A compilação Angular `npm run build` não foi executada porque a instalação npm não estava disponível no ambiente de construção. A validação operacional ponta a ponta com modelos corporativos, documentos reais anonimizados e série de índices não foi efetuada. Antes de publicar, execute os testes de negócio e segurança no ambiente de homologação e obtenha aprovação de Jurídico/Compliance/DPO conforme aplicável.

## Segurança

A autenticação de produção, permissão por função, tratamentos de documentos, retenção, dados pessoais, integrações com IA, operações de cálculo e critérios de revisão humana precisam ser avaliados pelo time responsável. Nenhum código substitui a validação jurídica dos pareceres, cláusulas ou cálculos. Segredos devem ficar fora do Git, de logs e do frontend. Não envie material de produção não anonimizado ao ambiente de teste.

## Hub de inteligência processual — cível e trabalhista

Acesse **Chatbot / AI Ready** na página inicial (`/chatbot`). A interface preserva as cores e o layout das aplicações integradas. Selecione **Processo cível** ou **Processo trabalhista**, envie PDFs pesquisáveis e clique em **Analisar processo**. Em seguida, navegue pelas seis abas: **Visão geral**, **Linha do tempo**, **Agenda e ações**, **Provas e lacunas**, **Documentos** e **Pergunte aos autos**.

- **Visão geral:** resumo, pedidos, partes, fatos controvertidos, alertas e roteiro de conferência adaptado à área selecionada.
- **Linha do tempo:** eventos com categoria e referência ao documento/página; o filtro limita os eventos mostrados.
- **Agenda e ações:** audiências, intimações, perícias e prazos **expressamente mencionados no texto**, apresentados como **pendentes de validação**. Não há contagem, cálculo de vencimento ou integração com diário/tribunal. Checklist temporário para revisão operacional.
- **Provas e lacunas:** itens levantados para conferência, com documento e página existentes. Não é um juízo sobre valor probatório, risco, êxito ou ônus da prova.
- **Documentos:** qualidade da extração textual por PDF, avisos de páginas com texto incompleto e **busca lexical** que mostra trechos originais e abre a página no visualizador.
- **Pergunte aos autos:** pesquisa de páginas relevantes seguida de uma pergunta ao **text_generator corporativo**. A resposta traz links para páginas recuperadas. Como o modelo pode errar, as citações são referências **para conferência**, não prova de que cada frase esteja correta.

O **chat flutuante** continua independente, conectado à API corporativa Q&A. Para perguntas sobre os arquivos enviados, utilize a aba **Pergunte aos autos**; o chat flutuante não recebe automaticamente o contexto dos PDFs. É possível **exportar um dossiê textual** no navegador e **encerrar a sessão**, removendo a seleção local e solicitando a exclusão do workspace em memória no servidor.

### API do hub

| Método | Caminho relativo à API chatbot | Descrição |
| --- | --- | --- |
| `POST` | `/ai-ready/analisar` | Multipart `files[]` e `tipo_processo=civel|trabalhista`; gera workspace temporário, agenda e evidências |
| `GET` | `/ai-ready/{workspace_id}/buscar?q=...` | Busca textual nas páginas armazenadas temporariamente |
| `POST` | `/ai-ready/perguntar-autos` | JSON `{"workspace_id":"...","pergunta":"..."}`; pergunta fundamentada em páginas recuperadas |
| `DELETE` | `/ai-ready/{workspace_id}` | Descarta o conteúdo temporário do workspace |

Na aplicação integrada, o prefixo é `/services/chatbot/api/v3`. Sem gerador corporativo configurado, não é possível criar novas análises; não há dados demonstrativos apresentados como se fossem processos reais. PDFs digitalizados sem camada de texto precisam ser disponibilizados em versão pesquisável. Não use dados de produção não anonimizados para testes.

As decisões de extração e limites de segurança estão em `docs/HUB_INTELIGENCIA_PROCESSUAL.md`. A parametrização geral e as instruções de `npm run setup` / `npm run doctor` da versão corrigida permanecem válidas.


## Demandas BJN — lote, pendências, filtros e validação de PDFs (30/10/2026)

Na página `/bjn/demandas`, o gestor pode marcar até 50 demandas em **Todas as demandas** e distribuí-las de uma única vez a advogado autorizado; na aba **Pendentes** vê todas as demandas não encerradas. O advogado vê somente pendências sob sua responsabilidade. Há filtros de data inicial/final (inclusive), advogado (nome conhecido no diretório ou e-mail), agência e solicitante. Para configurar nomes autorizados, adicione `bjn_lawyer_names` ao arquivo privado `config/app.settings.json`, mapeando e-mails da lista `bjn_allowed_lawyers` para nomes exibíveis.

No cadastro, a seleção/upload de PDF pesquisável inicia a identificação de natureza via `text_generator`. Os arquivos de definição ficam em `prompts/bjn/classificacao/*.md`. A aplicação mostra a natureza detectada e atualiza o formulário quando a resposta é um rótulo validado. Não inventa conteúdo em PDFs digitalizados. O backend repete a classificação ao salvar, registra mudanças no histórico e preserva triagem administrativa para `Pareceres em geral`. Erros de IA não impedem o atendimento humano.

**Correção do erro `demands.scss` (21,76 kB):** os estilos compartilhados passaram para o bundle global, retirados de `styleUrl` nos três componentes BJN. O limite Angular de **16 kB por componente** foi mantido, sem aumento artificial. Confira `docs/BJN_DEMANDAS_LOTE_PENDENCIAS_CLASSIFICACAO.md` para arquitetura, endpoints, testes, segurança e pendências de homologação.


## 30/10/2026 — Experiência renovada de Demandas e AI Ready

A página **BJN > Demandas** ganhou indicadores limitados aos resultados consultados, hierarquia visual mais clara, filtros avançados recolhíveis, tabela refinada e seleção em lote com limite exibido de 50 registros. No **AI Ready**, a entrada orienta a preparação dos documentos com seis objetivos de análise selecionáveis, checklist cível/trabalhista e perguntas preparatórias que não são enviadas automaticamente. Após a análise, um painel rápido usa dados efetivamente extraídos dos PDFs e permite exportar uma **pauta de revisão jurídica (.txt)**, distinta do dossiê geral.

As novas regras de apresentação estão em `frontend/src/demand-dashboard.scss` e `frontend/src/hub-home-dashboard.scss`, ambos globais para preservar o limite de estilos por componente. Ver `docs/UX_BJN_AI_READY_HUB_2026-10-30.md` para fluxos de uso, decisões, limites e checklist de homologação. **Validação neste pacote:** 82 testes Python e 44 testes estruturais de frontend aprovados; compilação Angular real e testes E2E de UI não executados neste ambiente.

## Quarta aplicação: Behavior e novas integrações

O Behavior integra o menu e a página inicial, com rota `/behavior` e API `/api/v3/laboratorio-comportamental`. Inclui agentes, cenários, eventos, repetições, conversas, métricas e visualização de interações. O modo demonstração utiliza exclusivamente dados sintéticos.

**Uma configuração corporativa:** copie `.env.example` para `.env` **na raiz** e ajuste uma só vez `BRADESCO_IDENTIFICADOR`, `BRADESCO_SENHA`, `BRADESCO_QA_WORKFLOW_CODE` e parâmetros da Bridge. Todas as aplicações leem o mesmo arquivo e importam o único `gpt_bradesco.py` da raiz. Reinicie a API após alterar `.env`. Não versionar segredos.

**Como incluir novos módulos:** utilize `python scripts/scaffold_application.py triagem --label "Triagem"` e consulte o tutorial completo [`docs/COMO_ADICIONAR_APLICACOES.md`](docs/COMO_ADICIONAR_APLICACOES.md). O registro de backend está em `applications/registry.py`; menu, home e aplicação ativa estão centralizados no frontend em `core/application-registry.ts`.

### Atualização do Behavior (16/11/2026)

Consulte [`docs/BEHAVIOR_CORRECAO_FEED_E_CONTROLE.md`](docs/BEHAVIOR_CORRECAO_FEED_E_CONTROLE.md) para os botões de pausar, retomar e resetar parâmetros, a correção das conversas e os testes de homologação.
