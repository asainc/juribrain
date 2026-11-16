# Behavior — mapa editável, estados, duração e IA corporativa

**Data:** 16/11/2026  
**Escopo:** somente Behavior e a interface compartilhada de geração de texto (`backend/services/bradesco_bridge.py`).  
**Responsável pela homologação:** a definir pela equipe mantenedora; a alteração não constitui homologação em produção.

## 1. Correção identificada na IA corporativa

A implementação anterior de `LabSimulator._bridge_reaction()` passava `temperature=` para `BradescoBridgeClient.generate_text_with_metadata()`, mas a assinatura **real** do adaptador não declarava esse parâmetro. A chamada gerava `TypeError` antes de invocar `gpt_bradesco.text_generator()`. Os stubs antigos dos testes aceitavam temperatura, o que escondia essa divergência de contrato.

**Correção:** a fachada compartilhada passa a aceitar `temperature: float | None = None`, valida a faixa de 0 a 2 e transmite o valor como parâmetro de `text_generator`, sem modificar a temperatura global dos outros módulos quando o argumento é omitido. Não foram duplicadas credenciais, clientes corporativos ou arquivos `.env`.

O mecanismo Behavior utiliza **geração de texto** (`BRADESCO_TEXT_MODEL`), não o código do workflow Q&A (`BRADESCO_QA_WORKFLOW_CODE`), que continua destinado às perguntas e respostas. Ter parâmetros preenchidos no `.env` **não comprova** que o deployment esteja autorizado ou acessível: possíveis erros 400/401/403/404/429, rede e TLS passam a receber diagnósticos públicos específicos.

## 2. Arrastar agentes no mapa

1. Acesse **Behavior → Observatory** e selecione uma sociedade ou uma simulação dessa sociedade.
2. Arraste um nó com mouse ou toque para a posição desejada. Para acessibilidade, selecione o nó com Tab e mova com as setas (Shift + seta move 20 unidades).
3. As posições são salvas automaticamente como coordenadas proporcionais ao `viewBox` SVG de 900×435; a distribuição se adapta a telas pequenas e grandes sem alterar a rede ou as reações do motor.
4. Use **Reorganizar mapa** para apagar somente a preferência visual daquela sociedade e recuperar a disposição automática.

**Decisão:** o layout fica em `localStorage`, separado por sociedade e por navegador (`behavior:network-layout:v1:<society_id>`). Não é um campo de domínio da simulação; portanto, não é enviado à IA, não muda as métricas, não interfere em replays e não exige migração de API. O layout não é sincronizado entre navegadores ou usuários. O armazenamento guarda apenas os IDs sintéticos e coordenadas, e opera em memória quando o navegador bloqueia persistência. O mapa permanece responsivo pelo `viewBox` e conversão do `getScreenCTM()`.

## 3. Estados e tempos da simulação

O observatório e a aba de resultados distinguem explicitamente:

| Estado | Significado exibido |
| --- | --- |
| Na fila | Aguardando worker, sem processamento iniciado |
| Executando | Reações concluídas / totais e cronômetro atualizado |
| Pausa solicitada | Aguarda o checkpoint após a chamada em curso |
| Pausada | Suspensão confirmada e cronômetro parado |
| Concluída | Todas as reações concluídas, horário de término registrado |
| Falhou | Motivo seguro, etapa técnica e código da falha |
| Cancelada | Cancelamento solicitado pelo operador |
| Interrompida | Reinício do processo interrompeu a execução |

Os campos adicionados, com **migração SQLite aditiva/idempotente**, são `started_at`, `finished_at`, `paused_at`, `paused_seconds` e `failure_stage`. A API devolve `elapsed_seconds` e `error_reason` calculados sem inspecionar respostas sensíveis. O cálculo desconta somente as pausas **confirmadas**, e não o tempo em fila. O cronômetro frontend usa a resposta do backend como fonte de verdade e atualiza entre consultas. As conversas mostram o horário de registro dos eventos. Para execuções antigas anteriores à migração, o tempo pode ser desconhecido e não é inventado.

