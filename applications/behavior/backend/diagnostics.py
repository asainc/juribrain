"""Catálogo público e sanitizado de diagnósticos de execução do Behavior."""
from __future__ import annotations

ERROR_REASONS: dict[str, str] = {
    "LAB_BRIDGE_UNAVAILABLE": "IA corporativa não configurada: revise o .env central e reinicie a API.",
    "bradesco_modulo_indisponivel": "O módulo gpt_bradesco.py não pôde ser carregado ou faltam dependências aprovadas.",
    "bradesco_modulo_incompativel": "A integração corporativa não expõe text_generator com o contrato esperado.",
    "bradesco_assinatura_incompativel": "A assinatura da função corporativa não é compatível com o adaptador.",
    "bradesco_requisicao_rejeitada": "O gateway rejeitou os parâmetros de geração (HTTP 400). Valide o deployment e o contrato da API.",
    "bradesco_credencial_invalida": "Autenticação recusada (HTTP 401). Valide identificador, senha ou token corporativo.",
    "bradesco_acesso_negado": "Acesso negado (HTTP 403). Confira a permissão para o modelo configurado.",
    "bradesco_recurso_indisponivel": "Serviço ou deployment indisponível (HTTP 404). Verifique ambiente, URL e modelo.",
    "bradesco_limite_requisicoes": "Limite de chamadas atingido (HTTP 429). Reduza a frequência ou tente novamente mais tarde.",
    "bradesco_tempo_esgotado": "A chamada de IA excedeu o tempo limite. Confira conectividade e BRADESCO_TIMEOUT_SECONDS.",
    "bradesco_falha_rede": "Falha de conexão com a Bridge. Confira rede, VPN, proxy e DNS.",
    "bradesco_certificado_invalido": "Falha no certificado TLS corporativo. Verifique a cadeia de confiança ou BRADESCO_CA_BUNDLE.",
    "bradesco_credencial_ausente": "Credenciais de IA não foram carregadas. Confira o .env central e reinicie a API.",
    "bradesco_token_nao_renovavel": "O token de IA expirou e não pôde ser renovado. Configure credenciais renováveis.",
    "bradesco_resposta_autenticacao_invalida": "O serviço de identidade não retornou token compatível.",
    "bradesco_resposta_incompativel": "A resposta do gateway difere do formato esperado pela integração.",
    "bradesco_saida_vazia": "O modelo não retornou texto para a reação solicitada.",
    "bradesco_indisponivel": "O serviço corporativo não concluiu a chamada. Consulte os logs técnicos sanitizados.",
    "bradesco_configuracao_invalida": "Os parâmetros de geração foram considerados inválidos pela integração.",
    "bradesco_temperatura_invalida": "A temperatura enviada está fora da faixa aceita (0 a 2).",
    "MODEL_OUTPUT_INVALID": "A IA retornou texto que não atende ao JSON/schema exigido. Verifique o modelo e aumente o limite de tokens por reação.",
    "LAB_METRIC_INVALID": "O modelo retornou uma métrica fora do tipo ou dos limites definidos no cenário.",
    "LAB_ACTION_INVALID": "O modelo propôs alteração de ambiente não autorizada pelo cenário.",
    "SERVER_RESTART": "O processo foi reiniciado antes da conclusão. Inicie uma nova simulação.",
    "LAB_EXECUTION_ERROR": "Uma falha interna interrompeu o experimento. Consulte o log técnico pelo identificador da execução.",
}


def describe_failure(code: str | None) -> str | None:
    """Retorna explicação segura sem divulgar conteúdo gerado ou credenciais."""
    return ERROR_REASONS.get(code or "", ERROR_REASONS["LAB_EXECUTION_ERROR"]) if code else None
