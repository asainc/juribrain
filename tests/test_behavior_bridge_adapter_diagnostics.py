"""Integração do Behavior com a fachada corporativa real, sem usar rede ou segredos."""
from __future__ import annotations

import json
import time
from types import SimpleNamespace

from fastapi.testclient import TestClient
from pydantic import SecretStr

from backend.config import Settings
from backend.principal import create_app
from backend.services.bradesco_bridge import BradescoBridgeClient, BradescoBridgeError


def _wait(client: TestClient, run_id: str) -> dict:
    """Aguarda o worker local apenas até uma transição terminal verificável."""
    for _ in range(300):
        run = client.get(f"/api/v3/laboratorio-comportamental/simulacoes/{run_id}").json()
        if run["status"] in {"COMPLETED", "FAILED", "CANCELLED", "INTERRUPTED"}:
            return run
        time.sleep(.02)
    raise AssertionError("Worker de teste não terminou")


def _app(tmp_path, text_generator):
    """Configura a integração compartilhada com valores exclusivamente fictícios."""
    settings = Settings(
        behavioral_lab_database_path=tmp_path / "behavior.sqlite3",
        bradesco_text_model="deployment-ficticio",
        bradesco_identificador=SecretStr("teste-identificador"),
        bradesco_senha=SecretStr("teste-senha"),
    )
    app = create_app(settings)
    bridge = BradescoBridgeClient(settings)
    bridge._module = SimpleNamespace(text_generator=text_generator)
    app.state.bridge = bridge
    app.state.behavioral_lab_simulator.bridge = bridge
    return app


def _start(client: TestClient) -> dict:
    """Cria um cenário sintético e submete uma reação real à fachada mockada."""
    root = "/api/v3/laboratorio-comportamental"
    created = client.post(f"{root}/exemplos").json()
    reply = client.post(f"{root}/simulacoes", json={
        "environment_id": created["environment"]["id"],
        "society_id": created["society"]["id"],
        "mode": "bridge", "rounds": 2, "temperature": .7,
    })
    assert reply.status_code == 202, reply.text
    return _wait(client, reply.json()["id"])


def test_behavior_uses_shared_adapter_with_per_run_temperature(tmp_path):
    """Reproduz e evita TypeError de temperature no adaptador central."""
    calls = []

    def fake_text(payload, parameters):
        calls.append((payload, parameters))
        return json.dumps({
            "stance": 55, "emotion": "cautela", "action": "avaliar",
            "message": "Estou avaliando o cenário fictício.",
            "reason": "Minha posição ainda é intermediária.",
            "metrics": {}, "environment_updates": {},
        })

    with TestClient(_app(tmp_path, fake_text)) as client:
        run = _start(client)
    assert run["status"] == "COMPLETED", (run["error_code"], run.get("error_reason"))
    assert run["started_at"] and run["finished_at"]
    assert run["elapsed_seconds"] is not None and run["elapsed_seconds"] >= 0
    assert len(calls) == run["total"]
    assert all(parameters["temperature"] == .7 for _, parameters in calls)
    assert all(parameters["deployment_name"] == "deployment-ficticio" for _, parameters in calls)
    assert all(parameters["stream"] is False for _, parameters in calls)


def test_error_reason_is_sanitized_and_stage_is_explicit(tmp_path):
    """Não expõe resposta do serviço nem credenciais no diagnóstico do usuário."""

    def fake_text(payload, parameters):
        raise BradescoBridgeError("bradesco_credencial_invalida", "segredo_somente_de_teste", 401)

    with TestClient(_app(tmp_path, fake_text)) as client:
        run = _start(client)
        history = client.get("/api/v3/laboratorio-comportamental/simulacoes").json()
    assert run["status"] == "FAILED"
    assert run["error_code"] == "bradesco_credencial_invalida"
    assert run["failure_stage"] == "CHAMADA_IA"
    assert "Autenticação" in run["error_reason"]
    assert "segredo_somente_de_teste" not in str(run)
    assert run["finished_at"] and run["started_at"]
    assert next(row for row in history if row["id"] == run["id"])["error_reason"] == run["error_reason"]


def test_default_temperature_remains_unchanged_for_other_apps(tmp_path):
    """A nova assinatura preserva a temperatura global nas chamadas sem override."""
    collected = []

    def fake_text(payload, parameters):
        collected.append(parameters)
        return "Texto de teste"

    client = BradescoBridgeClient(Settings(bradesco_text_temperature=.35))
    client._module = SimpleNamespace(text_generator=fake_text)
    assert client.generate_text("teste", max_tokens=256) == "Texto de teste"
    assert collected[0]["temperature"] == .35
