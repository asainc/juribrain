# Behavior — correção de conversas, pausa/retomada e reset de parâmetros

**Atualização:** 16/11/2026  
**Escopo:** apenas módulo Behavior da aplicação principal. Os demais produtos, o `.env` único e a integração compartilhada `gpt_bradesco.py` foram preservados.

## 1. O que foi corrigido em Conversas & acontecimentos

O feed apresentava uma coluna Flexbox com muitos eventos e permitia que cada cartão encolhesse. Ao reduzir a altura, o texto podia ultrapassar o espaço do cartão e ficar por cima dos registros vizinhos. A correção em `frontend/src/behavioral-lab.scss`:

- estabelece `flex: 0 0 auto` para cada mensagem e acontecimento;
- aplica rolagem vertical somente à lista de eventos (`overflow-y: auto`, `min-height: 0`);
- permite que mensagens, metadados e descrições extensas quebrem linhas (`overflow-wrap: anywhere` / `white-space: pre-wrap`);
- separa a área de inspeção da lista rolável e preserva a exibição em larguras reduzidas.

Isso é uma correção de layout; não modifica nem resume o texto dos eventos persistidos. Os filtros **Tudo**, **Conversas**, **Ambiente** e **Somente agente selecionado** foram mantidos.

## 2. Pausar e retomar a simulação

A mesa de controle e o mapa de interações apresentam **Pausar experimento** enquanto uma execução está na fila ou em andamento. Ao pedir pausa, o backend registra `PAUSE_REQUESTED`. Assim que a rotina chega a um ponto seguro, passa a `PAUSED`. O mesmo botão vira **Retomar experimento**.

Endpoints da aplicação (prefixo completo `/api/v3/laboratorio-comportamental`):

| Método | Rota | Finalidade |
|---|---|---|
| POST | `/simulacoes/{run_id}/pausar` | Solicitar pausa cooperativa |
| POST | `/simulacoes/{run_id}/retomar` | Desbloquear a simulação pausada |
| POST | `/simulacoes/{run_id}/cancelar` | Cancelar inclusive se estiver pausada |
| GET | `/simulacoes/{run_id}` | Acompanhar `status`, `pause_requested`, progresso e eventos |

O mecanismo está no SQLite do Behavior (`applications/behavior/backend/repository.py`) e é verificado pelo simulador (`applications/behavior/backend/simulator.py`) antes da primeira reação, de cada repetição e rodada, e antes/depois da geração de uma reação. Dessa forma, a execução não é recriada na retomada: semente, memória, contexto, configurações congeladas e eventos existentes permanecem os mesmos.

**Limitações importantes:** uma chamada remota de IA já em andamento não pode ser interrompida pelo botão. A pausa só se torna efetiva no próximo checkpoint e é por isso que existe o estado `PAUSE_REQUESTED`. Workers pausados continuam ocupando um dos dois slots do executor até retomada/cancelamento; não deixe muitos experimentos pausados simultaneamente. Se a API for reiniciada, execuções pausadas são marcadas `INTERRUPTED` — não são retomáveis após o reinício, pois o estado de execução em memória foi perdido. Para continuar nesse caso é necessário executar novamente a configuração. Este controle é aplicável às **simulações individuais do Studio**; a orquestração de variantes da aba Intelligence não ganhou um botão global de pausa nesta atualização.

## 3. Resetar configurações

O botão **Resetar configurações de simulação**, junto a Executar, restaura os valores padrão do formulário de execução e os filtros/seleções temporárias do feed após confirmação. Também seleciona o primeiro cenário e a primeira sociedade já cadastrados (quando existirem), preferindo o modo demo somente quando permitido no ambiente.

**Não apaga** perfis sintéticos, ambientes, sociedades, execuções, eventos, resultados, calibrações ou dados salvos. Não cancela uma simulação em andamento. Um experimento ativo continua consultável; seus parâmetros estão congelados no snapshot persistido e são independentes dos valores editáveis da tela. Não toca no `.env`, em credenciais nem em configuração de outros módulos.

## 4. Compatibilidade e auditoria

- A coluna `pause_requested` é adicionada por migração idempotente ao banco SQLite já existente. Os dados anteriores não são descartados.
- A contagem de execuções ativas e o stream de eventos consideram os estados `PAUSE_REQUESTED` e `PAUSED`.
- O estado `PAUSED` só é publicado quando o worker alcança um checkpoint seguro.
- Transições inválidas de pausa ou retomada respondem HTTP 409 com erro explícito.
- Registros sintéticos permanecem acessíveis via exportações existentes (JSON e CSV); nenhuma credencial ou prompt é exposto nos novos endpoints.

## 5. Testar após atualizar

1. Inicie o backend e frontend conforme o `README.md`, com o `.env` único na raiz.
2. Abra **Behavior > Observatory**, execute uma simulação fictícia com várias rodadas e observe que mensagens longas não se sobrepõem. Teste os três filtros e a rolagem.
3. Durante a execução, clique **Pausar experimento**, aguarde o estado **Pausada** e confirme que o contador de reações se estabiliza.
4. Clique **Retomar experimento** e confirme que o mesmo `run_id` prossegue, sem apagar eventos anteriores.
5. Execute novamente e cancele enquanto estiver pausada; confirme o status **Cancelada**.
6. Altere sliders e campos, clique **Resetar configurações de simulação**, confirme e verifique os padrões; os perfis, ambientes e histórico deverão permanecer.
7. Valide BJN, Auditoria e Chatbot em homologação para afastar regressões de integração.

### Evidências automatizadas nesta entrega

- `python -m pytest -q tests`: **126 testes aprovados** (inclui pausa/retomada/cancelamento, migração de banco e comportamento após reinício).
- `NODE_PATH=$(npm root -g) node --test frontend/tests/*.test.cjs`: **71 testes estruturais aprovados**, incluindo verificações de CSS e da ligação com endpoints. O uso de `NODE_PATH` serviu para usar TypeScript e PostCSS globais disponíveis no ambiente de teste, não substitui `npm ci`.
- A compilação Angular completa e a inspeção visual E2E em um navegador com Angular **não foram realizadas**, porque as dependências do frontend não estavam instaladas neste ambiente.
- A Bridge corporativa não foi chamada; o teste de pausa durante a geração usou o motor demonstrativo com reação artificialmente bloqueada, sem dados reais.
