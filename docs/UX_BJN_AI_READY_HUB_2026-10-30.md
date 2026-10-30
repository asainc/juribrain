# Evolução da experiência do BJN e do AI Ready

**Data:** 30/10/2026  
**Responsável:** equipe técnica do projeto (registro técnico; responsável nominal a designar na homologação)  
**Escopo:** experiência do usuário e funcionalidades locais de preparação/análise; **sem alteração de contratos de API, autenticação, modelos de IA ou motor de cálculos**.

## 1. Objetivo

Reorganizar a tela de gestão de demandas do BJN, que apresentava navegação e filtros com baixo contraste de prioridade visual, e transformar a entrada do AI Ready em um espaço orientado a tarefas de inteligência processual. A interface preserva superfícies claras, tipografia e vermelho de destaque do ecossistema.

## 2. O que mudou no BJN (`/bjn/demandas`)

- **Cabeçalho e hierarquia:** título, descrição e ação primária visível; indicadores compactos antes da listagem.
- **Indicadores:** quantidade de demandas, não concluídas, sem advogado e em análise, **calculados exclusivamente a partir dos registros retornados pela consulta atual**. Não representam necessariamente a carteira completa; o rodapé reforça o escopo. Durante o primeiro carregamento exibem travessão, não zero artificial.
- **Abas:** “Todas as demandas” e “Pendentes”, com estilo consistente e identificação do perfil.
- **Filtros:** campo principal e status sempre visíveis; data inicial/final, advogado, agência, solicitante e CPF em painel expansível. O filtro CPF continua sendo enviado por POST, sem exposição como parâmetro de URL.
- **Distribuição em lote:** seleção por checkbox, painel com responsável e contador; limite de 50 registros por operação reforçado no frontend. O backend continua sendo a autoridade de permissão e atomicidade; o frontend não concede acessos.
- **Tabela:** melhor espaçamento e tipografia, iniciais de responsável quando disponível, chips de status, ações de acesso mais claras e rolagem horizontal em viewport estreita.
- **Estado de tela:** carregamento explícito, erro acionável, vazio explicativo e opção de limpar filtros. Consultas com datas invertidas não são enviadas.

**Importante:** os contadores não são indicadores gerenciais consolidados de toda a base. Somente uma API específica de agregações poderia produzir dados de toda a carteira, com filtros e escopo de permissão definidos.

## 3. O que mudou no AI Ready (`/chatbot`)

### Antes da análise

1. **Landing orientada:** explica como preparar uma análise com documentos reais, sem exibir dados fictícios.
2. **Seis objetivos selecionáveis:** visão geral, cronologia, agenda, evidências, biblioteca e perguntas. A escolha define a aba inicialmente aberta **após** o processamento dos PDFs; as demais continuam disponíveis.
3. **Checklist por área:** uma lista para cível e outra para trabalhista; marcação temporária somente no navegador, não enviada ao modelo. É orientação, não bloqueio de upload.
4. **Perguntas orientadoras:** sugestões específicas da área escolhida. Uma seleção preenche a pergunta **após** a análise e direciona à aba “Pergunte aos autos”; nenhuma consulta é enviada automaticamente.
5. **Acesso direto ao seletor:** “Selecionar documentos” abre o seletor de PDFs, respeitando validações existentes de extensão, quantidade e tamanho.
6. **Instruções de governança:** a entrada diferencia fontes, interpretação jurídica, prazos e acompanhamento oficial.

### Depois da análise

1. **Mapa rápido:** cartões clicáveis informam as quantidades extraídas pelo backend de eventos, eventos de agenda, provas/lacunas e documentos com alertas de extração. Os números são contagens dos registros retornados, não qualidade jurídica, confiabilidade do processo ou probabilidade de êxito.
2. **Pauta de revisão (.txt):** arquivo baixado localmente mediante clique, contendo documentos com alertas, agenda mencionada, pontos de atenção, evidências/lacunas e checklist de providências. Inclui referências a documentos e páginas quando disponíveis, e avisos de validação humana.
3. **Dossiê textual:** exportação existente preservada; compartilha auxiliar de download com a nova pauta para reduzir duplicidade.
4. **Sessão:** fechamento continua limpando interface, arquivos temporários locais e solicitando descarte do workspace remoto.

**Regras de proteção:** a página não consulta tribunais, não calcula prazos legais e não declara que uma menção a prazo é um vencimento oficial. A integração com o gerador corporativo é a existente e depende de configuração/autorização. Arquivos usados em homologação devem ser sintéticos ou anonimizados.

