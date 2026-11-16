"""Contratos versionáveis e limites explícitos do Behavior.

Os agentes são perfis ficcionais. Cada linha da tabela equivale a um agente e
`characteristics` contém as colunas variáveis, sem schema rígido de domínio.
"""
from __future__ import annotations

from typing import Literal
import math
import re
from pydantic import Field, field_validator, model_validator
from backend.contracts.base import Contract


class AgentInput(Contract):
    """Perfil sintético com atributos extensíveis e parâmetros comportamentais."""

    name: str = Field(min_length=2, max_length=90)
    entity_type: str = Field(default="PESSOA", min_length=2, max_length=48, pattern=r"^[A-Z][A-Z0-9_]*$")
    group: str = Field(default="Geral", min_length=1, max_length=60)
    goal: str = Field(min_length=5, max_length=450)
    communication_style: str = Field(default="objetivo", min_length=2, max_length=120)
    initial_stance: int = Field(default=50, ge=0, le=100)
    influence: float = Field(default=0.5, ge=0, le=1)
    susceptibility: float = Field(default=0.5, ge=0, le=1)
    characteristics: dict[str, str] = Field(default_factory=dict)

    @field_validator("characteristics")
    @classmethod
    def validate_characteristics(cls, fields: dict[str, str]) -> dict[str, str]:
        """Impede payloads excessivos e tipos não previstos nas colunas dinâmicas."""
        if len(fields) > 24:
            raise ValueError("Até 24 características adicionais por agente.")
        for key, value in fields.items():
            if not isinstance(key, str) or not 1 <= len(key.strip()) <= 60:
                raise ValueError("O nome de cada característica deve ter de 1 a 60 caracteres.")
            if not isinstance(value, str) or len(value) > 500:
                raise ValueError("Cada característica deve ser um texto de até 500 caracteres.")
        return fields


class EntityTypeInput(Contract):
    """Tipo de entidade configurável; o identificador é estável nas revisões."""

    value: str = Field(min_length=2, max_length=48, pattern=r"^[A-Z][A-Z0-9_]*$")
    label: str = Field(min_length=2, max_length=80)

    @field_validator('label')
    @classmethod
    def clean_label(cls, value: str) -> str:
        """Evita catálogo com rótulo em branco sem restringir o domínio."""
        value = value.strip()
        if len(value) < 2:
            raise ValueError('O nome do tipo de entidade precisa de pelo menos 2 caracteres.')
        return value


class EnvironmentChange(Contract):
    """Evento opcional programado para alterar um mundo durante uma rodada.

    O impacto é um parâmetro de laboratório, não uma estimativa causal.
    """

    round: int = Field(ge=1, le=6)
    name: str = Field(min_length=3, max_length=90)
    description: str = Field(min_length=5, max_length=600)
    impact: float = Field(default=0, ge=-1, le=1)
    variable_updates: dict[str, str] = Field(default_factory=dict)

    @field_validator("variable_updates")
    @classmethod
    def validate_updates(cls, values: dict[str, str]) -> dict[str, str]:
        if len(values) > 8 or any(not isinstance(k, str) or not isinstance(v, str) or not k.strip() or len(k) > 60 or len(v) > 300 for k, v in values.items()):
            raise ValueError("Até 8 atualizações de variáveis com valores textuais limitados.")
        return values


class MetricDefinition(Contract):
    """Define uma saída verificável por tipo, independentemente do domínio."""

    key: str = Field(min_length=2, max_length=45, pattern=r"^[a-z][a-z0-9_]*$")
    label: str = Field(min_length=2, max_length=90)
    kind: Literal["number", "boolean", "category"] = "number"
    description: str = Field(default="Indicador exclusivamente sintético.", max_length=300)
    minimum: float = Field(default=0, ge=-1000000, le=1000000)
    maximum: float = Field(default=100, ge=-1000000, le=1000000)
    categories: list[str] = Field(default_factory=list, max_length=16)

    @model_validator(mode="after")
    def validate_metric(self):
        if self.kind == "number" and self.minimum >= self.maximum:
            raise ValueError("A métrica numérica exige máximo superior ao mínimo.")
        if self.kind == "category" and (len(self.categories) < 2 or len(set(self.categories)) != len(self.categories) or any(not 1 <= len(c) <= 60 for c in self.categories)):
            raise ValueError("A métrica categórica exige de 2 a 16 categorias distintas.")
        if self.kind != "category" and self.categories:
            raise ValueError("Categorias só são permitidas para métricas categóricas.")
        return self


