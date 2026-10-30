"""Rotas do workspace processual AI Ready."""
from __future__ import annotations

from fastapi import APIRouter, File, Form, Query, Request, UploadFile

from applications.chatbot.backend.contracts import AiReadyConfiguration, ChatRequest, ChatResponse, ProcessWorkspaceResponse, DocketSearchResponse, DocketQuestionRequest, DocketAnswer

router = APIRouter(prefix="/ai-ready", tags=["AI Ready"])


def _service(request: Request):
    return request.app.state.process_intelligence


def _chat_service(request: Request):
    return request.app.state.chat_service


@router.get("/configuracao", response_model=AiReadyConfiguration)
def configuration(request: Request) -> AiReadyConfiguration:
    """Informa limites da interface sem expor segredos ou endpoints corporativos."""
    settings = request.app.state.settings
    return AiReadyConfiguration(
        geracao_texto_configurada=request.app.state.bridge.configured,
        chat_qa_configurado=request.app.state.bridge.qa_configured,
        limite_arquivos=settings.max_upload_files,
        limite_mb_por_arquivo=settings.max_upload_bytes // (1024 * 1024),
        limite_total_mb=settings.max_total_upload_bytes // (1024 * 1024),
    )


@router.post("/analisar", response_model=ProcessWorkspaceResponse)
async def analyze(request: Request, files: list[UploadFile] = File(...), tipo_processo: str = Form("civel")) -> ProcessWorkspaceResponse:
    """Cria um workspace temporário a partir de PDFs de um processo cível."""
    return await _service(request).analyze_uploads(files, tipo_processo=tipo_processo)


@router.post("/chat", response_model=ChatResponse)
def chat(body: ChatRequest, request: Request) -> ChatResponse:
    """Encaminha ao agente corporativo a pergunta digitada no chatbot."""
    return _chat_service(request).ask(body.pergunta)


@router.delete("/{workspace_id}", status_code=204)
def discard(workspace_id: str, request: Request) -> None:
    """Permite remover imediatamente o contexto documental mantido em memória."""
    _service(request).discard(workspace_id)


@router.get("/{workspace_id}/buscar", response_model=DocketSearchResponse)
def search_documents(
    workspace_id: str, request: Request, q: str = Query(min_length=2, max_length=1600)
) -> DocketSearchResponse:
    """Busca auditável em páginas textuais do workspace temporário."""
    return _service(request).search(workspace_id, q)


@router.post("/perguntar-autos", response_model=DocketAnswer)
def ask_documents(body: DocketQuestionRequest, request: Request) -> DocketAnswer:
    """Responde com contexto textual restrito a páginas recuperadas dos PDFs."""
    return _service(request).ask_documents(body.workspace_id, body.pergunta)
