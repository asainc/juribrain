"""Testes novos dos catálogos e da jornada, sem dados pessoais ou bancários reais."""
from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest
from fastapi.testclient import TestClient

from backend.config import Settings
from backend.errors import ServiceError
from backend.principal import create_app
from applications.bjn.backend.services.bjn_directory import agencies, departments
from tests.test_bjn_journey import demand_data, identity

BASE = "/api/v3/bjn/demandas"
SYNTHETIC_AGENCY = "1234 - Agencia sintetica"


def test_csv_accepts_documented_headers_and_semicolon(monkeypatch, tmp_path: Path):
    """Os CSVs podem ser atualizados pela implantação, sem alterar o código."""
    dept = tmp_path / "departamentos.csv"
    dept.write_text("departamento\n4040 - Jurídico\n9000 - Unidade sintética\n", encoding="utf-8")
    bank = tmp_path / "agencias.csv"
    bank.write_text("numero_agencia;nome_agencia\n1234;Agencia sintetica\n", encoding="utf-8")
    monkeypatch.setenv("BJN_DEPARTMENTS_CSV", str(dept))
    monkeypatch.setenv("BJN_AGENCIES_CSV", str(bank))
    assert departments() == ["4040 - Jurídico", "9000 - Unidade sintética"]
    assert agencies() == [SYNTHETIC_AGENCY]


def test_csv_rejects_malformed_codes_and_duplicates(monkeypatch, tmp_path: Path):
    """Catálogo inválido falha visivelmente, sem aceitar opções incorretas."""
    dept = tmp_path / "departamentos.csv"
    dept.write_text("departamento\n4040 - Jurídico\n4040 - Jurídico\n", encoding="utf-8")
    monkeypatch.setenv("BJN_DEPARTMENTS_CSV", str(dept))
    with pytest.raises(ServiceError):
        departments()
    agency = tmp_path / "agencias.csv"
    agency.write_text("numero_agencia,nome_agencia\n12,Agencia incorreta\n", encoding="utf-8")
    monkeypatch.setenv("BJN_AGENCIES_CSV", str(agency))
    with pytest.raises(ServiceError):
        agencies()


def test_api_catalog_departments_and_agency_substring(monkeypatch, tmp_path: Path):
    """Registra unidade consultada e consulta agência por código ou palavra."""
    dept = tmp_path / "d.csv"
    dept.write_text("departamento\n4040 - Jurídico\n9000 - Unidade sintética\n", encoding="utf-8")
    bank = tmp_path / "a.csv"
    bank.write_text("numero_agencia,nome_agencia\n1234,Agencia sintetica\n", encoding="utf-8")
    monkeypatch.setenv("BJN_DEPARTMENTS_CSV", str(dept))
    monkeypatch.setenv("BJN_AGENCIES_CSV", str(bank))
    app = create_app(Settings(environment="local", bjn_database_path=tmp_path / "db.sqlite3",
        bjn_upload_directory=tmp_path / "uploads"))
    client = TestClient(app)
    conf = client.get(f"{BASE}/configuracao")
    assert conf.status_code == 200
    assert conf.json()["department_options"] == ["4040 - Jurídico", "9000 - Unidade sintética"]
    assert conf.json()["agency_options"] == [SYNTHETIC_AGENCY]
    proof_response = client.post(f"{BASE}/triagem", headers=identity(), json={"category": "OUTRAS"})
    assert proof_response.status_code == 200
    body = demand_data("Pareceres em geral")
    body.update({"requesting_department": "9000 - Unidade sintética", "consulted_department": "4040 - Jurídico",
        "branch": SYNTHETIC_AGENCY, "triage_proof": proof_response.json()["proof"]})
    response = client.post(f"{BASE}/fluxo", headers=identity(), data={"payload": json.dumps(body)})
    assert response.status_code == 201, response.text
    record = response.json()
    assert record["registration"]["consulted_department"] == "4040 - Jurídico"
    for fragment in ("1234", "sintetica", "Agencia", "1234 - Agencia"):
        result = client.post(f"{BASE}/consulta", headers=identity(), json={"branch": fragment})
        assert result.status_code == 200, result.text
        assert [row["id"] for row in result.json()["items"]] == [record["id"]]
    assert client.post(f"{BASE}/consulta", headers=identity(), json={"branch": "4567"}).json()["items"] == []
    assert client.post(f"{BASE}/consulta", headers=identity(), json={"branch": "%"}).json()["items"] == []
    assert client.post(f"{BASE}/consulta", headers=identity(), json={"branch": "_"}).json()["items"] == []
    body["consulted_department"] = "9000 - Unidade sintética"
    rejected = client.post(f"{BASE}/fluxo", headers=identity(), data={"payload": json.dumps(body)})
    assert rejected.status_code == 422
    body["consulted_department"] = "4040 - Jurídico"
    body["requesting_department"] = "8000 - Inexistente"
    rejected = client.post(f"{BASE}/fluxo", headers=identity(), data={"payload": json.dumps(body)})
    assert rejected.status_code == 422


def test_auto_opinion_endpoint_keeps_existing_draft(tmp_path: Path):
    """Duas aberturas não podem disparar gerações nem substituir texto preliminar."""
    app = create_app(Settings(environment="local", bjn_database_path=tmp_path / "db.sqlite3",
        bjn_upload_directory=tmp_path / "uploads", bjn_allowed_lawyers=["advogado@example.invalid"]))
    client = TestClient(app)
    proof = client.post(f"{BASE}/triagem", headers=identity(), json={"category": "OUTRAS"}).json()["proof"]
    payload = demand_data("Pareceres em geral")
    payload["triage_proof"] = proof
    created = client.post(f"{BASE}/fluxo", headers=identity(), data={"payload": json.dumps(payload)})
    assert created.status_code == 201, created.text
    demand_id = created.json()["id"]
    assert client.patch(f"{BASE}/{demand_id}/competencia", headers=identity("admin"),
        json={"is_team_competence": True}).status_code == 200
    assert client.patch(f"{BASE}/{demand_id}/atribuicao", headers=identity("admin"),
        json={"lawyer_email": "advogado@example.invalid"}).status_code == 200
    calls = []
    def fake_generate(nature: str, description: str):
        calls.append(nature)
        return "Parecer sintético preliminar que exige revisão humana antes de publicar.", "hash-teste"
    app.state.bjn_opinion_ai.generate = fake_generate
    first = client.post(f"{BASE}/{demand_id}/parecer/rascunho", headers=identity("advogado"))
    second = client.post(f"{BASE}/{demand_id}/parecer/rascunho", headers=identity("advogado"))
    assert first.status_code == second.status_code == 200
    assert calls == ["Pareceres em geral"]
    assert second.json()["opinion"]["version"] == 1
    assert second.json()["opinion"]["final_text"] == ""
