"""Ponto de acoplamento do Behavior: configura recursos e o ciclo de vida.

O registro do módulo injeta dependências da plataforma, sem duplicar credenciais
ou inicializar uma API FastAPI isolada só para expor o Behavior.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI

from applications.behavior.backend.experiments import ExperimentOrchestrator
from applications.behavior.backend.repository import LabRepository
from applications.behavior.backend.router import router
from applications.behavior.backend.simulator import LabSimulator
from backend.config import Settings
from backend.services.bradesco_bridge import BradescoBridgeClient


class BehaviorModule:
    """Mantém persistência, motor e workers do Behavior sob um único dono."""

    key = "behavior"
    router = router

    def __init__(self, settings: Settings, bridge: BradescoBridgeClient):
        """Prepara a infraestrutura sem misturá-la com outras aplicações."""
        self.repository = LabRepository(settings.behavioral_lab_database_path)
        self.simulator = LabSimulator(self.repository, bridge)
        self.executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="behavior")

    def attach(self, app: FastAPI) -> None:
        """Expõe dependências ao roteador via estado da instância FastAPI."""
        app.state.behavioral_lab_repository = self.repository
        app.state.behavioral_lab_simulator = self.simulator
        app.state.behavioral_lab_executor = self.executor

    @asynccontextmanager
    async def lifespan(self) -> AsyncIterator[None]:
        """Retoma somente tarefas pendentes e encerra o pool sem perder resultados."""
        try:
            for run_id in self.repository.queued_run_ids():
                self.executor.submit(self.simulator.execute, run_id)
            orchestrator = ExperimentOrchestrator(self.repository, self.simulator)
            for experiment_id in self.repository.queued_experiment_ids():
                self.executor.submit(orchestrator.execute, experiment_id)
            yield
        finally:
            # Evita cancelar à força chamadas corporativas iniciadas.
            self.executor.shutdown(wait=False, cancel_futures=True)
