"""Módulo BJN acoplado à API do ecossistema.

A estrutura replica o contrato de extensão usado por Behavior. Nenhum serviço
BJN é inicializado pelo núcleo; configurações e Bridge são injetadas pelo host.
"""
from __future__ import annotations

import os
import secrets
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import APIRouter, FastAPI

from applications.bjn.backend.routers import bjn, bjn_demands
from applications.bjn.backend.services.bjn_demand_ai import BjnDemandAIService
from applications.bjn.backend.services.bjn_demand_store import DEMO_LAWYERS, DemandStore
from applications.bjn.backend.services.bjn_document_opinion import BjnDocumentOpinionService
from applications.bjn.backend.services.bjn_nature_classifier import BjnNatureClassifier
from applications.bjn.backend.services.bjn_opinion import OpinionAIService
from backend.config import Settings
from backend.services.bradesco_bridge import BradescoBridgeClient
from backend.services.chat_service import ChatService

router = APIRouter()
router.include_router(bjn.router)
router.include_router(bjn_demands.router)


def _document_signing_key(settings: Settings) -> str:
    """Protege identificadores do BJN; o segredo local nunca entra no ZIP."""
    key = settings.bjn_document_hash_key.get_secret_value()
    if key or settings.environment != 'local':
        return key
    private_path = settings.bjn_database_path.parent / '.bjn-cpf-local.key'
    private_path.parent.mkdir(parents=True, exist_ok=True)
    if not private_path.exists():
        try:
            fd = os.open(private_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(fd, 'w', encoding='ascii') as stream:
                stream.write(secrets.token_hex(32))
        except FileExistsError:
            pass
    return private_path.read_text(encoding='ascii').strip()


class BjnModule:
    """Isola serviços, rotas e persistência BJN sem alterar contratos HTTP."""

    key = 'bjn'
    router = router

    def __init__(self, settings: Settings, bridge: BradescoBridgeClient):
        """Recebe a única configuração corporativa e adaptador da plataforma."""
        self.settings = settings
        self.bridge = bridge

    def attach(self, app: FastAPI) -> None:
        """Disponibiliza serviços de domínio somente na inicialização do produto."""
        settings = self.settings
        app.state.bjn_chat_service = ChatService(settings, self.bridge)
        app.state.bjn_demand_ai = BjnDemandAIService(self.bridge)
        app.state.bjn_opinion_ai = OpinionAIService(self.bridge)
        app.state.bjn_document_opinion = BjnDocumentOpinionService(self.bridge)
        app.state.bjn_nature_classifier = BjnNatureClassifier(self.bridge)
        demo_lawyers = (
            list(DEMO_LAWYERS)
            if settings.environment == 'local' and settings.bjn_demo_lawyers_enabled
            else []
        )
        app.state.bjn_demo_lawyers = demo_lawyers
        app.state.bjn_demand_store = DemandStore(
            settings.bjn_database_path,
            settings.bjn_upload_directory,
            [*settings.bjn_allowed_lawyers, *demo_lawyers],
            document_key=_document_signing_key(settings),
            lawyer_names=settings.bjn_lawyer_names,
        )

    @asynccontextmanager
    async def lifespan(self) -> AsyncIterator[None]:
        """Reserva o ciclo de vida para recursos futuros sem novos mounts."""
        yield
