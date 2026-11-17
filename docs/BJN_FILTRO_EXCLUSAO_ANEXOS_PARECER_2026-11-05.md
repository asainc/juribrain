# BJN — Assunto da demanda, exclusão de escopo e anexos do parecer

**Registro técnico:** 2026-11-05  
**Responsável:** equipe técnica do projeto  
**Situação:** código e testes sintéticos concluídos; homologação Angular, jurídica e de segurança pendente.

## Escopo

As mudanças ficam restritas ao módulo BJN de demandas. O fluxo de contratos, Auditoria de Pagamentos e Hub de Inteligência Processual não foi alterado.

### Filtro por assunto / natureza

Na página `/bjn/demandas`, o campo **Assunto / natureza** aparece junto à pesquisa e ao filtro de status. Os valores são carregados de `GET /api/v3/bjn/demandas/configuracao` (`available_natures`): **Inventário, Alvará, Curatela, Procuração e Pareceres em geral**.

A interface envia `nature` em `POST /api/v3/bjn/demandas/consulta`. O backend valida estritamente o valor contra `NATURES` e adiciona `service_nature = ?` na consulta SQL parametrizada. O filtro pode ser combinado com datas, advogado, status e demais campos existentes. As restrições de visibilidade por perfil permanecem ativas. Um valor fora do catálogo retorna HTTP 422. O filtro por natureza não envia identificadores pessoais na URL.

### Exclusão de demandas fora do escopo

Ação disponível **somente para gestor** e apenas enquanto o protocolo **não foi distribuído**, com status `RECEBIDA`, `EM_TRIAGEM` ou `TRIAGEM_ADMINISTRATIVA`. Na lista de distribuição, uma ação **Excluir** aparece ao lado de **Abrir** nas demandas elegíveis. A mesma ação existe no detalhe da demanda. Antes de confirmar, é obrigatório informar uma justificativa com 10 a 300 caracteres.

Endpoint: `POST /api/v3/bjn/demandas/{id}/exclusao-escopo`, corpo `{ "reason": "A competência pertence a outra unidade jurídica." }`.

**Decisão de arquitetura:** exclusão **lógica**, não física. O status torna-se `EXCLUIDA_ESCOPO`; o evento `EXCLUSAO_ESCOPO` registra o usuário, a data e a justificativa; o protocolo, o histórico e os documentos permanecem íntegros. A demanda aparece na aba **Todas as demandas** com o filtro **Todos os status**, bem como no filtro explícito **Excluída — fora do escopo** e por sua URL autenticada; continua fora da aba **Pendentes** e das distribuições em lote. A ação não pode ser desfeita pela interface. Exclusões posteriores à distribuição são bloqueadas (HTTP 409), evitando interferência em pareceres em andamento. A operação exige política corporativa de retenção e regras para eventual reabertura, a serem definidas pelo jurídico e compliance.

### Documento complementar do parecer

Na seção **Elaboração e validação do parecer**, o advogado responsável pode selecionar arquivos **PDF, PNG ou JPEG** de no máximo **15 MB por arquivo**. O limite total da demanda, somando todos os documentos, permanece **20 arquivos**. A publicação exige pelo menos 40 caracteres e marcação de revisão humana, como antes.

Endpoint novo: `POST /api/v3/bjn/demandas/{id}/parecer/publicar-com-anexos` com `multipart/form-data`:

- `final_text`: texto final do parecer jurídico.
- `human_review_confirmed`: `true`.
- `files`: zero ou mais anexos opcionais.

Para evitar publicações parciais, o backend valida o advogado responsável e a etapa de elaboração antes de gravar, analisa MIME, extensão e assinatura de cada arquivo, verifica o limite total, registra metadados na mesma transação da publicação e remove arquivos movidos se a transação falhar. Na conclusão, registra evento `PARECER_ANEXOS` com a quantidade e atribui a categoria `PARECER_COMPLEMENTAR`.

