# BJN Demandas — Filtros alinhados e seletores pesquisáveis

Data: 2026-11-12. Escopo: interface de cadastro e consulta de demandas do BJN. Responsável pela homologação: equipe mantenedora de BJN.

## Objetivo e comportamento

- O filtro avançado de **Agência** não mostra mais o texto auxiliar longo. O campo permanece pesquisável por qualquer parte do código ou nome e continua utilizando o catálogo retornado pela API.
- Os filtros principais e avançados seguem grades responsivas com alturas e espaçamentos consistentes. Em telas menores, os campos são reordenados sem reduzir a legibilidade.
- **Departamento consultado** e **Solicitante** (unidade solicitante no cadastro) utilizam um seletor pesquisável comum. A pessoa pode abrir a lista ou digitar um código/nome e selecionar uma opção correspondente ao arquivo CSV. Como a validação do backend é restrita aos departamentos cadastrados, nenhum texto parcial é aceito como departamento definitivo.
- **Agência** no cadastro e no filtro também utiliza a lista pesquisável, mas permite digitação livre. Isso mantém compatibilidade com demandas anteriores e com o arquivo corporativo de agências ainda não preenchido. Quando existem opções, selecionar uma delas preenche o nome e código completos.
- A busca ignora diferenças de maiúsculas/minúsculas e acentuação: buscar `juridico` localiza `4040 - Jurídico`. A pesquisa por número também funciona.
- A escolha funciona por clique, setas para cima/baixo e Enter; Esc fecha a lista. A lista limita a renderização às primeiras 40 opções e solicita digitação para refinar quando houver mais registros.

## Arquitetura e decisões

- Novo componente reutilizável: `frontend/src/app/bjn/demands/searchable-select.component.ts`.
- Integração com cadastro: `demand-new.component.ts`.
- Integração com filtro e remoção do texto: `demand-list.component.ts`.
- Estilos globais: `demands.scss` e `frontend/src/demand-dashboard.scss`. A separação evita aumentar o estilo de componente acima do limite do Angular.
- O componente usa os dados `department_options` e `agency_options` já fornecidos por `GET /api/v3/bjn/demandas/configuracao`; **não altera** serviços, schemas, tabelas ou regras do backend.
- Os arquivos CSV e suas validações permanecem conforme `docs/BJN_CADASTROS_DEPARTAMENTOS_AGENCIAS_PARECER_AUTOMATICO.md`. Não foram adicionados departamentos ou agências reais.
- O campo **Usuário solicitante** no filtro continua pesquisando usuário por nome/e-mail; é diferente do seletor de **Solicitante** (unidade departamental) do cadastro, e foi identificado assim para evitar ambiguidade.

## Testes e verificação

- Executar `npm test` dentro de `frontend`: cobre pesquisa com acentos/códigos, seleção, ações por teclado, filtros e integridade da integração.
- Executar `python -m pytest -q tests/test_bjn_directories_2026.py tests/test_bjn_demands.py` na raiz: garante que catálogos e demandas permanecem disponíveis.
- Em um ambiente com dependências Angular instaladas, executar `npm run build` e testar manualmente os três seletores no cadastro e agência nos filtros em resoluções desktop e mobile.
- Testar tabulação, leituras por tecnologias assistivas, abertura/fechamento e escolha com teclado e mouse.
- Carregar CSVs corporativos válidos e inválidos para conferir validações; a responsabilidade pelos registros e políticas de acesso é da equipe proprietária dos dados.

## Limitações

Sem o Angular instalado, os testes de estrutura/lógica não substituem compilação de templates e testes de interação real no navegador. O fluxo de 4040 - Jurídico e a regra de revisão humana do parecer não foram alterados.
