"""Testes da composição ASGI dos três produtos; não exigem serviços externos."""
from fastapi.testclient import TestClient
from backend.principal import create_app


def test_home_service_health_endpoints():
    """Verifica isolamento e contrato HTTP dos três módulos montados."""
    app = create_app()
    with TestClient(app) as client:
        for url in ("/api/v3/saude", "/services/auditoria/api/v2/saude", "/services/chatbot/api/v3/saude"):
            response = client.get(url)
            assert response.status_code == 200, (url, response.text)
            assert response.json()["status"] == "ok"


def test_modules_keep_distinct_openapi_paths():
    """Confere que as rotas de BJN, auditoria e chatbot não se sobrepõem."""
    app = create_app()
    assert any(route.path == "/services/auditoria" for route in app.routes)
    assert any(route.path == "/services/chatbot" for route in app.routes)
    assert any(route.path == "/api/v3/bjn/demandas" for route in app.routes)


def test_audit_manual_calculation_matches_synthetic_fixture(tmp_path):
    """Executa cálculo original sem serviço externo nem persistência de dados reais."""
    import json
    from pathlib import Path

    from applications.auditoria.backend.config import Settings as AuditSettings
    from applications.auditoria.backend.principal import create_app as create_audit_app

    fixture = Path(__file__).resolve().parents[1] / "applications" / "auditoria" / "tests_original" / "fixtures" / "angular_request.json"
    request = json.loads(fixture.read_text(encoding="utf-8"))
    request["origem_calculo"] = "manual"
    request["numero_processo"] = None
    request["identificador_calculo"] = "synthetic-only"
    with TestClient(create_audit_app(AuditSettings(data_dir=tmp_path))) as client:
        response = client.post("/api/v2/calculos", json=request)
    assert response.status_code == 200, response.text
    assert response.json()["origem_calculo"] == "manual"
    assert {item["campo"]: item["valor"] for item in response.json()["resumo"]}["total_geral"] == "1234.56"
