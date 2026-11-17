"""Regressão BJN: lote, perfis, filtros e IA documental com dados sintéticos."""
from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory

import pymupdf
import pytest
from fastapi.testclient import TestClient

from backend.config import Settings
from backend.principal import create_app
from applications.bjn.backend.services.bjn_nature_classifier import BjnNatureClassifier, NATURE_FILES
from backend.errors import ServiceError

BASE = "/api/v3/bjn/demandas"


def actor(user: str, role: str) -> dict:
    """Cria credenciais fictícias exclusivamente para o ambiente local de testes."""
    return {"X-Authenticated-User": user, "X-Authenticated-Role": role, "X-Authenticated-Name": "Usuario de teste"}


def data() -> dict:
    """Evita qualquer conteúdo de produção e ativa cadastro legado de desenvolvimento."""
    return {"requesting_department": "Departamento ficticio", "consult_area": "Consultivo sintetico",
            "service_nature": "Alvará", "title": "Demanda juridica sintetica",
            "description": "Consulta juridica de teste com descricao suficientemente longa."}


def pdf_text() -> bytes:
    """Gera PDF em memória para testar o extrator sem serviços externos."""
    pdf = pymupdf.open()
    page = pdf.new_page()
    page.insert_text((40, 80), "Espolio, inventariante, monte mor e partilha de bens aos herdeiros. " * 4)
    content = pdf.tobytes()
    pdf.close()
    return content


class FakeBridge:
    """Simula text_generator: a saída é fixada por teste e nenhuma rede é acessada."""
    configured = True

    def __init__(self, answer: str):
        self.answer = answer
        self.last_payload = ""

    def generate_text(self, payload: str, *, max_tokens: int) -> str:
        """Captura contexto para testar os prompts sem registrar documentos em logs."""
        self.last_payload = payload
        return self.answer


def client_in(root: Path):
    """Cria banco isolado e configura nomes de advogados permitidos."""
    settings = Settings(environment="local", bjn_database_path=root / "data.sqlite", bjn_upload_directory=root / "files",
                        bjn_allowed_lawyers=["lawyer.a@example.invalid", "lawyer.b@example.invalid"],
                        bjn_lawyer_names={"lawyer.a@example.invalid": "Advogado Alfa", "lawyer.b@example.invalid": "Advogada Beta"})
    app = create_app(settings)
    return TestClient(app), app


def create_demand(client: TestClient, requester: str) -> str:
    """Cria protocolo sem PDF, para testar transações e visibilidade de maneira isolada."""
    response = client.post(BASE, headers=actor(requester, "solicitante"), data={"payload": json.dumps(data())})
    assert response.status_code == 201, response.text
    return response.json()["id"]


def test_bulk_assignment_is_atomic_and_admin_only():
    """Falha de um item não pode distribuir nenhum dos outros; eventos auditáveis por demanda."""
    with TemporaryDirectory() as directory:
        client, _ = client_in(Path(directory))
        first = create_demand(client, "requester.a@example.invalid")
        second = create_demand(client, "requester.b@example.invalid")
        endpoint = BASE + "/atribuicao/lote"
        selection = {"demand_ids": [first, second], "lawyer_email": "lawyer.a@example.invalid"}
        assert client.patch(endpoint, headers=actor("requester.a@example.invalid", "solicitante"), json=selection).status_code == 403
        assert client.patch(endpoint, headers=actor("admin@example.invalid", "admin"), json={**selection, "lawyer_email": "external@example.invalid"}).status_code == 422
        assert client.patch(endpoint, headers=actor("admin@example.invalid", "admin"), json={"demand_ids": [first, "NON-EXISTENT"], "lawyer_email": "lawyer.a@example.invalid"}).status_code == 404
        assert client.get(BASE + "/" + first, headers=actor("admin@example.invalid", "admin")).json()["lawyer_email"] is None
        result = client.patch(endpoint, headers=actor("admin@example.invalid", "admin"), json=selection)
        assert result.status_code == 200, result.text
        assert result.json()["assigned_count"] == 2
        for demand_id in (first, second):
            details = client.get(BASE + "/" + demand_id, headers=actor("admin@example.invalid", "admin")).json()
            assert details["status"] == "EM_ANALISE"
            assert details["lawyer_email"] == "lawyer.a@example.invalid"
            assert any(event["event_type"] == "DISTRIBUICAO_LOTE" for event in details["events"])
        assert client.patch(endpoint, headers=actor("admin@example.invalid", "admin"), json={"demand_ids": [first, first], "lawyer_email": "lawyer.a@example.invalid"}).status_code == 422