Códigos corporativos possuem explicações estáveis em `applications/behavior/backend/diagnostics.py`. Nunca se devolve a mensagem original da exceção corporativa, que poderia incluir detalhes confidenciais. Cada falha mantém `run_id`, `error_code`, `failure_stage`; logs estruturados também não contêm prompt nem credencial. Saídas de IA inválidas não são convertidas em resultados fictícios.

## 4. Arquivos modificados

| Arquivo | Alteração |
| --- | --- |
| `frontend/src/app/behavioral-lab/behavioral-lab-page.component.ts` | Drag/touch/teclado, persistência proporcional, estado e cronômetro |
| `frontend/src/app/behavioral-lab/behavioral-lab-page.component.html` | Controles do mapa, diagnóstico e horários |
| `frontend/src/app/behavioral-lab/behavioral-lab-api.service.ts` | Contrato com tempos e motivo da falha |
| `frontend/src/behavioral-lab.scss` | Feedback visual, responsividade e acessibilidade |
| `backend/services/bradesco_bridge.py` | Correção real da assinatura `temperature` |
| `applications/behavior/backend/diagnostics.py` | Catálogo de explicações públicas permitidas |
| `applications/behavior/backend/repository.py` | Duração auditável e migração da base SQLite |
| `applications/behavior/backend/simulator.py` | Classificação da etapa/código de erro |
| `tests/test_behavior_bridge_adapter_diagnostics.py` | Regressão da chamada do adaptador central com mock |
| `tests/test_behavior_timing.py` | Duração e exclusão de pausas |
| `frontend/tests/behavioral-lab.test.cjs` | Verificações adicionais do mapa e status |

## 5. Como executar e validar no ambiente corporativo

1. Extraia o **ZIP completo**. Preserve a pasta `.runtime` da instalação anterior antes de substituir arquivos, se houver históricos locais. Os bancos e chaves privadas locais **não** são distribuídos no ZIP novo.
2. Copie `.env.example` para `.env` **na raiz**, se ainda não existir. Configure `BRADESCO_IDENTIFICADOR`, `BRADESCO_SENHA`, `BRADESCO_TEXT_MODEL`, `BRADESCO_QA_WORKFLOW_CODE` (usado pelo chatbot), ambiente e CA quando aplicável. Não coloque credenciais no repositório, prints, testes ou logs.
3. Reinicie o backend para aplicar a configuração. Não existem `.env` nem cópias de `gpt_bradesco.py` específicos do Behavior.
4. Execute `python -m pytest -q` na raiz. Na pasta `frontend`, execute `npm test` e, **no ambiente com dependências homologadas instaladas**, `npm run build`.
5. Na UI, teste **Demonstração** com perfis fictícios, reposicione nós, altere a largura da janela, recarregue e teste **Reorganizar mapa**.
6. No modo **IA corporativa**, comece com poucos agentes e poucas rodadas, revise o orçamento de chamadas e confirme autorização do deployment. Se falhar, examine estado, **etapa**, **código** e **ID** da execução; compare com o log técnico correspondente. Não compartilhe token, prompt com dados reais nem resposta bruta do gateway.
7. Teste suspensão/retomada e verifique que a duração não cresce durante a pausa confirmada. Compare o horário de término ao da execução concluída.

## 6. Evidências e limitações

- Os testes locais usam somente simulações e clientes corporativos **fictícios / mockados**. Testes automatizados não representam aceitação por usuários do banco.
- Acesso real à Bridge, permissões do deployment, certificado/proxy do host e geração com diferentes modelos continuam **pendentes de homologação corporativa**.
- O build Angular e a interação visual em navegador real dependem de componentes Angular instalados. Verificações estáticas não substituem essa validação.
- Não há garantia de validade estatística dos comportamentos sintéticos; qualquer utilização no processo jurídico requer avaliação humana e controles de governança já previstos no projeto.
