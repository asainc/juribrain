"""Cenários integrados com dados fictícios para demandas e pareceres jurídicos."""
from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory

from tests.test_bjn_demands import BASE, actor, create_client, payload


FINAL_OPINION = "Parecer sintético de homologação revisado pelo advogado responsável, sem qualquer decisão jurídica real."
PDF_BYTES = b"%PDF-1.4\n1 0 obj << /Type /Catalog >> endobj\n%%EOF\n"


def register(client, nature: str, name: str = "Protocolo sintético") -> str:
    """Registra protocolo sem pessoas reais para validação de filtros e permissões."""
    data = payload()
    data["service_nature"] = nature
    data["title"] = name
    response = client.post(BASE, headers=actor("requester@example.invalid"), data={"payload": json.dumps(data)})
    assert response.status_code == 201, response.text
    return response.json()["id"]


def test_filter_nature_is_exact_and_combines_with_status_and_access():
    """O filtro por natureza não ignora outros filtros e respeita o solicitante."""
    with TemporaryDirectory() as directory:
        client = create_client(Path(directory))
        inventory_id = register(client, "Inventário", "Inventário sintético")
        order_id = register(client, "Alvará", "Alvará sintético")
        inventory = client.post(f"{BASE}/consulta", headers=actor("requester@example.invalid"),
                                json={"nature": "Inventário"})
        assert inventory.status_code == 200, inventory.text
        assert [item["id"] for item in inventory.json()["items"]] == [inventory_id]
        assert client.get(BASE, params={"nature": "Alvará"},
                          headers=actor("requester@example.invalid")).json()["items"][0]["id"] == order_id
        assert client.post(f"{BASE}/consulta", headers=actor("requester@example.invalid"),
                           json={"nature": "Inventário", "status": "CONCLUIDA"}).json()["items"] == []
        assert client.post(f"{BASE}/consulta", headers=actor("other@example.invalid"),
                           json={"nature": "Inventário"}).json()["items"] == []
        assert client.post(f"{BASE}/consulta", json={"nature": "__invalid__"}).status_code == 422


def test_scope_exclusion_requires_admin_reason_and_undistributed_status():
    """A exclusão é lógica e exige motivo, perfil gestor e etapa apropriada."""
    with TemporaryDirectory() as directory:
        client = create_client(Path(directory))
        uid = register(client, "Alvará")
        path = f"{BASE}/{uid}/exclusao-escopo"
        reason = "Demanda pertence a outra área, fora do escopo do atendimento BJN."
        assert client.post(path, json={"reason": reason}, headers=actor("requester@example.invalid")).status_code == 403
        assert client.post(path, json={"reason": "Curto"}, headers=actor("admin@example.invalid", "admin")).status_code == 422
        excluded = client.post(path, json={"reason": reason}, headers=actor("admin@example.invalid", "admin"))
        assert excluded.status_code == 200, excluded.text
        value = excluded.json()
        assert value["status"] == "EXCLUIDA_ESCOPO"
        assert value["can_exclude_scope"] is False
        assert any(event["event_type"] == "EXCLUSAO_ESCOPO" and reason in event["description"] for event in value["events"])
        # O filtro vazio equivale a "Todos os status", incluindo exclusões.
        for response in (
            client.post(f"{BASE}/consulta", json={}, headers=actor("admin@example.invalid", "admin")),
            client.get(BASE, headers=actor("admin@example.invalid", "admin")),
            client.post(f"{BASE}/consulta", json={}, headers=actor("requester@example.invalid")),
        ):
            assert response.status_code == 200, response.text
            assert uid in {item["id"] for item in response.json()["items"]}
        # A exclusão continua fora das pendências, independente do filtro escolhido.
        for status in ("", "EXCLUIDA_ESCOPO"):
            pending = client.post(f"{BASE}/consulta", headers=actor("admin@example.invalid", "admin"),
                                  json={"status": status, "pending_only": True})
            assert pending.status_code == 200, pending.text
            assert uid not in {item["id"] for item in pending.json()["items"]}
        # O acesso continua limitado ao perfil do solicitante ou do gestor.
        outsider = client.post(f"{BASE}/consulta", json={}, headers=actor("other@example.invalid"))
        assert uid not in {item["id"] for item in outsider.json()["items"]}
        archived = client.post(f"{BASE}/consulta", headers=actor("admin@example.invalid", "admin"),
                               json={"status": "EXCLUIDA_ESCOPO"}).json()["items"]
        assert [item["id"] for item in archived] == [uid]
        assert client.get(f"{BASE}/{uid}", headers=actor("requester@example.invalid")).status_code == 200
        assert client.patch(f"{BASE}/{uid}/atribuicao", headers=actor("admin@example.invalid", "admin"),
                            json={"lawyer_email": "lawyer@example.invalid"}).status_code == 409
        assert client.post(path, json={"reason": reason}, headers=actor("admin@example.invalid", "admin")).status_code == 409


