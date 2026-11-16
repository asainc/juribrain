## 2026-11-16 — Behavior: auditabilidade, sociedades, mundos e Checagem Externa

- Incluída `decision_trace` (versão 1) nos eventos de reação para explicar mudança ou estabilidade de opinião, distinguindo componentes numéricos de regras demonstrativas de justificativas declaradas pela IA corporativa.
- Auditoria didática por reação no feed e no inspetor de agente, com expansão, evidências de rede/contexto e histórico exportável em JSON, CSV e Markdown.
- Criada aba própria de Sociedades para criação, edição de participantes, inclusão, retirada e cadastro de novo integrante. Bloqueada exclusão de agente ainda vinculado; snapshots e revisões preservados.
- Campo livre `world_type` para cenários de qualquer domínio; modelos de exemplo seguem opcionais e antigos cadastros mantêm compatibilidade.
- Catálogo persistente de tipos de entidade (GET/POST/DELETE), proteção de tipos nativos e em uso, validação de payloads e tela para novo tipo.
- Reprojetada a Checagem Externa para o padrão do ecossistema, preservando caráter descritivo, revisão humana e uso exclusivo de referências agregadas.
- Removidas classes/atributos duplicados herdados dos contratos Behavior, sem mudança das regras do motor.
- Testes: 134 backend, 77 verificações estáticas frontend. Build Angular, teste visual e Bridge real pendentes.
- Documentação: `docs/BEHAVIOR_AUDITORIA_SOCIEDADES_MUNDOS_2026-11-16.md`.

## 2026-11-16 — Behavior: mapa livre, tempo e diagnóstico da IA corporativa

- Coordenadas editáveis por arraste com mouse/toque e por teclado, normalizadas no SVG para responsividade; posição por sociedade salva localmente no navegador e botão para reorganizar.
- Painel de execução com estados distintos, timestamps, cronômetro efetivo sem pausas confirmadas e justificativas de falha sanitizadas com etapa/código da execução.
- Corrigida incompatibilidade real na assinatura de `BradescoBridgeClient.generate_text_with_metadata(temperature=...)`, mantendo comportamento anterior de outros módulos.
- Migração SQLite aditiva de timestamps de execução; biblioteca de diagnósticos sem dados sensíveis e testes de integração com fachada corporativa mockada.
- Validação corporativa real da Bridge e compilação Angular completa pendentes. Referência: `docs/BEHAVIOR_MAPA_STATUS_BRIDGE_2026-11-16.md`.

## 2026-11-16 — Behavior: correção do feed e controle da execução

- Corrigida a compressão vertical no painel "Conversas & acontecimentos": cartões preservam altura natural, com quebra de linhas e rolagem interna independente.
- Adicionados pausa/retomada reais por checkpoints persistidos no SQLite (`PAUSE_REQUESTED` e `PAUSED`), com endpoints HTTP e cancelamento compatível.
- Incluído botão para resetar apenas os parâmetros editáveis de simulação aos padrões, sem apagar configurações corporativas, cadastros ou histórico.
- Migração idempotente da coluna `pause_requested`, interrupção segura de execução pausada em reinícios e novos testes de concorrência.
- Validação: 126 testes backend e 71 verificações de frontend; compilação Angular e teste live da Bridge seguem pendentes de homologação.
- Instruções, limitações e passo a passo: `docs/BEHAVIOR_CORRECAO_FEED_E_CONTROLE.md`.

- Primeiro ZIP preservado como base, inclusive correções recentes de BJN.
- Behavior 3 integrado em `applications/behavior/backend`, com frontend em `/behavior`, ciclo de vida próprio e API sob `/api/v3/laboratorio-comportamental`.
- Criados registros explícitos (`applications/registry.py` e `core/application-registry.ts`), teste de contrato e utilitário de criação de módulos.
- Único `.env` e `gpt_bradesco.py` na raiz; removidas cópias dos produtos Auditoria e Chatbot.
- Adicionado tutorial de extensão e modelo de decisões arquiteturais.
- Pendências de validação: ambiente Bridge corporativo real, políticas de acesso e homologação jurídico/compliance; responsável técnico a definir pela equipe mantenedora.

## 2026-11-16 — Behavior como quarta aplicação e configuração corporativa única

## 2026-11-16 — BJN: catálogo de departamentos e seleção pesquisável

