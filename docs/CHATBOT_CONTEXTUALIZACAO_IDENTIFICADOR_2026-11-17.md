# Chatbot — identificador de referência contextual (17/11/2026)

## Objetivo

Permitir que uma pergunta geral digitada no chat corporativo seja complementada, no momento do envio, por um identificador selecionado pelo usuário. Não altera a API nem o histórico de perguntas documentais dos PDFs.

## Passo a passo

1. Abra **Chatbot** (`/chatbot`) e clique no botão flutuante **AI**.
2. Na parte inferior da janela, acima da pergunta, selecione **GCPJ**, **Número CNJ** ou **Número ConectaJur**.
3. Informe o **Valor do identificador** (até 80 caracteres). É opcional. O mesmo valor permanece preenchido durante a conversa até ser editado ou a sessão ser encerrada.
4. Escreva a pergunta e clique em **Enviar** ou pressione Enter. Shift+Enter insere uma quebra de linha na pergunta.
5. A mensagem exibida no chat continua sendo a pergunta que você escreveu, com a etiqueta **Referência enviada** para mostrar qual identificador foi usado. A API recebe a pergunta complementada.

### Exemplo

| Campo | Valor sintético |
| --- | --- |
| Tipo | GCPJ |
| Valor | `12345` |
| Pergunta digitada | `faça um resumo da petição inicial` |
| Texto encaminhado à API | `faça um resumo da petição inicial do gcpj 12345` |

Outros exemplos:

- **Número CNJ** `0000000-00.2026.8.26.0000` + `Resuma a inicial.` envia `Resuma a inicial do número cnj 0000000-00.2026.8.26.0000.`
- **Número ConectaJur** `ABC/2026-7` + `Qual é o assunto?` envia `Qual é o assunto do número conectajur ABC/2026-7?`
- **Valor vazio** envia apenas a pergunta original, sem nenhum complemento.

Os valores são ilustrativos e não fazem referência a processos reais.

## Comportamento visual

O histórico das mensagens (`.chat-body`) é a **única região que rola**. O cabeçalho e o compositor com o seletor, valor e mensagem permanecem fixos dentro da janela, inclusive em telas menores. A altura máxima passou de 620 px para 710 px no desktop e 690 px em telas de até 760 px, sempre limitada pela altura disponível do viewport (`dvh`). A largura usa limite responsivo.

## Decisões técnicas e justificativas

| Decisão | Justificativa |
| --- | --- |
| Complementação no frontend por `buildContextualChatPrompt` | A API Q&A existente já recebe o campo `pergunta`. Não é preciso alterar contratos, endpoints, credenciais ou outros módulos. |
| Tipos definidos em `frontend/src/app/chatbot/core/chat-context.ts` | Evita lógica de concatenação dispersa e facilita adicionar novas opções posteriormente. |
| Contexto opcional | Não interrompe perguntas gerais quando o usuário não tem um número em mãos. |
| Manter o texto original no histórico com uma etiqueta separada | Permite ao usuário ver o que digitou e qual identificador efetivamente acompanhou a requisição. |
| Capturar tipo e valor antes do envio assíncrono | Evita associar uma referência alterada posteriormente à pergunta anterior. |
| Limitar valor a 80 caracteres e proibir controles, espaços internos e símbolos não usuais | Evita complementos acidentais e introdução de linhas de instrução na referência; o formato oficial de cada identificador deve ser confirmado pelos responsáveis dos sistemas de origem. |
| Respeitar 8.000 caracteres para a pergunta final | Garante compatibilidade com `ChatRequest.pergunta` no backend, mesmo após acrescentar o identificador. |
| Limpar referência em `Encerrar sessão` | Reduz o risco de reutilizar acidentalmente identificador de um atendimento anterior. |

A referência acrescentada é **texto para a IA**. Este recurso **não consulta automaticamente** bases GCPJ, CNJ ou ConectaJur, nem verifica existência/permissão de acesso ao processo. A interpretação e a capacidade de resposta dependem do workflow Q&A corporativo configurado; homologação do time responsável é necessária. Os dados de identificação inseridos são enviados ao serviço corporativo quando o usuário submete uma pergunta.

## Componentes alterados

- `frontend/src/app/chatbot/chatbot-page.component.ts`: controles, visualização da referência e montagem de mensagem na submissão.
- `frontend/src/app/chatbot/core/chat-context.ts`: função pura com lista de opções, sanitização, pontuação e limite de comprimento.
- `frontend/src/workspace-layout.scss`: altura ampliada, cabeçalho/compositor estáveis e rolagem na área do histórico.
- `frontend/tests/chatbot-context.test.cjs`: testes de composição, validação, integração estrutural e sintaxe TypeScript.

## Verificações realizadas

- `cd frontend && npm test`: **84 testes aprovados**, incluindo sete testes novos.
- `python -m pytest -q`: **137 testes aprovados**, sem alteração de contratos ou lógica backend.
- O teste do prompt é executado sobre o próprio módulo TypeScript transpilado durante o teste; não depende da instalação do Angular.

**Pendências de homologação:** build Angular completo (as bibliotecas Angular não estão instaladas no ambiente), inspeção visual no navegador em desktop e mobile, conexão real com a Bridge e validação dos formatos de identificador aceitos pelos sistemas de origem.

Responsável técnico/aceite: a definir pela equipe mantenedora. Validação de segurança, privacidade e uso de identificadores reais: jurídico/compliance/DPO e donos dos sistemas, quando aplicável.