O endpoint anterior `POST .../parecer/publicar` com JSON permanece para compatibilidade e permite publicar sem anexos. Na tela de consulta, o parecer publicado possui a seção **Anexos do parecer**, que abre os arquivos na **Central de documentos** (aba **Parecer**). O solicitante, o advogado designado e o gestor acessam os documentos exclusivamente por `GET /api/v3/bjn/demandas/{id}/documentos/{document_id}/arquivo`, após a autorização por demanda. Não se publica link direto ao disco ou URL permanente.

**Observação de segurança:** a checagem de assinatura/MIME não substitui verificação antimalware, criptografia do volume, auditoria corporativa, antivírus e política de retenção. Essas medidas são exigências de implantação para documentos reais e precisam ser validadas por Segurança da Informação e DPO. A IA não modifica o conteúdo dos anexos do parecer.

## Arquivos / responsabilidades

| Arquivo | Entrada principal | Saída |
|---|---|---|
| `applications/bjn/backend/services/bjn_demand_store.py` | Natureza, exclusão, documentos e ator autenticado | SQL parametrizado, trilha de eventos, metadados e arquivos privados |
| `applications/bjn/backend/routers/bjn_demands.py` | Requisições HTTP validadas | Respostas de consulta, exclusão e publicação multipart |
| `frontend/src/app/core/bjn-demand-api.service.ts` | Filtros e arquivos selecionados | Requisições tipadas |
| `frontend/src/app/bjn/demands/demand-list.component.ts` | Natureza e justificativa | Lista filtrada e exclusão explicitamente confirmada |
| `frontend/src/app/bjn/demands/demand-detail.component.ts` | Parecer, anexos e ação de gestão | Publicação revisada e consulta por documento |
| `frontend/src/app/bjn/demands/demand-ui.ts` | Status | Textos visíveis para usuário |
| `frontend/src/app/bjn/demands/demands.scss`, `frontend/src/demand-dashboard.scss` | Padrões de interface | Estilos globais (sem elevar o orçamento SCSS Angular) |
| `tests/test_bjn_nature_exclusion_opinion_attachments.py` | Protocolo/PDF sintéticos | Testes de integração e isolamento |
| `frontend/tests/bjn-nature-exclusion-attachments.test.cjs` | Código-fonte | Testes estáticos de contratos e interface |

## Regressão executada

- `python -m pytest tests -q` — executar com dependências Python fixadas.
- `cd frontend && npm test` — testes estáticos de front sem Angular instalado.
- `cd frontend && npm run doctor && npm run build` — **homologar no ambiente com pacotes Angular instalados**.

### Roteiro manual de homologação

1. Gestor abre demandas, escolhe **Inventário** em **Assunto / natureza** e verifica que somente protocolos dessa natureza são retornados.
2. Gestor seleciona demanda não distribuída na listagem, escolhe **Excluir**, informa motivo e confirma. Verifica permanência na lista ao escolher Todos os status, ausência em Pendentes, busca por status de exclusão e evento no histórico.
3. Tenta excluir uma demanda já atribuída: o servidor deve retornar HTTP 409 sem alterar o protocolo.
4. Advogado designado entra em **Elaboração e validação do parecer**, informa texto final, anexa um PDF sintético, marca revisão humana e publica.
5. Solicitante autorizado abre a demanda concluída, lê o parecer e seleciona **Anexos do parecer**; o documento deve ser aberto na Central.
6. Um terceiro usuário não autorizado tenta abrir o documento: deve receber HTTP 404.
7. Tenta publicar um PDF com assinatura inválida: a publicação deve falhar e o status continuar em análise.
8. Verifica que BJN Contratos, Auditoria e Hub Processual continuam operacionais, e que o frontend não ultrapassa o limite de SCSS por componente.

## Restrições e decisões pendentes

- **Retenção e exclusão**: a exclusão é lógica justamente para não destruir evidências de auditoria; critérios de descarte definitivo e reabertura exigem validação Jurídico, Compliance e DPO.
- **Anexos**: armazenamento SQLite + diretório local é voltado a desenvolvimento/instância única. Para produção, exigir antivírus, controle de tamanho no proxy, backup, controle de acesso à mídia, criptografia em repouso, volume persistente e política de retenção corporativa.
- **Status de testes**: os testes automatizados não comprovam compilação Angular real, renderização ou integração com o gateway corporativo. Aceite produtivo depende de ambiente homologado.