- Identificado que o CSV distribuído contém somente `4040 - Jurídico`; inclusão de unidades continua administrativa e não é feita por texto livre.
- Ajustada seleção por clique/teclado para evitar dupla confirmação e permitir reabrir as opções ao clicar no campo.
- Adicionado botão **Atualizar lista** em Departamento consultado e Solicitante, com contador de opções disponíveis e indicação explícita de falha de carregamento.
- Criado `scripts/manage_bjn_departments.py` para listar/incluir unidades com validação de código de quatro dígitos, detecção de duplicidade e gravação atômica.
- Preservada a restrição de roteamento ao `4040 - Jurídico`; novas unidades podem ser **Solicitante**, mas exigem fluxo aprovado para serem destinos atendidos.
- Documentados os passos e testes em `docs/BJN_ATUALIZACAO_DEPARTAMENTOS_E_SELETORES.md`.
- Responsável técnico: manutenção do ecossistema; integração com catálogos reais e homologação do browser pendentes.

## 2026-11-16 — BJN: diagnóstico e recuperação do cadastro HTTP 5xx

- Corrigido risco de retorno HTTP 500 após criação confirmada quando etapas auxiliares de IA falham inesperadamente.
- Falhas na classificação e na sugestão documental passam a gerar aviso de revisão, preservando o protocolo e os anexos cadastrados.
- Erros de banco ocupado, banco indisponível e diretório de upload sem escrita retornam códigos estruturados e mensagens públicas seguras.
- Registro de estágio da requisição e identificador para correlação com logs sem dados documentais, SQL ou credenciais.
- Criado diagnóstico local somente de metadados e documentação de triagem. Causa original no ambiente do usuário ainda requer correlação com o log correspondente.
- Responsável técnico: manutenção do ecossistema; homologação do ambiente de execução pendente.

## 2026-11-12 — BJN: seletores pesquisáveis e alinhamento dos filtros

- Retirado o texto explicativo do campo de agência no filtro avançado.
- Criado seletor pesquisável compartilhado para departamento consultado, Solicitante e Agência no cadastro; agência na consulta utiliza a mesma experiência.
- Incluída pesquisa por código/nome sem sensibilidade a acentos, seleção por teclado/mouse e lista limitada para catálogos grandes.
- Reorganizada a grade responsiva dos filtros, sem alterar APIs, regras de permissão ou cadastros corporativos.
- Adicionados testes automatizados e roteiro de homologação em `docs/BJN_FILTROS_SELETORES_PESQUISAVEIS_2026-11-12.md`.

## 2026-11-13 — BJN Demandas: catálogos e parecer automático

- Novo seletor inicial de departamento consultado, com roteamento do 4040 ao fluxo jurídico existente.
- Campo Solicitante passa a ser preenchido por CSV de departamentos.
- Filtro de agência com pesquisa parcial e sugestões de CSV com número e nome.
- Rascunho de parecer preparado automaticamente ao abrir a demanda como advogado responsável, sem publicação automática e sem sobrescrever rascunho anterior.
- Migração aditiva, testes e manual de operação/homologação.

## 30/10/2026 — Correção de instalação Angular

- Adicionado `npm run setup` para instalar Angular com dependências de desenvolvimento e fallback **somente** para o defeito `edgesOut` do npm 10.
- Adicionado `npm run doctor` e pré-verificação de `@angular/build` antes de iniciar a aplicação.
- Atualizadas faixas permitidas de Node.js/npm conforme compatibilidade do Angular 21; mantido o baseline conservador dos scripts corporativos de lockfile.
- Documentação de instalação, diagnósticos e decisão arquitetural ADR-006.
- Adicionados seis testes de regressão da instalação, incluindo simulação sem acesso à rede.
- Nenhuma modificação nas regras financeiras, lógica processual ou identidade visual.

# Changelog

## 1.0.0 — 2026-10-29

- Criada página inicial para o ecossistema jurídico, com cartões de acesso a BJN, Auditoria de Pagamentos e Chatbot / AI Ready.
- Reunidas três aplicações em um único Angular e host FastAPI, preservando fluxos e a identidade visual.
- Versões de API isoladas sob `/api/v3`, `/services/auditoria/api/v2` e `/services/chatbot/api/v3`.
- Copiados componentes completos, serviços, prompts e motor `judicial_calc` dos projetos de origem; ajustes de namespace necessários para execução conjunta.
- Adicionada configuração de frontend para três APIs, com proxy único e tratamento de navegação entre módulos.
- Documentadas arquitetura, instalação, decisões, limitações e checagens de segurança.
- Criados testes de infraestrutura, configuração e links da página inicial.

Os históricos de origem do BJN e do chatbot permanecem em suas documentações de referência. O projeto não registra como homologada nenhuma alteração de regra de negócio.

## 2026-10-29 — Hub de inteligência processual cível e trabalhista