def test_pending_by_role_and_lawyer_date_filters():
    """Gestor vê todas; advogado só enxerga pendências atribuídas ao próprio perfil."""
    with TemporaryDirectory() as directory:
        client, _ = client_in(Path(directory))
        first = create_demand(client, "requester.a@example.invalid")
        second = create_demand(client, "requester.b@example.invalid")
        third = create_demand(client, "requester.c@example.invalid")
        for demand_id, lawyer in ((first, "lawyer.a@example.invalid"), (second, "lawyer.b@example.invalid")):
            assert client.patch(BASE + f"/{demand_id}/atribuicao", headers=actor("admin@example.invalid", "admin"), json={"lawyer_email": lawyer}).status_code == 200
        admin = actor("admin@example.invalid", "admin")
        pending = {"pending_only": True}
        assert len(client.post(BASE + "/consulta", headers=admin, json=pending).json()["items"]) == 3
        for user, expected in (("lawyer.a@example.invalid", first), ("lawyer.b@example.invalid", second)):
            items = client.post(BASE + "/consulta", headers=actor(user, "advogado"), json=pending).json()["items"]
            assert [item["id"] for item in items] == [expected]
        only_one = client.post(BASE + "/consulta", headers=admin, json={**pending, "lawyer": "Advogado Alfa"}).json()["items"]
        assert [item["id"] for item in only_one] == [first]
        from datetime import date
        today = date.today().isoformat()
        assert len(client.post(BASE + "/consulta", headers=admin, json={"from_date": today, "to_date": today}).json()["items"]) == 3
        assert not client.post(BASE + "/consulta", headers=admin,
                               json={"from_date": "1900-01-01", "to_date": "1900-01-02"}).json()["items"]
        assert client.post(BASE + "/consulta", headers=admin, json={"from_date": "2026-11-10", "to_date": "2026-01-01"}).status_code == 422
        assert client.post(BASE + "/consulta", headers=actor("requester.c@example.invalid", "solicitante"), json=pending).json()["items"][0]["id"] == third


@pytest.mark.parametrize("label", [*NATURE_FILES])
def test_classifier_accepts_only_exact_canonical_label(label: str):
    """Não usa heurísticas ou texto livre como valor autorizado da natureza."""
    bridge = FakeBridge(label)
    classified = BjnNatureClassifier(bridge).classify([("test.pdf", "application/pdf", pdf_text(), "synthetic")], "Alvará")
    assert classified.status == "IDENTIFICADA"
    assert classified.detected_nature == label
    assert "<documentos_nao_confiaveis>" in bridge.last_payload
    for value in NATURE_FILES:
        assert f"### {value}" in bridge.last_payload
    assert classified.prompt_hash


def test_classifier_ambiguity_does_not_change_nature():
    """Resposta ambígua, erro de IA e PDF sem texto exigem revisão humana."""
    service = BjnNatureClassifier(FakeBridge("Provavelmente Inventário, mas pode ser Alvará."))
    classified = service.classify([("test.pdf", "application/pdf", pdf_text(), "synthetic")], "Alvará")
    assert classified.detected_nature is None and classified.status == "INDETERMINADA"
    scanner = pymupdf.open(); scanner.new_page(); empty = scanner.tobytes(); scanner.close()
    with pytest.raises(ServiceError) as error:
        service.classify([("scanned.pdf", "application/pdf", empty, "synthetic")], "Inventário")
    assert error.value.code == "DOCUMENT_TEXT_UNAVAILABLE"


