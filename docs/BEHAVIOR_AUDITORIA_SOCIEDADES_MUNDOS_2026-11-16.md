# Behavior — auditoria de decisões, sociedades, mundos livres e checagem externa

Data: 16/11/2026  |  Versão do esquema de auditoria por reação: `1`

## 1. O que mudou

Este módulo continua acessível em `/behavior`, dentro do ecossistema jurídico. As alterações não mudam o motor de regras da demonstração, o modelo corporativo selecionado ou a configuração centralizada do projeto. Também não modificam BJN, Auditoria de Pagamentos ou Chatbot.

**Auditabilidade da interação:** cada evento `REACTION` de uma execução **nova** inclui um objeto `decision_trace`. Na interface, abra **Observatory → Conversas & acontecimentos**, clique numa reação (ou num agente da rede) e use **Expandir auditoria**. A explicação mostra: posição anterior e atual, variação, se permaneceu ou mudou, mensagens recebidas e respectivos pesos, choques do ambiente, eventos programados e justificativa textual. No modo demonstrativo é possível expandir a composição da fórmula; no modo corporativo a justificativa é somente a **declaração do modelo**. Não se afirma causalidade nem fidelidade comportamental para pessoas reais.

**Sociedades:** a aba **Sociedades** permite criar um coletivo, selecionar integrantes existentes, retirar integrantes, abrir o editor de um perfil e criar um perfil já selecionado para a sociedade em edição. A nova composição **só é persistida ao clicar em Salvar sociedade**. Ao editar um perfil o retorno é ao cadastro de agentes; a vinculação existente permanece. O backend bloqueia a exclusão de um agente enquanto ele pertence a qualquer sociedade. Antes de excluir o perfil, retire-o das sociedades e salve as alterações. Cada edição da sociedade gera uma revisão consultável e nenhuma delas reescreve snapshots de simulações anteriores.

**Mundos:** **Mundos → Tipo de mundo (livre)** aceita rótulos como Saúde, Educação, Justiça, Finanças, Sustentabilidade ou qualquer outro contexto ficcional. Os três modelos rápidos são **exemplos opcionais**, não os únicos tipos possíveis. O atributo `world_type` é opcional em chamadas API antigas e recebe `Personalizado` por padrão; a edição de cadastros antigos continua possível.

**Tipos de entidade:** no editor de agentes, abra **Cadastrar novo tipo de entidade**, informe nome e, opcionalmente, identificador. O sistema normaliza o identificador para letras maiúsculas e underscores; o backend valida `^[A-Z][A-Z0-9_]*$` (2 a 48 caracteres). Tipos ficam persistidos no SQLite e são compartilhados pelo editor e importação CSV. Identificadores são imutáveis. Tipos personalizados podem ser excluídos **somente se nenhum agente os estiver usando**; os sete tipos nativos não podem ser excluídos.

**Checagem Externa:** o formulário foi reorganizado com separação entre resumo da simulação, valores de referência, fonte/revisor, botão e histórico de comparações. O número apresentado como desvio absoluto é apenas a diferença entre duas médias registradas; **não é validação estatística**. Insira somente indicadores agregados de fonte autorizada, nunca dados individuais de produção. Avalie previamente a necessidade de revisão por Jurídico, Compliance ou DPO.

## 2. Exemplo de trilha registrada

Uma reação sintética pode apresentar:

```json
{
  "schema_version": 1,
  "previous_stance": 50,
  "current_stance": 55,
  "delta": 5,
  "changed": true,
  "first_round": false,
  "peer_signals": [
    {"agent_id": "id-ficticio", "name": "Perfil fictício", "stance": 80, "weight": 0.7, "influence": 0.5}
  ],
  "scheduled_changes": [],
  "shock": null,
  "source": "REGRAS_DEMO",
  "reason": "Justificativa ilustrativa do motor de demonstração.",
  "calculation": {
    "components": {"influencia_social": 5.0, "variacao_aleatoria": 0.0, "variante": 0.0,
                   "eventos_programados": 0.0, "choque_aleatorio": 0.0},
    "raw_stance": 55.0,
    "rounding_or_clipping": 0.0
  },
  "interpretation": "Componentes numéricos calculados por regras ilustrativas, sem validação empírica."
}
```

> Este exemplo demonstra apenas a **estrutura**. Os números não são resultado de um experimento medido. Os dados reais de cada simulação permanecem em seu próprio registro de execução.

### Semântica dos campos

