# Hub de inteligência processual — arquitetura, decisões e limitações

Data: 2026-10-29. Escopo: módulo Chatbot / AI Ready (`/chatbot`), processos cíveis e trabalhistas.

## Objetivo

Ajudar o advogado a localizar informações e organizar uma revisão dos autos, sem apresentar eventos ou prazos como confirmados e sem automatizar decisão jurídica. Não altera lógica de BJN ou do motor de Auditoria de Pagamentos.

## Fluxo de dados

1. O usuário declara a área processual, seleciona PDFs e inicia a análise.
2. `ProcessIntelligenceService.analyze_uploads` valida quantidade, tamanho, assinatura PDF, nomes de arquivos e páginas disponíveis. Arquivos com nomes repetidos são rejeitados, evitando ambiguidade entre fontes.
3. `PdfTextExtractor` extrai texto de cada página localmente; PDFs sem camada utilizável são rejeitados.
4. O prompt `analise_trecho.md` extrai fatos por trecho. `consolidacao_processo.md` consolida resumo, linha do tempo, agenda e mapa de evidências, preservando a área declarada.
5. `_normalize_hub_items` só aceita fontes cujos **nomes e páginas existem** no conjunto enviado. Isso evita referências totalmente inexistentes, mas **não garante** que a afirmação do modelo esteja correta na página.
6. O resultado é mantido por TTL em `WorkspaceStore` em memória do processo. Não há histórico persistente nem índice externo.
7. A busca `search` usa normalização de acentos e correspondência lexical para identificar páginas; trechos são retirados do PDF original, sem geração. `ask_documents` recupera no máximo cinco páginas e solicita resposta ao gerador, com instrução de ancoragem. O modelo **pode não cumprir** essas instruções, exigindo revisão humana.
8. A interface oferece filtros, exportação local em `.txt` e botão de encerramento. O descarte do servidor é solicitado por HTTP; em falha de conexão, a interface avisa e o TTL ainda se aplica.

## Decisões técnicas (registro de arquitetura)

| Decisão | Justificativa | Trade-off ou risco residual |
| --- | --- | --- |
| Campos estruturados opcionais na resposta | Mantém compatibilidade com o contrato anterior e com modelos que omitem informação | Agenda ou mapa de provas podem vir vazios |
| Tipos `civel` / `trabalhista` selecionados pelo usuário | Dá contexto explícito ao modelo sem inferir competência jurídica | Seleção pode não corresponder ao documento; conferir |
| Não calcular prazos nem assinalar situação de vencimento | Evita interpretações normativas dependentes de rito, intimação, suspensão e calendário | Não substitui controle de prazos do tribunal |
| Mostrar só fontes com documento e página existentes | Reduz alucinação estrutural de referência | Ainda requer comparação com o trecho original |
| Pesquisa lexical simples e transparência das fontes | É explicável, determinística e não depende de serviço de embeddings | Pode falhar com sinônimos, OCR ruim e termos que não aparecem literalmente |
| IA generativa condicionada ao contexto recuperado | Evita responder com o chat Q&A geral sobre documentos não vinculados | Não elimina geração de conteúdo impreciso; recuperação limitada a cinco páginas |
| Workspaces temporários em memória e descarte explícito | Minimiza persistência de conteúdo e simplifica isolamento entre aplicações | Não é armazenamento distribuído; estado expira e não é compartilhado entre workers |
| Exportação textual local, com clique explícito | Permite conferência e compartilhamento controlado pelo usuário | Arquivo exportado pode conter conteúdo sigiloso; respeitar a política corporativa |

## Como testar

Pré-requisitos: Python e dependências do projeto instaladas conforme `docs/INSTALACAO.md`.

```bash
python -m pytest -q tests/test_hub_inteligencia_processual.py
python -m pytest -q tests
cd frontend
npm test
npm run build
```

Os testes do hub utilizam exclusivamente PDFs e respostas **sintéticos**. Em homologação, testar documentos anonimizados/autorizados de ambas as áreas, arquivos incompletos, páginas inválidas, timeout da IA, respostas sem fontes e expiração do workspace. Validar reconhecimento de entidades e citações por revisão humana.

## Ficha de validação pendente

- Modelo: deployment configurável por `BRADESCO_TEXT_MODEL`, via `gpt_bradesco.text_generator`.
- Treino: não realizado no projeto; depende do provedor corporativo.
- Conjunto de validação jurídico: **a definir e aprovar**.
- Precisão de extração de eventos, provas, agenda e fonte/página: **não medida**.
- Viés e robustez por área processual, tribunal, rito e tipo de documento: **não avaliados**.
- Responsável técnico, data de aprovação e critérios de aceite: **a designar**.
- Drift: acompanhar alteração no perfil de documentos e queda na acurácia validada em amostras humanas; critérios/limiares dependem de baseline medido.

Para produção, obter revisão dos times **Jurídico, Segurança, Compliance e DPO** sobre permissão de dados, bases legais, retenção, modelo corporativo, controle de acesso por usuário e política de exportação. Nada nesta documentação constitui interpretação legal ou automatiza estratégia processual.
