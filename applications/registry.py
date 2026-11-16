"""Registro explícito de aplicações, sem imports circulares no núcleo.

- Módulos montados preservam API, configuração e ciclo de vida próprios.
- Extensões de API recebem dependências do núcleo sem duplicar login/Bridge.
- Para nova aplicação, registrar sua fábrica em uma das duas funções abaixo.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Protocol
from contextlib import AbstractAsyncContextManager

from fastapi import APIRouter, FastAPI
from backend.config import Settings
from backend.services.bradesco_bridge import BradescoBridgeClient


@dataclass(frozen=True)
class MountedApplication:
    """Monta uma API de produto independente sob um endereço estável."""
    key: str
    mount_path: str
    factory: Callable[[], FastAPI]


class ApiExtension(Protocol):
    """Contrato mínimo para incluir novos módulos na API compartilhada."""
    key: str
    router: APIRouter

    def attach(self, app: FastAPI) -> None: ...
    def lifespan(self) -> AbstractAsyncContextManager[None]: ...


def mounted_applications() -> tuple[MountedApplication, ...]:
    """Centraliza os subprodutos isolados sem modificar seus roteadores."""
    from applications.auditoria.backend.principal import create_app as create_audit_app
    from applications.chatbot.backend.principal import create_app as create_chatbot_app
    return (
        MountedApplication("auditoria", "/services/auditoria", create_audit_app),
        MountedApplication("chatbot", "/services/chatbot", create_chatbot_app),
    )


def api_extensions(settings: Settings, bridge: BradescoBridgeClient) -> tuple[ApiExtension, ...]:
    """Registra produtos que usam o gateway e a versão de API do núcleo."""
    from applications.behavior.backend.module import BehaviorModule
    return (BehaviorModule(settings, bridge),)
