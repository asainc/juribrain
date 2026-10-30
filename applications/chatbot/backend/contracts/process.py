"""Contratos HTTP da análise documental e do assistente processual."""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import Field

from applications.chatbot.backend.contracts.base import Contract


Confidence = Literal["alta", "media", "baixa"]
TimelineCategory = Literal[
    "ajuizamento",
    "citacao",
    "manifestacao",
    "prova",
    "audiencia",
    "decisao",
    "recurso",
    "cumprimento",
    "outro",
]


class Party(Contract):
    """Parte ou participante expressamente identificado nos documentos."""

    nome: str = Field(min_length=1, max_length=300)
    papel: str = Field(min_length=1, max_length=120)


class TimelineEvent(Contract):
    """Fato processual com referência documental rastreável."""

    data: str | None = Field(default=None, max_length=20)
    titulo: str = Field(min_length=1, max_length=220)
    descricao: str = Field(min_length=1, max_length=1400)
    categoria: TimelineCategory = "outro"
    documento: str = Field(min_length=1, max_length=260)
    pagina: int | None = Field(default=None, ge=1, le=100000)
    confianca: Confidence = "media"


class DocumentSummary(Contract):
    """Metadados técnicos do PDF, sem persistir o conteúdo textual na resposta."""

    identificador: str
    nome: str
    paginas: int = Field(ge=1)
    paginas_utilizaveis: int = Field(ge=0)
    tamanho_bytes: int = Field(ge=1)
    qualidade_textual: Literal["boa", "parcial", "insuficiente"]
    alertas: list[str] = Field(default_factory=list)


class ProcessOverview(Contract):
    """Síntese factual do processo extraída dos documentos enviados."""

    numero_processo: str | None = None
    classe_processual: str | None = None
    tribunal: str | None = None
    unidade_judicial: str | None = None
    fase_processual: str | None = None
    assunto_principal: str | None = None
    valor_causa: str | None = None
    ultima_data_relevante: str | None = None
    partes: list[Party] = Field(default_factory=list)
    resumo: str
    pedidos: list[str] = Field(default_factory=list)
    fatos_controvertidos: list[str] = Field(default_factory=list)
    pontos_atencao: list[str] = Field(default_factory=list)
    proximas_acoes_sugeridas: list[str] = Field(default_factory=list)


class EvidenceReference(Contract):
    """Referência verificada na camada textual do PDF, sem afirmação de validade jurídica."""

    documento: str = Field(min_length=1, max_length=260)
    pagina: int = Field(ge=1, le=100000)
    trecho: str = Field(default="", max_length=900)


class DocketAgendaItem(Contract):
    """Compromisso, comunicação ou prazo apenas mencionado nos documentos."""

    tipo: Literal["audiencia", "prazo_mencionado", "intimacao", "pericia", "outro"] = "outro"
    titulo: str = Field(min_length=1, max_length=240)
    data_mencionada: str | None = Field(default=None, max_length=80)
    descricao: str = Field(min_length=1, max_length=900)
    fonte: EvidenceReference
    status_verificacao: Literal["conferir_nos_autos"] = "conferir_nos_autos"


class DocketEvidenceItem(Contract):
    """Prova, divergência ou lacuna apontada como hipótese de conferência."""

    tipo: Literal["prova", "divergencia", "lacuna"]
    titulo: str = Field(min_length=1, max_length=240)
    descricao: str = Field(min_length=1, max_length=1000)
    fonte: EvidenceReference


class ProcessWorkspaceResponse(Contract):
    """Estado necessário para renderizar a tela principal do AI Ready."""

    workspace_id: str
    gerado_em: datetime
    processo: ProcessOverview
    linha_tempo: list[TimelineEvent]
    tipo_processo: Literal["civel", "trabalhista"] = "civel"
    agenda_documental: list[DocketAgendaItem] = Field(default_factory=list)
    provas_e_lacunas: list[DocketEvidenceItem] = Field(default_factory=list)
    documentos: list[DocumentSummary]
    aviso: str


class ChatRequest(Contract):
    """Pergunta digitada pelo usuário na janela do chatbot."""

    pergunta: str = Field(min_length=2, max_length=8000)


class ChatResponse(Contract):
    """Resposta devolvida pelo campo ``answer`` da API corporativa Q&A."""

    resposta: str
    aviso: str


class AiReadyConfiguration(Contract):
    """Disponibilidade funcional sem expor credenciais ou configuração sensível."""

    provedor: Literal["bradesco_iagen"] = "bradesco_iagen"
    geracao_texto_configurada: bool
    chat_qa_configurado: bool
    limite_arquivos: int
    limite_mb_por_arquivo: int
    limite_total_mb: int


class DocketSearchHit(Contract):
    """Trecho recuperado da página original; não foi gerado pela IA."""

    documento: str
    pagina: int = Field(ge=1)
    trecho: str = Field(max_length=900)
    pontuacao: int = Field(ge=1)


class DocketSearchResponse(Contract):
    """Resultados paginados logicamente em um máximo de oito ocorrências."""

    resultados: list[DocketSearchHit] = Field(default_factory=list)
    aviso: str = "Resultados textuais dos PDFs enviados; confira a página de origem."


class DocketQuestionRequest(Contract):
    """Pergunta contextualizada pelo workspace, não enviada ao Q&A genérico."""

    workspace_id: str = Field(min_length=32, max_length=32, pattern=r"^[a-f0-9]{32}$")
    pergunta: str = Field(min_length=3, max_length=1600)


class DocketAnswer(Contract):
    """Resposta contextual e trechos comprováveis oferecidos para conferência."""

    resposta: str
    fontes: list[DocketSearchHit] = Field(default_factory=list)
    aviso: str = "Resposta assistida por IA. Confirme as evidências nos PDFs antes de utilizá-la."
