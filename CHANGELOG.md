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