class EnvironmentInput(Contract):
    """Contexto, decisão hipotética e variáveis controladas do experimento."""

    name: str = Field(min_length=3, max_length=90)
    world_type: str = Field(default="Personalizado", min_length=2, max_length=80)

    @field_validator('world_type')
    @classmethod
    def clean_world_type(cls, value: str) -> str:
        """Aceita qualquer domínio ficcional, desde que haja nome legível."""
        value = value.strip()
        if len(value) < 2:
            raise ValueError('Informe um tipo de mundo com pelo menos 2 caracteres.')
        return value
    context: str = Field(min_length=10, max_length=2200)
    decision: str = Field(min_length=10, max_length=1600)
    success_criterion: str = Field(min_length=5, max_length=400)
    target_behavior: str = Field(default="Aderir à decisão apresentada", min_length=3, max_length=160)
    low_label: str = Field(default="Resistência", min_length=2, max_length=45)
    middle_label: str = Field(default="Em avaliação", min_length=2, max_length=45)
    high_label: str = Field(default="Adesão", min_length=2, max_length=45)
    # Limiares do mundo simulado: definem onde começam os níveis médio e alto.
    low_threshold: int = Field(default=40, ge=1, le=98)
    high_threshold: int = Field(default=65, ge=2, le=100)
    events: list[EnvironmentChange] = Field(default_factory=list, max_length=12)
    metrics: list[MetricDefinition] = Field(default_factory=list, max_length=12)
    enable_agent_actions: bool = False
    allowed_agent_effects: dict[str, list[str]] = Field(default_factory=dict)
    variables: dict[str, str] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_thresholds(self):
        """Exige faixas ordenadas e não vazias, inclusive para cenários antigos."""
        if len({metric.key for metric in self.metrics}) != len(self.metrics):
            raise ValueError("Os identificadores das métricas devem ser únicos.")
        if len(self.allowed_agent_effects) > 8:
            raise ValueError('Até 8 variáveis mutáveis pelos agentes.')
        for key, options in self.allowed_agent_effects.items():
            if key not in self.variables or not 1 <= len(options) <= 8 or len(options) != len(set(options)) or any(not 1 <= len(v) <= 100 for v in options):
                raise ValueError('Ações permitidas exigem variável existente e de 1 a 8 valores distintos.')
        if self.low_threshold >= self.high_threshold:
            raise ValueError("O início da faixa média deve ser menor que o início da faixa alta.")
        return self

    @field_validator("variables")
    @classmethod
    def validate_variables(cls, fields: dict[str, str]) -> dict[str, str]:
        if len(fields) > 16 or any(not isinstance(k, str) or not isinstance(v, str) or not k.strip() or len(k) > 60 or len(v) > 300 for k, v in fields.items()):
            raise ValueError("Até 16 variáveis, cada uma com nome e valor textual limitados.")
        return fields


class SocietyInput(Contract):
    """Seleciona indivíduos que podem influenciar-se em cada rodada."""

    name: str = Field(min_length=3, max_length=90)
    description: str = Field(default="Rede de agentes sintéticos", max_length=400)
    agent_ids: list[str] = Field(min_length=1, max_length=30)

    @field_validator("agent_ids")
    @classmethod
    def unique_agents(cls, ids: list[str]) -> list[str]:
        if len(ids) != len(set(ids)):
            raise ValueError("Um agente não pode constar duas vezes na sociedade.")
        return ids


class SimulationInput(Contract):
    """Todas as variáveis estocásticas e limites de execução da simulação."""

    environment_id: str
    society_id: str
    mode: Literal["bridge", "demo"] = "demo"
    rounds: int = Field(default=3, ge=1, le=6)
    repetitions: int = Field(default=1, ge=1, le=10)
    seed: int = Field(default=42, ge=0, le=2147483647)
    temperature: float = Field(default=0.2, ge=0, le=2)
    uncertainty: float = Field(default=0.2, ge=0, le=1)
    social_pressure: float = Field(default=0.55, ge=0, le=1)
    shock_probability: float = Field(default=0.15, ge=0, le=1)
    shock_intensity: float = Field(default=0.35, ge=0, le=1)
    network_density: float = Field(default=0.45, ge=0, le=1)
    max_tokens_per_reaction: int = Field(default=420, ge=128, le=1200)
    memory_window: int = Field(default=4, ge=1, le=10)

    @model_validator(mode="after")
    def validate_ids(self):
        if not self.environment_id.strip() or not self.society_id.strip():
            raise ValueError("Selecione ambiente e sociedade.")
        return self