def test_preview_and_upload_correct_nature_and_write_audit_event():
    """Modelo sintético corrige alvará para inventário na API e registra origem auditável."""
    with TemporaryDirectory() as directory:
        client, app = client_in(Path(directory))
        app.state.bjn_nature_classifier = BjnNatureClassifier(FakeBridge("Inventário"))
        content = pdf_text()
        file_data = [("files", ("fake.pdf", content, "application/pdf"))]
        preview = client.post(BASE + "/assistente/classificar-natureza", headers=actor("admin@example.invalid", "admin"),
                              data={"selected_nature": "Alvará"}, files=file_data)
        assert preview.status_code == 200, preview.text
        assert preview.json()["detected_nature"] == "Inventário"
        assert preview.json()["changed"] is True
        created = client.post(BASE, headers=actor("requester@example.invalid", "solicitante"), data={"payload": json.dumps(data())}, files=file_data)
        assert created.status_code == 201, created.text
        assert created.json()["service_nature"] == "Inventário"
        assert created.json()["nature_classification"]["changed"] is True
        assert any(event["event_type"] == "NATUREZA_CORRIGIDA_IA" for event in created.json()["events"])
        detail = client.get(BASE + "/" + created.json()["id"], headers=actor("requester@example.invalid", "solicitante"))
        assert detail.json()["service_nature"] == "Inventário"


def test_batch_rejects_closed_demand_without_partial_assignment():
    """Demanda cancelada torna todo o lote inelegível sem efeitos colaterais."""
    with TemporaryDirectory() as directory:
        client, _ = client_in(Path(directory))
        closed = create_demand(client, "requester.first@example.invalid")
        open_id = create_demand(client, "requester.second@example.invalid")
        admin = actor("admin@example.invalid", "admin")
        cancelled = client.patch(BASE + "/" + closed + "/status", headers=admin,
                                 json={"status": "CANCELADA", "note": "Teste de encerramento"})
        assert cancelled.status_code == 200
        result = client.patch(BASE + "/atribuicao/lote", headers=admin, json={"demand_ids": [open_id, closed],
                                "lawyer_email": "lawyer.b@example.invalid"})
        assert result.status_code == 409
        assert client.get(BASE + "/" + open_id, headers=admin).json()["lawyer_email"] is None
        pending = client.post(BASE + "/consulta", headers=admin, json={"pending_only": True}).json()["items"]
        assert [item["id"] for item in pending] == [open_id]


def test_classifier_preserves_selected_nature_if_unavailable():
    """Integração desconectada não gera falso positivo e não bloqueia o usuário."""
    class MissingBridge:
        configured = False
    result = BjnNatureClassifier(MissingBridge()).classify([("file.pdf", "application/pdf", pdf_text(), "synthetic")], "Alvará")
    assert result.status == "INDISPONIVEL" and result.detected_nature is None and not result.as_dict()["changed"]


def test_classification_general_opinion_moves_to_competence_review():
    """A categoria geral exige triagem manual inclusive após correção documental."""
    with TemporaryDirectory() as directory:
        client, app = client_in(Path(directory))
        app.state.bjn_nature_classifier = BjnNatureClassifier(FakeBridge("Pareceres em geral"))
        created = client.post(BASE, headers=actor("requester@example.invalid", "solicitante"),
                              data={"payload": json.dumps(data())},
                              files=[("files", ("fake.pdf", pdf_text(), "application/pdf"))])
        assert created.status_code == 201, created.text
        assert created.json()["service_nature"] == "Pareceres em geral"
        assert created.json()["status"] == "TRIAGEM_ADMINISTRATIVA"
        result = client.patch(BASE + "/atribuicao/lote", headers=actor("admin@example.invalid", "admin"),
                              json={"demand_ids": [created.json()["id"]], "lawyer_email": "lawyer.a@example.invalid"})
        assert result.status_code == 409
