"""Regressão do cadastro BJN com falhas pós-gravação e de persistência.

Todos os dados e identificadores utilizados são sintéticos e isolados em tmp_path.
"""
from __future__ import annotations

import json
import logging
import sqlite3
from pathlib import Path

from fastapi.testclient import TestClient

from backend.config import Settings
from backend.principal import create_app
from applications.bjn.backend.services.bjn_demand_store import save_upload
from backend.errors import ServiceError
from tests.test_bjn_journey import identity, demand_data

BASE = "/api/v3/bjn/demandas"
PDF = b"%PDF-1.4\n1 0 obj<<>>endobj\n%%EOF\n"


def make_client(tmp_path: Path) -> tuple[TestClient, object]:
    """Cria uma instância nova para evitar reutilizar bases de outras execuções."""
    app = create_app(Settings(
        environment="local",
        bjn_database_path=tmp_path / "demandas.sqlite3",
        bjn_upload_directory=tmp_path / "uploads",
    ))
    return TestClient(app), app


def register_with_pdf(client: TestClient):
    """Simula a abertura completa de uma demanda do tipo Inventário."""
    proof = client.post(f"{BASE}/triagem", headers=identity(), json={"category": "OUTRAS"}).json()["proof"]
    body = demand_data("Inventário")
    body["triage_proof"] = proof
    return client.post(f"{BASE}/fluxo", headers=identity(), data={"payload": json.dumps(body)},
                       files=[("files", ("exemplo.pdf", PDF, "application/pdf"))])


def test_nature_classification_unexpected_failure_does_not_invalidate_committed_registration(tmp_path, monkeypatch):
    """Falha do modelo ou do leitor posterior ao commit não pode criar falso erro de cadastro."""
    client, app = make_client(tmp_path)

    def broken_classification(*args, **kwargs):
        raise RuntimeError("erro sintético após gravação")

    monkeypatch.setattr(app.state.bjn_nature_classifier, "classify", broken_classification)
    created = register_with_pdf(client)
    assert created.status_code == 201, created.text
    data = created.json()
    assert data["nature_classification"]["status"] == "INDETERMINADA"
    assert data["nature_classification"]["detected_nature"] is None
    assert data["id"].startswith("BJN-")
    assert len(client.get(f"{BASE}/{data['id']}", headers=identity()).json()["documents"]) == 1


def test_document_analysis_unexpected_failure_does_not_invalidate_committed_registration(tmp_path, monkeypatch):
    """Documento salvo continua acessível se geração complementar da IA falhar."""
    client, app = make_client(tmp_path)

    def broken_document_opinion(*args, **kwargs):
        raise RuntimeError("erro sintético na análise documental")

    monkeypatch.setattr(app.state.bjn_document_opinion, "analyze", broken_document_opinion)
    created = register_with_pdf(client)
    assert created.status_code == 201, created.text
    assert "Cadastro realizado" in created.json()["document_analysis_error"]
    assert created.json()["id"] in [item["id"] for item in client.get(BASE, headers=identity()).json()["items"]]


def test_locked_database_is_explicit_and_has_request_id(tmp_path, monkeypatch):
    """Uma base ocupada retorna orientação segura, sem SQL nem dados no navegador."""
    client, app = make_client(tmp_path)

    def locked_database():
        raise sqlite3.OperationalError("database is locked")

    monkeypatch.setattr(app.state.bjn_demand_store, "_connect", locked_database)
    created = register_with_pdf(client)
    assert created.status_code == 503
    body = created.json()
    assert body["code"] == "DATABASE_BUSY"
    assert body["retryable"] is True
    assert len(body["request_id"]) >= 16
    assert "database is locked" not in str(body)


def test_storage_failure_is_explicit_and_avoids_filename_leak(tmp_path):
    """Diretório indisponível resulta em erro controlado de armazenamento."""
    missing = tmp_path / "missing_upload_directory"
    try:
        with open(tmp_path / "synthetic.pdf", "wb") as writer:
            writer.write(PDF)
        with open(tmp_path / "synthetic.pdf", "rb") as handle:
            save_upload(handle, "exemplo.pdf", "application/pdf", missing, "ANEXO")
        raise AssertionError("Deveria rejeitar o diretório indisponível")
    except ServiceError as error:
        assert error.status_code == 503
        assert error.code == "UPLOAD_STORAGE_UNAVAILABLE"
        assert str(missing) not in error.message


def test_unknown_persistence_failure_is_correlated_without_sensitive_values(tmp_path, monkeypatch):
    """O rastreamento permite identificar a etapa, sem enviar exceção crua ao cliente."""
    client, app = make_client(tmp_path)

    def broken_create(*args, **kwargs):
        raise RuntimeError("mensagem técnica sintética não exibida ao cliente")

    monkeypatch.setattr(app.state.bjn_demand_store, "create", broken_create)
    seen = []

    class EventRecorder(logging.Handler):
        """Captura apenas registros do teste, sem escrever conteúdo nos arquivos."""
        def emit(self, record):
            seen.append(record)

    recorder = EventRecorder()
    audit_logger = logging.getLogger("ai_ready")
    audit_logger.addHandler(recorder)
    try:
        response = register_with_pdf(client)
    finally:
        audit_logger.removeHandler(recorder)
    assert response.status_code == 500
    payload = response.json()
    assert payload["code"] == "INTERNAL_ERROR"
    assert "mensagem técnica" not in str(payload)
    request_events = [e for e in seen if e.msg == "request_failed"]
    assert len(request_events) == 1
    assert request_events[0].stage == "registration_persistence"
    assert request_events[0].error_type == "RuntimeError"
    assert request_events[0].request_id == payload["request_id"]