class Reaction(Contract):
    """Saída estrita de IA, sem inferir certeza científica do resultado."""

    stance: int = Field(ge=0, le=100)
    emotion: str = Field(min_length=2, max_length=70)
    action: str = Field(min_length=2, max_length=180)
    message: str = Field(min_length=3, max_length=900)
    reason: str = Field(min_length=3, max_length=800)
    metrics: dict[str, float | bool | str | None] = Field(default_factory=dict)
    environment_updates: dict[str, str] = Field(default_factory=dict, max_length=4)

    @field_validator('environment_updates')
    @classmethod
    def validate_action_updates(cls, values: dict[str, str]):
        if any(not 1 <= len(key) <= 60 or not 1 <= len(value) <= 100 for key, value in values.items()):
            raise ValueError('Atualização de ambiente inválida.')
        return values

    @field_validator("metrics")
    @classmethod
    def validate_metric_values(cls, values: dict[str, float | bool | str | None]):
        if len(values) > 12:
            raise ValueError("Até 12 métricas por reação.")
        for key, value in values.items():
            if not re.fullmatch(r"[a-z][a-z0-9_]{1,44}", key):
                raise ValueError("Identificador da métrica inválido.")
            if isinstance(value, float) and not math.isfinite(value):
                raise ValueError("Métrica não pode conter valores infinitos ou NaN.")
            if isinstance(value, str) and len(value) > 60:
                raise ValueError("Valor categórico excede 60 caracteres.")
        return values


class ExperimentVariant(Contract):
    """Variante controlada de um experimento para comparação A/B e sensibilidade."""

    name: str = Field(min_length=2, max_length=80)
    parameter_updates: dict[str, float] = Field(default_factory=dict, max_length=8)
    variable_updates: dict[str, str] = Field(default_factory=dict, max_length=12)
    impact: float = Field(default=0, ge=-1, le=1)

    @field_validator("parameter_updates")
    @classmethod
    def accepted_parameters(cls, updates: dict[str, float]) -> dict[str, float]:
        limits = {"temperature": (0, 2), "uncertainty": (0, 1), "social_pressure": (0, 1),
                  "shock_probability": (0, 1), "shock_intensity": (0, 1), "network_density": (0, 1)}
        for key, value in updates.items():
            if key not in limits or not isinstance(value, (float, int)) or not math.isfinite(value) or not limits[key][0] <= value <= limits[key][1]:
                raise ValueError(f"Parâmetro experimental inválido: {key}")
        return updates

    @field_validator("variable_updates")
    @classmethod
    def accepted_variables(cls, updates: dict[str, str]) -> dict[str, str]:
        if any(not key.strip() or len(key) > 60 or not isinstance(value, str) or len(value) > 300 for key, value in updates.items()):
            raise ValueError("Variáveis de comparação inválidas.")
        return updates


class ExperimentInput(Contract):
    """Planeja execuções comparáveis com sementes e agentes correspondentes."""

    name: str = Field(min_length=3, max_length=120)
    hypothesis: str = Field(min_length=10, max_length=1200)
    baseline: SimulationInput
    variants: list[ExperimentVariant] = Field(min_length=1, max_length=6)

    @model_validator(mode="after")
    def validate_variants(self):
        names = [variant.name.casefold() for variant in self.variants]
        if len(names) != len(set(names)) or "base" in names:
            raise ValueError("Nomes de variantes devem ser únicos e diferentes de 'base'.")
        return self


class CalibrationInput(Contract):
    """Comparação opcional com referência agregada previamente revisada."""

    observed_mean: float = Field(ge=0, le=100)
    source_description: str = Field(min_length=10, max_length=300)
    sample_size: int | None = Field(default=None, ge=1, le=100000000)
    validated_by: str = Field(min_length=3, max_length=100)


