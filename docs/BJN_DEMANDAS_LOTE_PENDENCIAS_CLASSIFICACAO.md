# BJN — gestão de demandas, distribuição e classificação documental

Data: 2026-10-30. Responsável: equipe técnica. Status: implementação e regressão sintética concluídas; homologação corporativa e validação jurídica pendentes.

## Objetivo e escopo

A evolução preserva os módulos BJN (minutas), Auditoria e AI Ready. Na rota `/bjn/demandas`, estão disponíveis abas **Todas as demandas** e **Pendentes**, filtros adicionais e operação de distribuição em lote exclusiva do gestor. O cadastro BJN verifica a natureza de PDFs pesquisáveis com `text_generator` antes do envio e reconfirma o resultado no backend ao efetivar upload.

## Fluxo passo a passo

1. **Cadastro** (`demand-new.component.ts`): demandante conclui a triagem, seleciona natureza e PDFs. `verifyNature()` envia os primeiros quatro PDFs para `POST /api/v3/bjn/demandas/assistente/classificar-natureza`, recebendo `NatureClassification` com `status`, `selected_nature`, `detected_nature`, `changed` e `warnings`.
2. **Classificação** (`bjn_nature_classifier.py`): a API valida assinatura, tamanho e PDF pesquisável; extrai somente texto e lê cinco definições em `applications/bjn/prompts/classificacao/*.md`. Chama `bridge.generate_text` (que utiliza `text_generator` do `gpt_bradesco`). A resposta deve ser exatamente `Inventário`, `Alvará`, `Curatela`, `Procuração`, `Pareceres em geral` ou `INDETERMINADA`. Somente as cinco naturezas válidas são usadas para correção.
3. **Revisão antes do envio**: a interface informa natureza identificada, original e corrigida, e mantém aviso de revisão humana. A classificação é sempre apresentada como sujeita a erro; PDFs digitalizados sem texto extraível ficam como revisão manual.
4. **Persistência** (`bjn_demands.py`, `bjn_demand_store.py`): no upload definitivo, a API reclassifica os mesmos PDFs associados à demanda. Quando houver correção permitida, atualiza a natureza e grava evento `NATUREZA_CORRIGIDA_IA`, incluindo versão do prompt (hash). Em `Pareceres em geral`, direciona para triagem administrativa. Após distribuição para advogado, a natureza não pode ser modificada automaticamente: exige revisão humana.
5. **Consulta e pendências**: `POST /api/v3/bjn/demandas/consulta` usa `pending_only`, `lawyer`, `from_date`, `to_date` e filtros anteriores. A API aplica restrição por perfil **antes** dos filtros e executa a busca de datas de forma inclusiva. Pendentes excluem situações terminais (concluída, cancelada, resolvida por IA e encaminhada a outra área). Para advogado, inclui apenas demandas atribuídas a sua identidade autenticada; para gestor, inclui todas as pendentes.
6. **Distribuição em lote**: o gestor seleciona até 50 demandas elegíveis e escolhe advogado da lista autorizada. O frontend envia `PATCH /api/v3/bjn/demandas/atribuicao/lote` com `{"demand_ids":["..."],"lawyer_email":"..."}`. O backend verifica perfil, advogado e **todas** as demandas antes de executar os updates numa transação SQLite, registra `DISTRIBUICAO_LOTE` em cada demanda e responde `{"assigned_count":N,"demand_ids":[...],"lawyer_email":"..."}`. Uma demanda inválida cancela o lote todo.

## Configuração de nomes de advogados

O diretório de nomes não deve ser inferido de e-mails. Configure no arquivo de configuração privado gerenciado pela equipe:

```json
{
  "bjn_allowed_lawyers": ["advogado.ficticio@example.invalid"],
  "bjn_lawyer_names": {
    "advogado.ficticio@example.invalid": "Advogado Exemplo"
  }
}
```

Somente nomes mapeados para advogados permitidos são expostos na lista do gestor. Sem mapeamento, o filtro funciona pelo e-mail; para busca nominal real, o diretório corporativo deve fornecer o nome autorizado. A autenticação do usuário segue dependente do gateway e não das opções de tela.

## Limites e decisões

- **SCSS:** `demands.scss` é carregado uma única vez em `frontend/angular.json`. Os componentes de cadastro, lista e detalhe deixam de compilar esse arquivo individualmente. O orçamento de `anyComponentStyle` continua em **16 kB**; não foi elevado. A validação do build final requer `npm run build` com o registry npm aprovado.
- **Não classificar por heurística:** o modelo pode responder algo inválido, ambíguo ou contraditório. Nesse caso a aplicação preserva a natureza escolhida, mostra alerta e solicita conferência.
- **Não executar OCR oculto:** PDFs escaneados ou bloqueados não são inferidos. Solicite versão pesquisável ou revisão humana.
- **Preservar fontes:** a correção registrada após upload é vinculada a PDF salvo, com hash SHA-256, e usa versão do prompt. O modelo não tem permissão de publicar parecer jurídico.
- **Não falhar o cadastro por IA:** indisponibilidade do `text_generator` não destrói a demanda; a natureza permanece sob responsabilidade do demandante. A API não simula uma classificação.
- **Menor privilégio:** seleção e visibilidade são validadas no backend. Headers de simulação de usuário estão restritos a ambiente `local`; gateways de produção devem controlar identidade de origem.
- **Concorrência:** a operação de lote usa transação única. Alterações concorrentes entre a prévia da IA e o cadastro são mitigadas pela reclassificação durante o upload; a decisão final ainda requer validação jurídica.
- **LGPD e governança:** prazo de retenção, bases legais, fluxo de dados com provedor corporativo, credenciais, trilhas de auditoria e política de revisão devem ser homologados por Jurídico, Compliance e DPO. Não usar PDFs de produção não anonimizados em testes.

## Teste e reprodutibilidade

Na raiz: `python -m pytest -q tests`. No frontend: `npm test`, `npm run setup`, `npm run doctor`, `npm run build`. `tests/test_bjn_bulk_and_classification.py` valida permissões, lote atômico, filtros, classificação com mock, PDFs sem texto e eventos. `frontend/tests/bjn-bulk-classification.test.cjs` valida o vínculo estrutural das telas e que o orçamento de estilos não foi elevado.

**Pendências de homologação:** compilação Angular real, credenciais do `text_generator`, precisão por natureza em base de validação anonimizada, inspeção de PDFs digitalizados e integração do cadastro de advogados. As classificações exemplificativas feitas nos testes são sintéticas; não representam métricas de acurácia.