## 4. Decisões técnicas (ADR-UX-008)

| Decisão | Justificativa | Consequência |
| --- | --- | --- |
| Manter a lógica de gestão em `demand-list.component.ts` | Reutilizar contratos e a autorização existente; nenhuma permissão é resolvida no CSS | Operações seguem protegidas pela API |
| Criar `src/demand-dashboard.scss` e `src/hub-home-dashboard.scss` | Evitar repetir o erro de orçamento `anyComponentStyle` de 16 kB | Estilos incluídos no bundle global do Angular |
| Não criar endpoints para o painel visual | Contagens locais e checklists não justificam tráfego adicional | Indicadores restritos aos resultados consultados |
| Manter a entrada sem dados fictícios | Evitar transmitir falsa percepção de atividade/alertas na carteira | Landing apresenta roteiros até haver PDFs reais |
| Não executar automaticamente perguntas escolhidas | Exigir confirmação consciente do envio de contexto processual | A pergunta é preenchida e o advogado decide quando consultar |
| Exportar somente após ação do usuário | Evitar gravação/compartilhamento automático de material potencialmente sigiloso | Download no navegador; necessário orientar guarda institucional |

## 5. Arquivos modificados

- `frontend/src/app/bjn/demands/demand-list.component.ts`: novo painel BJN, filtros e tabela.
- `frontend/src/demand-dashboard.scss`: estilos do painel BJN.
- `frontend/src/app/chatbot/chatbot-page.component.ts`: landing AI Ready, seleção de objetivo, checklist, perguntas, indicadores e pauta.
- `frontend/src/hub-home-dashboard.scss`: estilos do novo hub.
- `frontend/angular.json`: inclusão dos dois SCSS globais (mantém orçamento de 16 kB).
- `frontend/tests/ui-processual-dashboard.test.cjs`: testes estruturais das novas experiências.
- `README.md`, `CHANGELOG.md`: atualização da documentação.

## 6. Fluxos de aceitação em homologação

**Gestor BJN:** abrir demandas, observar indicadores, aplicar filtros por período e advogado, selecionar 2 demandas elegíveis, distribuir a advogado autorizado, verificar na tabela e no histórico. Comparar quantidades exibidas com os resultados efetivamente retornados. Tentar selecionar mais de 50 e validar mensagem.

**Advogado BJN:** abrir Pendentes e confirmar que apenas demandas atribuídas ao seu usuário autenticado aparecem; garantir que o painel de distribuição não é exibido. Verificar, também por acesso direto à API, o bloqueio de demanda de outro advogado.

**AI Ready cível:** selecionar a área, completar parcialmente checklist, escolher uma pergunta, carregar PDF sintético pesquisável, analisar. Confirmar abertura de “Pergunte aos autos” com pergunta preenchida, mas **não enviada**. Confirmar fontes e download da pauta.

**AI Ready trabalhista:** mudar a área, confirmar checklist e perguntas específicas, escolher objetivo cronologia, analisar PDF sintético e verificar abertura correta da aba. Validar documentos com e sem alertas de qualidade, e que a pauta não inventa prazos.

**Responsividade:** Chrome corporativo em desktop, tela intermediária e celular; conferir ordem do foco, navegação por teclado, tabelas roláveis, seletor de PDFs e janela de chat.

## 7. Validação executada e pendências

- **Executados:** `python -m pytest -q tests` (**82 aprovados**) e `cd frontend && npm test` (**44 aprovados**). Os testes do frontend verificam estrutura, sintaxe TS e parsing dos novos SCSS; **não** são uma compilação Angular nem testes de navegador.
- **Pendente:** `npm run setup && npm run doctor && npm run build`, testes E2E visuais, validação de layout nos tamanhos e navegadores homologados, teste real do `text_generator` e autorização de segurança/privacidade/compliance.
- **Sem nova avaliação de modelo:** nenhuma métrica de acurácia jurídica, viés ou qualidade do LLM foi medida neste ciclo; validar separadamente antes de uso produtivo.

## 8. Execução

```powershell
cd frontend
npm run setup
npm run doctor
npm run build
npm start
```

Com o backend iniciado, acessar `/bjn/demandas` e `/chatbot`. As instruções para inicializar o backend e configurar credenciais estão no README principal. Nunca copiar arquivos de produção não anonimizados, chaves ou tokens para diretórios de teste.
