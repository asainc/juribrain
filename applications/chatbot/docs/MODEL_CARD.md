# Ficha técnica — AI Ready Processual

## Uso pretendido

Apoiar profissionais jurídicos na leitura e organização de documentos de processos cíveis. A aplicação resume conteúdo, estrutura informações, monta cronologia factual e responde perguntas usando o contexto fornecido pelo usuário.

## Modelo

O deployment é definido por `BRADESCO_TEXT_MODEL` e executado pela função `gpt_bradesco.text_generator`. O repositório não fixa o nome de um modelo corporativo específico porque essa informação depende do ambiente autorizado.

## Dados de entrada

PDFs enviados pelo usuário durante a sessão. O texto é extraído localmente com PyMuPDF. PDFs sem camada textual suficiente são rejeitados para evitar inferência a partir de conteúdo ausente.

## Limitações

- A IA pode omitir, interpretar incorretamente ou associar uma informação à página errada.
- A aplicação não substitui leitura dos autos nem validação jurídica.
- Imagens digitalizadas sem texto pesquisável não são automaticamente submetidas a OCR neste fluxo.
- O chatbot recebe apenas uma parcela dos trechos quando o conjunto excede o limite de contexto configurado; o resumo estruturado do workspace também é incluído para preservar informação consolidada.
- Métricas de acurácia não são declaradas neste documento porque precisam ser medidas em uma base de validação representativa e aprovada.

## Validação recomendada

Criar conjunto anonimizado/adequadamente autorizado de processos cíveis, definir campos esperados e medir precisão/recall por tipo de informação, além de taxa de citações corretas de documento/página. Qualquer uso com efeito decisório deve passar por validação adicional de Jurídico, Compliance e DPO quando aplicável.

## Ampliação para o hub processual — 2026-10-29

O uso pretendido inclui também processos **trabalhistas**. O modelo recebe a área declarada pelo usuário como contexto, mas não verifica a competência do processo. A saída foi ampliada para eventos de agenda **mencionados no texto**, provas e lacunas com referência a PDF e página, além de perguntas contextualizadas por busca lexical em até cinco páginas textuais recuperadas.

A validação da existência de arquivo/página é determinística. A correspondência entre a afirmação gerada e o conteúdo da página **não foi avaliada quantitativamente**. A busca não é pesquisa jurisprudencial, não consulta sistemas oficiais, não calcula prazos e não certifica intimações. A revisão humana é obrigatória.

Ensaios de regressão com documentos sintéticos constam em `tests/test_hub_inteligencia_processual.py`. Dados de validação autorizados, métricas por área processual, análise de vieses, responsável técnico, aprovação jurídica e baseline de drift permanecem pendentes para homologação. Nenhum indicador de desempenho foi inventado ou inferido dos testes unitários.
