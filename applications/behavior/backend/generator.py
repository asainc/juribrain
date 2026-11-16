"""Criador assistido de cenários agnósticos para o laboratório.

A IA só propõe perfis fictícios; o contrato estrito valida cada campo antes
que o repositório grave o conjunto de agentes, ambiente e sociedade.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Protocol

from pydantic import Field, ValidationError

from applications.behavior.backend.contracts import AgentInput, EnvironmentInput
from backend.contracts.base import Contract
from backend.errors import ServiceError

PROMPT_PATH = Path(__file__).resolve().parents[3] / "prompts" / "behavioral_lab" / "scenario.system.md"


class ScenarioRequest(Contract):
    """Pergunta do usuário e orçamento explícito de perfis para criação assistida."""

    description: str = Field(min_length=30, max_length=1600)
    agent_count: int = Field(default=6, ge=2, le=10)


class ScenarioProposal(Contract):
    """Representação gerada que só é aceita após validar toda a estrutura."""

    agents: list[AgentInput] = Field(min_length=2, max_length=10)
    environment: EnvironmentInput
    society_name: str = Field(min_length=3, max_length=90)
    society_description: str = Field(default="Sociedade totalmente fictícia", max_length=400)


class TextBridge(Protocol):
    """Interface mínima necessária da Bridge; facilita mocks em testes."""

    def generate_text_with_metadata(self, prompt: str, *, max_tokens: int, temperature: float = 0.2): ...


class ScenarioGenerator:
    """Constrói um esboço estruturado, sem conceder à IA operações de escrita."""

    def __init__(self, bridge: TextBridge):
        self.bridge = bridge

    def propose(self, request: ScenarioRequest) -> ScenarioProposal:
        """Separa instrução de texto não confiável e rejeita respostas inválidas."""
        system_prompt = PROMPT_PATH.read_text(encoding="utf-8")
        data = json.dumps(request.model_dump(), ensure_ascii=False)
        response = self.bridge.generate_text_with_metadata(
            f"<system>\n{system_prompt}\n</system>\n"
            f"<scenario_description_untrusted>\n{data}\n</scenario_description_untrusted>\n"
            "Retorne somente o objeto JSON solicitado.",
            max_tokens=4500,
            temperature=0.35,
        )
        raw = response.text.strip()
        if raw.startswith("```"):
            raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw, flags=re.IGNORECASE)
        try:
            proposal = ScenarioProposal.model_validate(json.loads(raw))
        except (ValueError, TypeError, ValidationError) as exc:
            raise ServiceError("A IA não devolveu um cenário com a estrutura esperada. Ajuste a descrição e tente novamente.",
                               422, code="LAB_INVALID_GENERATED_SCENARIO") from exc
        if len(proposal.agents) != request.agent_count:
            raise ServiceError("A IA retornou quantidade de agentes diferente da solicitada. Gere novamente o cenário.",
                               422, code="LAB_INVALID_GENERATED_SCENARIO")
        # Eventos do modelo ficam dentro do limite das seis rodadas suportadas.
        # Os agentes jamais recebem identificadores de pessoas do mundo real.
        return proposal
