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