- Expansão da tela Chatbot/AI Ready com abas de panorama, cronologia, agenda, evidências, biblioteca e perguntas documentais.
- Área processual selecionável, orientações operacionais específicas, pesquisa com página de origem e exportação textual voluntária.
- Novos contratos de agenda/evidência, busca lexical e perguntas contextualizadas; referência inválida descartada.
- Manutenção do Q&A corporativo independente e do BJN/Auditoria sem alterações funcionais.
- Testes sintéticos específicos da integração e documentação de limites jurídicos e de privacidade.
- Responsável: equipe técnica do projeto; implantação e aceite jurídico pendentes.

## 2026-10-30 — Demandas BJN e correção do orçamento Angular

- Corrigido excesso de 16 kB de estilo por componente sem elevar orçamento: SCSS compartilhado incluído no pacote global.
- Distribuição em lote (até 50 demandas), uma transação e eventos por demanda, somente gestor.
- Aba Pendentes por perfil: gestor visualiza todas as pendentes; advogado, apenas as atribuídas a si.
- Filtros de responsável por nome/e-mail cadastrado e período inclusivo de datas de cadastro.
- Classificação de PDFs com `text_generator` e cinco prompts Markdown; atualização de natureza no cadastro e no backend, com trilha auditável.
- Criados testes de autorização, atomicidade, limites e PDFs sintéticos; validação jurídica e testes corporativos ainda pendentes.
- Responsável: equipe técnica do projeto; aceite jurídico/compliance/DPO pendente.

## 2026-10-30 — Refinamento visual BJN e entrada orientada do AI Ready

- Painel BJN com cartões de indicadores dos resultados consultados, filtros avançados recolhíveis, tabela aprimorada, estados de carregamento e seleção limitada a 50 demandas.
- Nova página inicial contextual do AI Ready: seis objetivos, checklist por área, perguntas orientadoras e instruções de validação, sem métricas/processos fictícios.
- Painel pós-análise com atalhos baseados nos retornos existentes da API e exportação local de pauta de revisão.
- Criados estilos SCSS globais sem elevar budget `anyComponentStyle` e testes estruturais específicos.
- Preservadas APIs BJN/Chatbot/Auditoria, autenticação, gerador corporativo e lógica dos cálculos.
- Validações executadas: 82 testes Python e 44 testes frontend; testes E2E visuais e compilação Angular pendentes em ambiente com npm instalado.
- Responsável: equipe técnica do projeto; homologação Jurídico/Compliance/DPO pendente.

## 2026-11-05 — BJN: filtro por natureza, exclusão de escopo e complementos do parecer

- Filtro por natureza com catálogo existente, consulta parametrizada e restrições de perfil preservadas.
- Exclusão lógica de demanda antes da distribuição, apenas por gestor, exigindo justificativa de 10 a 300 caracteres e evento auditável.
- Exclusões lógicas preservam consulta pelo status explícito e pelo detalhe autenticado, mantendo histórico auditável.
- Publicação de parecer com anexos opcionais na mesma transação, categoria `PARECER_COMPLEMENTAR` e visualização na Central de documentos.
- Mantida a compatibilidade do endpoint JSON anterior de publicação.
- Adicionados testes integrados com PDFs sintéticos e teste estrutural da interface.
- Decisão técnica, limitações e homologação descritas em `docs/BJN_FILTRO_EXCLUSAO_ANEXOS_PARECER_2026-11-05.md`.
- Responsável: equipe técnica do projeto; validação jurídica, de segurança e de frontend Angular em ambiente homologado pendente.

## 2026-11-05 — BJN: visibilidade das demandas excluídas em Todos os status

- A consulta sem status específico agora retorna também `EXCLUIDA_ESCOPO`, com a mesma restrição de acesso por perfil.
- A aba **Pendentes** continua omitindo demandas excluídas, mesmo quando o status excluído for enviado à API.
- O filtro **Todos os status** explicita que inclui excluídas; a confirmação de exclusão explica essa regra.
- O indicador **Sem advogado designado** desconsidera demandas já excluídas, que não estão disponíveis para distribuição.
- Casos de regressão adicionados para GET/POST, filtro vazio, escopo do solicitante e exclusão das pendências.
- Justificativa: permitir acompanhamento e auditoria sem reativar demandas encerradas administrativamente.
- Responsável: equipe técnica do projeto; compilação Angular e homologação jurídica permanecem pendentes.

## 2026-11-05 — BJN: rótulo simplificado do filtro de status

- O seletor de status apresenta apenas **Todos os status**, sem texto adicional.
- O valor enviado à API permanece vazio quando selecionado, preservando a inclusão de demandas excluídas e as restrições de perfil já aplicadas.
- O comportamento da aba **Pendentes** permanece inalterado.
- Teste de regressão atualizado para exigir o rótulo exato.
