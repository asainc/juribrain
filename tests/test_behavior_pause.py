"""Regressão do controle de pausa/retomada com dados estritamente sintéticos."""
from __future__ import annotations

import sqlite3
import threading
import time

from fastapi.testclient import TestClient

from applications.behavior.backend.repository import LabRepository
from backend.config import Settings
from backend.principal import create_app

ROOT = "/api/v3/laboratorio-comportamental"


def _wait_status(client: TestClient, run_id: str, expected: set[str], timeout: float = 5) -> dict:
    """Aguarda um estado observável, sem depender da velocidade fixa de um worker."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        response = client.get(f"{ROOT}/simulacoes/{run_id}")
        assert response.status_code == 200
        run = response.json()
        if run["status"] in expected:
            return run
        time.sleep(0.025)
    raise AssertionError(f"O experimento não alcançou {expected} no prazo")


def _start_slow_demo(client: TestClient, mock_controller) -> str:
    """Prepara um cenário fictício com primeira reação bloqueada para testar concorrência."""
    example = client.post(f"{ROOT}/exemplos")
    assert example.status_code == 201
    setup = example.json()
    simulator = client.app.state.behavioral_lab_simulator
    original = simulator._demo_reaction

    def delayed_reaction(*args, **kwargs):
        # O evento sinaliza que a operação está em curso antes de pedir a pausa.
        mock_controller["started"].set()
        assert mock_controller["release"].wait(8), "A primeira reação não foi liberada"
        return original(*args, **kwargs)

    simulator._demo_reaction = delayed_reaction
    response = client.post(f"{ROOT}/simulacoes", json={
        "environment_id": setup["environment"]["id"],
        "society_id": setup["society"]["id"],
        "rounds": 2, "repetitions": 1, "mode": "demo", "seed": 42,
    })
    assert response.status_code == 202, response.text
    assert mock_controller["started"].wait(4), "A primeira reação não começou"
    return response.json()["id"]


def test_pause_stops_new_reactions_then_resume_preserves_progress(tmp_path):
    """Pausa real bloqueia novas reações e retoma o mesmo run/resultado."""
    events = {"started": threading.Event(), "release": threading.Event()}
    with TestClient(create_app(Settings(behavioral_lab_database_path=tmp_path / "pausa.sqlite3"))) as client:
        run_id = _start_slow_demo(client, events)
        try:
            reply = client.post(f"{ROOT}/simulacoes/{run_id}/pausar")
            assert reply.status_code == 200 and reply.json()["status"] == "PAUSE_REQUESTED"
            # A chamada já iniciada termina; o checkpoint segura a gravação.
            events["release"].set()
            paused = _wait_status(client, run_id, {"PAUSED"})
            assert paused["pause_requested"] is True
            assert paused["completed"] == 0
            before = len(paused["events"])
            time.sleep(0.25)
            still = client.get(f"{ROOT}/simulacoes/{run_id}").json()
            assert still["status"] == "PAUSED" and still["completed"] == 0
            assert len(still["events"]) == before
            invalid = client.post(f"{ROOT}/simulacoes/{run_id}/pausar")
            assert invalid.status_code == 409
            resumed = client.post(f"{ROOT}/simulacoes/{run_id}/retomar")
            assert resumed.status_code == 200
            complete = _wait_status(client, run_id, {"COMPLETED"})
            assert complete["completed"] == complete["total"] == 12
            assert len([event for event in complete["events"] if event["event_type"] == "REACTION"]) == 12
            assert client.post(f"{ROOT}/simulacoes/{run_id}/retomar").status_code == 409
        finally:
            events["release"].set()


def test_cancel_while_paused_does_not_require_resume(tmp_path):
    """Cancelar execução pausada encerra o worker sem retomada manual."""
    events = {"started": threading.Event(), "release": threading.Event()}
    with TestClient(create_app(Settings(behavioral_lab_database_path=tmp_path / "cancelar.sqlite3"))) as client:
        run_id = _start_slow_demo(client, events)
        try:
            assert client.post(f"{ROOT}/simulacoes/{run_id}/pausar").status_code == 200
            events["release"].set()
            _wait_status(client, run_id, {"PAUSED"})
            assert client.post(f"{ROOT}/simulacoes/{run_id}/cancelar").status_code == 200
            done = _wait_status(client, run_id, {"CANCELLED"})
            assert done["completed"] == 0 and done["cancel_requested"]
            assert client.post(f"{ROOT}/simulacoes/{run_id}/retomar").status_code == 409
        finally:
            events["release"].set()


def test_paused_run_is_interrupted_on_restart(tmp_path):
    """Após reinício, um worker perdido não pode aparecer como retomável."""
    path = tmp_path / "restart.sqlite3"
    repo = LabRepository(path)
    with sqlite3.connect(path) as db:
        db.execute("INSERT INTO lab_runs (id,status,mode,configuration,snapshot,total,created_at,updated_at,pause_requested) "
                   "VALUES (?,?,?,?,?,?,?,?,?)",
                   ("simulacao-ficticia", "PAUSED", "demo", "{}", "{}", 1, "inicio", "atualizacao", 1))
    new_repo = LabRepository(path)
    run = new_repo.get_run("simulacao-ficticia")
    assert run["status"] == "INTERRUPTED"
    assert run["error_code"] == "SERVER_RESTART"
    assert run["pause_requested"] is False


def test_legacy_database_is_migrated_without_dropping_runs(tmp_path):
    """Atualização preserva bases criadas antes da coluna de pausa."""
    path = tmp_path / "legacy.sqlite3"
    with sqlite3.connect(path) as db:
        db.execute("CREATE TABLE lab_runs (id TEXT PRIMARY KEY,status TEXT NOT NULL,mode TEXT NOT NULL, "
                   "configuration TEXT NOT NULL,snapshot TEXT NOT NULL,result TEXT,error_code TEXT, "
                   "completed INTEGER NOT NULL DEFAULT 0,total INTEGER NOT NULL, "
                   "cancel_requested INTEGER NOT NULL DEFAULT 0,created_at TEXT NOT NULL,updated_at TEXT NOT NULL)")
        db.execute("INSERT INTO lab_runs (id,status,mode,configuration,snapshot,total,created_at,updated_at) "
                   "VALUES ('legado','COMPLETED','demo','{}','{}',1,'inicio','atualizacao')")
    repo = LabRepository(path)
    preserved = repo.get_run("legado")
    assert preserved["status"] == "COMPLETED" and preserved["pause_requested"] is False