| Campo | Significado e limite de interpretação |
|---|---|
| `previous_stance`, `current_stance`, `delta` | Valores observados na simulação; `delta` é a diferença aritmética, não uma probabilidade. |
| `peer_signals` | Somente sinais efetivamente fornecidos como contexto à reação, com posição, peso do vínculo e influência registrada. |
| `scheduled_changes`, `shock` | Eventos de ambiente presentes naquele passo; não identificam necessariamente sua contribuição individual no modo IA. |
| `source=REGRAS_DEMO` | `calculation.components` detalha efeitos numéricos da **fórmula simulada**. A soma pode requerer arredondamento e truncamento 0–100. |
| `source=JUSTIFICATIVA_IA` | `reason` é um texto devolvido pelo modelo; `calculation` é `null`. Não representa SHAP, explicação causal nem prova de consideração dos fatores. |
| `schema_version` | Versão do payload de explicabilidade para interpretação futura de exportações. |

### Exportações e legados

- `/simulacoes/{id}` e o arquivo **Exportar JSON** mantêm a trilha dentro do evento `REACTION`.
- **Exportar CSV** acrescenta `posicao_anterior`, `variacao` e `trilha_decisao_json`; colunas anteriores continuam no mesmo arquivo, com novas colunas adicionadas.
- **Relatório Markdown** agora contém a seção **Decisões por interação**, com a mudança e a justificativa declarada.
- **Simulações anteriores** não têm `decision_trace`. A aplicação mantém o histórico e mostra a justificativa antiga quando presente; jamais inventa explicações retroativas.
- O identificador do motor `behavior-3.0` foi preservado porque a **fórmula não mudou**. A mudança adiciona uma camada de registro auditável versionada separadamente.

## 3. Rotas novas e compatibilidade

| Método | Rota relativa à API Behavior | Finalidade |
|---|---|---|
| GET | `/tipos-entidade` | Listar catálogo nativo + personalizado |
| POST | `/tipos-entidade` | Criar categoria com `value` e `label` |
| DELETE | `/tipos-entidade/{value}` | Excluir categoria sem referências e não nativa |

A API original de sociedades (`GET/POST/PUT/DELETE /sociedades`) continua a mesma. `world_type` é um campo aditivo no contrato de ambientes. Os contratos da Bridge e o `.env` único não foram alterados. As versões e revisões ficam no banco SQLite existente.

## 4. Testes e homologação

### Verificação automatizada executada

- Backend: `pytest -q` — **134 testes aprovados** em ambiente isolado com mocks da IA; abrange dados sintéticos, CRUD, trilha por interação, CSV, markdown e preservação de snapshots.
- Frontend: `NODE_PATH=... node --test tests/*.test.cjs` — **77 verificações aprovadas** de estruturas, sintaxe TypeScript, estilos e contratos. São verificações estáticas, **não equivalem a build Angular**.

### Ainda exige homologação

1. Instalar Angular via registry corporativo aprovado; executar `npm run doctor` e `npm run build`.
2. Abrir o Behavior com tela larga e estreita; testar rolagem, expandir/recolher auditabilidade e Checagem Externa com teclado e mouse.
3. Criar duas sociedades e mover um perfil entre elas; confirmar erro ao excluir um perfil ainda vinculado e conferir revisões.
4. Criar um mundo inteiramente novo, executar demonstração e verificar registro JSON/CSV/replay.
5. Executar cenário pequeno com Bridge real autorizada e validar se sua resposta estruturada contém justificativa utilizável; nenhuma credencial deve aparecer em logs ou tela.
6. Validar com Jurídico, Compliance e DPO o procedimento de uso de referências agregadas e quaisquer grupos com risco de vieses.

## 5. Decisões técnicas

- **Trilha append-only no evento de reação:** mantém os vínculos com o histórico de rodada e a sequência; não cria tabelas adicionais por evento. Limitada às mensagens e fatores observáveis, sem coletar prompt completo ou credenciais.
- **Cálculo só no motor demo:** separa decomposição exata de regra ilustrativa da justificativa narrativa de IA. Atribuição causal futura exigiria experimento e abordagem de explicabilidade validados.
- **Catálogo em SQLite:** mudanças podem ser compartilhadas entre usuários, mas não exigem reiniciar o servidor. Tipos nativos são inicializados de forma idempotente.
- **Bloqueio referencial na exclusão:** evita sociedades inválidas e preserva snapshots históricos sem exclusão em cascata.
- **`world_type` opcional na API:** evita migração de registros históricos e permite novos temas sem modificar listas de presets.
- **Revisão de Checagem Externa restrita ao frontend:** nenhum método estatístico foi inventado nem mudou a semântica da referência agregada.

Responsável pela homologação e validação externa: a ser definido pela equipe mantenedora.