def test_scope_exclusion_does_not_remove_an_already_assigned_demand():
    """Uma demanda distribuída exige fluxo jurídico regular, sem exclusão administrativa."""
    with TemporaryDirectory() as directory:
        client = create_client(Path(directory))
        uid = register(client, "Curatela")
        assigned = client.patch(f"{BASE}/{uid}/atribuicao", headers=actor("admin@example.invalid", "admin"),
                                json={"lawyer_email": "lawyer@example.invalid"})
        assert assigned.status_code == 200
        denied = client.post(f"{BASE}/{uid}/exclusao-escopo", headers=actor("admin@example.invalid", "admin"),
                             json={"reason": "A competência pertence a outra unidade e exige reavaliação."})
        assert denied.status_code == 409
        assert client.get(f"{BASE}/{uid}").json()["status"] == "EM_ANALISE"


def test_opinion_publishes_with_attachments_and_permitted_document_preview():
    """Advogado publica documento complementar e o solicitante o consulta por protocolo."""
    with TemporaryDirectory() as directory:
        client = create_client(Path(directory))
        uid = register(client, "Inventário")
        assert client.patch(f"{BASE}/{uid}/atribuicao", headers=actor("admin@example.invalid", "admin"),
                            json={"lawyer_email": "lawyer@example.invalid"}).status_code == 200
        route = f"{BASE}/{uid}/parecer/publicar-com-anexos"
        fields = {"final_text": FINAL_OPINION, "human_review_confirmed": "true"}
        upload = [("files", ("complemento.pdf", PDF_BYTES, "application/pdf")),
                  ("files", ("imagem.png", b"\x89PNG\r\n\x1a\n" + b"\x00" * 16, "image/png"))]
        assert client.post(route, data=fields, files=upload, headers=actor("admin@example.invalid", "admin")).status_code == 403
        published = client.post(route, data=fields, files=upload, headers=actor("lawyer@example.invalid", "advogado"))
        assert published.status_code == 200, published.text
        item = published.json()
        assert item["status"] == "CONCLUIDA" and item["opinion"]["final_text"] == FINAL_OPINION
        docs = [doc for doc in item["documents"] if doc["category"] == "PARECER_COMPLEMENTAR"]
        assert {doc["original_name"] for doc in docs} == {"complemento.pdf", "imagem.png"}
        assert any(event["event_type"] == "PARECER_ANEXOS" for event in item["events"])
        document = next(doc for doc in docs if doc["original_name"] == "complemento.pdf")
        view_path = f"{BASE}/{uid}/documentos/{document['id']}/arquivo"
        assert client.get(view_path, headers=actor("requester@example.invalid")).content == PDF_BYTES
        assert client.get(view_path, headers=actor("outsider@example.invalid")).status_code == 404
        assert client.post(route, data=fields, files=upload,
                           headers=actor("lawyer@example.invalid", "advogado")).status_code == 409


def test_invalid_attachments_do_not_publish_opinion_or_leave_uploads():
    """Falha de formato impede tanto o parecer quanto qualquer arquivo residual."""
    with TemporaryDirectory() as directory:
        root = Path(directory)
        client = create_client(root)
        uid = register(client, "Procuração")
        assert client.patch(f"{BASE}/{uid}/atribuicao", headers=actor("admin@example.invalid", "admin"),
                            json={"lawyer_email": "lawyer@example.invalid"}).status_code == 200
        fields = {"final_text": FINAL_OPINION, "human_review_confirmed": "true"}
        route = f"{BASE}/{uid}/parecer/publicar-com-anexos"
        rejected = client.post(route, data=fields, headers=actor("lawyer@example.invalid", "advogado"),
                               files=[("files", ("correct.pdf", PDF_BYTES, "application/pdf")),
                                      ("files", ("incorrect.pdf", b"executable content", "application/pdf"))])
        assert rejected.status_code == 415
        detail = client.get(f"{BASE}/{uid}", headers=actor("lawyer@example.invalid", "advogado")).json()
        assert detail["status"] == "EM_ANALISE" and detail["opinion"] is None
        assert detail["documents"] == []
        assert list((root / "uploads").iterdir()) == []
        assert client.post(route, data={**fields, "human_review_confirmed": "false"},
                           headers=actor("lawyer@example.invalid", "advogado")).status_code == 422


def test_legacy_json_publication_still_works_without_files():
    """O endpoint anterior permanece compatível para integrações existentes."""
    with TemporaryDirectory() as directory:
        client = create_client(Path(directory))
        uid = register(client, "Alvará")
        assert client.patch(f"{BASE}/{uid}/atribuicao", headers=actor("admin@example.invalid", "admin"),
                            json={"lawyer_email": "lawyer@example.invalid"}).status_code == 200
        response = client.post(f"{BASE}/{uid}/parecer/publicar", headers=actor("lawyer@example.invalid", "advogado"),
                               json={"final_text": FINAL_OPINION, "human_review_confirmed": True})
        assert response.status_code == 200, response.text
        assert response.json()["documents"] == []
