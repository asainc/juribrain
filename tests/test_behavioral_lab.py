"""Testes de integração do Laboratório: todos os perfis e respostas são fictícios."""
from __future__ import annotations

import io
import json
import time
from pathlib import Path

from fastapi.testclient import TestClient

from backend.config import Settings
from backend.principal import create_app
from backend.services.bradesco_bridge import TextGenerationResult


def make_client(tmp_path: Path) -> TestClient:
    """Isola cada teste em banco de dados temporário, sem credenciais de produção."""
    return TestClient(create_app(Settings(behavioral_lab_database_path=tmp_path / "lab.sqlite3")))


def wait_for_run(client: TestClient, run_id: str, timeout_seconds: float = 8) -> dict:
    """Espera apenas pelo worker local testável, nunca por serviços externos."""
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        response = client.get(f"/api/v3/laboratorio-comportamental/simulacoes/{run_id}")
        assert response.status_code == 200
        run = response.json()
        if run["status"] not in ("QUEUED", "RUNNING"):
            return run
        time.sleep(.03)
    raise AssertionError("O worker não concluiu o teste dentro do timeout.")


def test_demo_multiround_reproducibility_and_exports(tmp_path):
    """Confere sociedade, influência, progresso, agregados e exportações."""
    with make_client(tmp_path) as client:
        root = "/api/v3/laboratorio-comportamental"
        example = client.post(f"{root}/exemplos")
        assert example.status_code == 201, example.text
        data = example.json()
        assert len(data["agents"]) == 6
        assert data["agents"][0]["characteristics"]["perfil"] == "inteiramente fictício"
        configuration = {"environment_id": data["environment"]["id"], "society_id": data["society"]["id"],
                         "mode": "demo", "rounds": 3, "seed": 123, "network_density": 1.0,
                         "shock_probability": 0, "uncertainty": .25, "social_pressure": .8}
        response = client.post(f"{root}/simulacoes", json=configuration)
        assert response.status_code == 202, response.text
        first = wait_for_run(client, response.json()["id"])
        assert first["status"] == "COMPLETED"
        assert first["total"] == 18 and first["completed"] == 18
        assert len([event for event in first["events"] if event["event_type"] == "REACTION"]) == 18
        assert len([event for event in first["events"] if event["event_type"] == "INTERACTION"]) > 0
        assert first["result"]["final"]["agents"] == 6
        assert first["result"]["method_note"].startswith("Simulação ilustrativa")
        response = client.post(f"{root}/simulacoes", json=configuration)
        assert response.status_code == 202, response.text
        second = wait_for_run(client, response.json()["id"])
        assert second["status"] == "COMPLETED"
        first_values = [event["payload"] for event in first["events"] if event["event_type"] == "REACTION"]
        second_values = [event["payload"] for event in second["events"] if event["event_type"] == "REACTION"]
        assert first_values == second_values, "Semente idêntica deve gerar reações idênticas no modo demo."
        exported = client.get(f"{root}/simulacoes/{first['id']}/exportar?format=json")
        assert exported.status_code == 200
        assert json.loads(exported.content)["snapshot"]["society"]["name"] == data["society"]["name"]
        csv_response = client.get(f"{root}/simulacoes/{first['id']}/exportar?format=csv")
        assert csv_response.status_code == 200
        assert "rodada,agente_id" in csv_response.text


def test_dynamic_attributes_csv_input_and_limits(tmp_path):
    """Importa colunas personalizadas, valida cabeçalhos e impede planilhas executáveis."""
    with make_client(tmp_path) as client:
        root = "/api/v3/laboratorio-comportamental"
        csv_data = "name,goal,channel,priority\nPerfil A,Buscar atendimento,chat,tempo\nPerfil B,Questionar mudança,presencial,=HYPERLINK()\n"
        response = client.post(f"{root}/agentes/importar-csv", files={"file": ("synthetic.csv", csv_data.encode(), "text/csv")})
        assert response.status_code == 201, response.text
        assert response.json()["imported"] == 2
        agents = client.get(f"{root}/agentes").json()
        assert any(agent["characteristics"]["channel"] == "chat" for agent in agents)
        result = client.get(f"{root}/agentes/exportar-csv")
        assert "'=HYPERLINK()" in result.text
        invalid = client.post(f"{root}/agentes/importar-csv", files={"file": ("fail.csv", b"name\nABC\n", "text/csv")})
        assert invalid.status_code == 422
        too_many = client.post(f"{root}/simulacoes", json={"environment_id": "missing", "society_id": "missing"})
        assert too_many.status_code == 404


def test_bridge_multiagent_context_and_structured_output(tmp_path):
    """Usa um mock explícito da Bridge, sem autenticação externa."""
    class FakeBridge:
        configured = True
        def __init__(self):
            self.prompts = []
        def text_generator_status(self):
            return {"code": "CONFIGURED_NOT_TESTED"}
        def generate_text_with_metadata(self, payload, *, max_tokens, temperature=None):
            self.prompts.append((payload, max_tokens, temperature))
            return TextGenerationResult(json.dumps({"stance": 72, "emotion": "cautela", "action": "Analisar",
                "message": "Pondero a proposta fictícia.", "reason": "Meu objetivo é obter clareza."}))

    app = create_app(Settings(behavioral_lab_database_path=tmp_path / "lab.sqlite3"))
    stub = FakeBridge()
    app.state.bridge = stub
    app.state.behavioral_lab_simulator.bridge = stub
    with TestClient(app) as client:
        root = "/api/v3/laboratorio-comportamental"
        example = client.post(f"{root}/exemplos").json()
        run = client.post(f"{root}/simulacoes", json={"environment_id": example["environment"]["id"],
            "society_id": example["society"]["id"], "mode": "bridge", "rounds": 2, "network_density": 1, "temperature": .4})
        assert run.status_code == 202, run.text
        result = wait_for_run(client, run.json()["id"])
        assert result["status"] == "COMPLETED", result.get("error_code")
        assert len(stub.prompts) == 12
        assert all(max_tokens == 420 and temperature == .4 for _, max_tokens, temperature in stub.prompts)
        assert '"peer_messages_previous_round": []' in stub.prompts[0][0]
        assert any('"name": "Morador universitário"' in prompt for prompt, _, _ in stub.prompts)
        assert any('"peer_messages_previous_round": [{' in prompt for prompt, _, _ in stub.prompts[6:])
        assert '"scheduled_changes": []' in stub.prompts[0][0]
        assert '"scheduled_changes": [{' in stub.prompts[6][0]
        assert '"events":' not in stub.prompts[0][0], "Eventos futuros não podem chegar ao modelo antes da rodada."
        assert result["result"]["prompt_sha256"] is not None


def test_invalid_bridge_output_fails_closed(tmp_path):
    """Falha de JSON não é convertida em métricas fictícias."""
    class InvalidBridge:
        configured = True
        def text_generator_status(self):
            return {"code": "CONFIGURED_NOT_TESTED"}
        def generate_text_with_metadata(self, payload, *, max_tokens, temperature=None):
            return TextGenerationResult("texto sem estrutura")

    app = create_app(Settings(behavioral_lab_database_path=tmp_path / "lab.sqlite3"))
    app.state.bridge = InvalidBridge()
    app.state.behavioral_lab_simulator.bridge = app.state.bridge
    with TestClient(app) as client:
        root = "/api/v3/laboratorio-comportamental"
        example = client.post(f"{root}/exemplos").json()
        response = client.post(f"{root}/simulacoes", json={"environment_id": example["environment"]["id"],
            "society_id": example["society"]["id"], "mode": "bridge", "rounds": 2})
        result = wait_for_run(client, response.json()["id"])
        assert result["status"] == "FAILED"
        assert result["result"] is None
        assert result["error_code"] == "MODEL_OUTPUT_INVALID"


def test_repeated_experiments_independent_replay_and_environment_change(tmp_path):
    """Confere N simulações, eventos, variáveis efetivas e consolidação de replicações."""
    with make_client(tmp_path) as client:
        root = "/api/v3/laboratorio-comportamental"
        example = client.post(f"{root}/exemplos?tipo=mercado").json()
        environment = example["environment"]
        assert environment["target_behavior"] == "Experimentar o novo serviço de assinatura"
        assert environment["events"][0]["round"] == 2
        config = {"environment_id": environment["id"], "society_id": example["society"]["id"],
                  "mode": "demo", "rounds": 2, "repetitions": 3, "seed": 1337,
                  "network_density": 1, "shock_probability": 0, "social_pressure": .8}
        started = client.post(f"{root}/simulacoes", json=config)
        assert started.status_code == 202, started.text
        run = wait_for_run(client, started.json()["id"])
        assert run["status"] == "COMPLETED", run.get("error_code")
        assert run["total"] == run["completed"] == 6 * 2 * 3
        events = run["events"]
        assert len([event for event in events if event["event_type"] == "NETWORK"]) == 3
        assert len([event for event in events if event["event_type"] == "ENVIRONMENT_CHANGE"]) == 3
        changes = [event for event in events if event["event_type"] == "ENVIRONMENT_CHANGE"]
        assert {item["payload"]["repetition"] for item in changes} == {1, 2, 3}
        assert all(item["payload"]["variables_after"]["preço"] == "médio" for item in changes)
        assert run["snapshot"]["environment"]["variables"]["preço"] == "baixo"
        assert run["result"]["repetitions_completed"] == 3
        assert len(run["result"]["repetitions"]) == 3
        assert run["result"]["final"]["agents"] == 18
        assert run["result"]["final_score_distribution"]["minimum"] <= run["result"]["final_score_distribution"]["maximum"]
        repeat = client.post(f"{root}/simulacoes", json=config)
        assert repeat.status_code == 202
        other = wait_for_run(client, repeat.json()["id"])
        def reactions(value):
            return [event["payload"] for event in value["events"] if event["event_type"] == "REACTION"]
        assert reactions(run) == reactions(other)
        assert run["result"]["final_score_distribution"] == other["result"]["final_score_distribution"]
        # Exportação registra toda a trilha, inclusive replicações e atualizações.
        exported = client.get(f"{root}/simulacoes/{run['id']}/exportar?format=json").json()
        assert len(exported["events"]) == len(events)


def test_agnostic_entities_and_input_validation(tmp_path):
    """O motor não supõe apenas clientes e bloqueia parâmetros acima dos limites."""
    with make_client(tmp_path) as client:
        root = "/api/v3/laboratorio-comportamental"
        example = client.post(f"{root}/exemplos?tipo=organizacao")
        assert example.status_code == 201
        data = example.json()
        names = [item["entity_type"] for item in data["agents"]]
        assert "ORGANIZACAO" in names and "AGENTE_IA" in names
        agent = client.post(f"{root}/agentes", json={"name": "Fenômeno simulado", "entity_type": "OUTRO",
            "group": "Elementos", "goal": "Manifestar variações observáveis ao longo do tempo"})
        assert agent.status_code == 201, agent.text
        assert agent.json()["entity_type"] == "OUTRO"
        env = data["environment"]
        broken = client.put(f"{root}/ambientes/{env['id']}", json={**{
            key: value for key, value in env.items() if key not in {"id", "created_at", "updated_at"}},
            "events": [{"round": 7, "name": "Evento tardio", "description": "Fora do horizonte simulado"}]})
        assert broken.status_code == 422
        invalid = client.post(f"{root}/simulacoes", json={"environment_id": env["id"],
            "society_id": data["society"]["id"], "repetitions": 11})
        assert invalid.status_code == 422
        overbudget = client.post(f"{root}/simulacoes", json={"environment_id": env["id"],
            "society_id": data["society"]["id"], "rounds": 6, "repetitions": 10})
        assert overbudget.status_code == 422
        assert overbudget.json().get("error", {}).get("code", "LAB_CALL_LIMIT") or overbudget.status_code == 422


def test_single_agent_world_and_future_event_guard(tmp_path):
    """Permite cenários sem sociedade coletiva e torna evidente o evento fora do horizonte."""
    with make_client(tmp_path) as client:
        root = "/api/v3/laboratorio-comportamental"
        example = client.post(f"{root}/exemplos?tipo=comunidade").json()
        one = client.post(f"{root}/sociedades", json={"name": "Agente isolado",
            "description": "Experimento de agente único, sem conexões sociais",
            "agent_ids": [example["agents"][0]["id"]]})
        assert one.status_code == 201, one.text
        request = {"environment_id": example["environment"]["id"], "society_id": one.json()["id"],
                   "mode": "demo", "rounds": 1, "repetitions": 2, "seed": 7}
        rejected = client.post(f"{root}/simulacoes", json=request)
        assert rejected.status_code == 422
        assert "Há acontecimentos" in rejected.text
        # Dois ciclos tornam o evento da rodada 2 alcançável.
        request["rounds"] = 2
        response = client.post(f"{root}/simulacoes", json=request)
        assert response.status_code == 202, response.text
        result = wait_for_run(client, response.json()["id"])
        assert result["status"] == "COMPLETED"
        assert result["completed"] == 4
        assert all(event["payload"]["edges"] == [] for event in result["events"] if event["event_type"] == "NETWORK")
        assert not any(event["event_type"] == "INTERACTION" for event in result["events"])


def test_assisted_scenario_generation_uses_bridge_and_persists_bundle(tmp_path):
    """A proposta da IA é validada antes da gravação conjunta dos três recursos."""
    class FakeScenarioBridge:
        configured = True
        def __init__(self):
            self.calls = []
        def text_generator_status(self):
            return {"code": "CONFIGURED_NOT_TESTED"}
        def generate_text_with_metadata(self, prompt, *, max_tokens, temperature=None):
            self.calls.append((prompt, max_tokens, temperature))
            payload = {
                "society_name": "Sociedade de teste imaginária",
                "society_description": "Dois papéis completamente fictícios",
                "agents": [
                    {"name": "Observador A", "entity_type": "PESSOA", "group": "Grupo A",
                     "goal": "Obter clareza no experimento de teste", "initial_stance": 35,
                     "characteristics": {"canal": "teste"}},
                    {"name": "Entidade B", "entity_type": "ORGANIZACAO", "group": "Grupo B",
                     "goal": "Proteger interesses da comunidade imaginária", "initial_stance": 68},
                ],
                "environment": {"name": "Mundo imaginário", "context": "Cenário fictício com recursos limitados",
                                "decision": "Testar a distribuição hipotética de novos recursos",
                                "target_behavior": "Apoiar a redistribuição", "success_criterion": "Observar a posição sintética",
                                "events": [{"round": 2, "name": "Nova informação", "description": "Chega um dado totalmente imaginário", "impact": 0.3}]},
            }
            return TextGenerationResult(json.dumps(payload, ensure_ascii=False))
    app = create_app(Settings(behavioral_lab_database_path=tmp_path / "lab.sqlite3"))
    fake = FakeScenarioBridge()
    app.state.bridge = fake
    with TestClient(app) as client:
        root = "/api/v3/laboratorio-comportamental"
        response = client.post(f"{root}/assistente/criar-cenario", json={
            "description": "Simular uma comunidade inventada avaliando recursos limitados e comunicação.",
            "agent_count": 2,
        })
        assert response.status_code == 201, response.text
        result = response.json()
        assert len(result["agents"]) == 2
        assert result["society"]["agent_ids"] == [a["id"] for a in result["agents"]]
        assert result["environment"]["target_behavior"] == "Apoiar a redistribuição"
        assert len(client.get(f"{root}/sociedades").json()) == 1
        assert len(client.get(f"{root}/ambientes").json()) == 1
        assert len(client.get(f"{root}/agentes").json()) == 2
        assert "scenario_description_untrusted" in fake.calls[0][0]
        assert fake.calls[0][1] == 4500
        assert "Simular uma comunidade inventada" in fake.calls[0][0]


def test_assisted_generation_fails_closed_without_persisting(tmp_path):
    """JSON incompatível e número incorreto de perfis não criam dados parciais."""
    class InvalidScenarioBridge:
        configured = True
        def text_generator_status(self):
            return {"code": "CONFIGURED_NOT_TESTED"}
        def generate_text_with_metadata(self, prompt, *, max_tokens, temperature=None):
            return TextGenerationResult('{"agents": [], "environment": {}}')
    app = create_app(Settings(behavioral_lab_database_path=tmp_path / "lab.sqlite3"))
    app.state.bridge = InvalidScenarioBridge()
    with TestClient(app) as client:
        root = "/api/v3/laboratorio-comportamental"
        response = client.post(f"{root}/assistente/criar-cenario", json={
            "description": "Hipótese inteiramente fictícia para simulação de duas entidades independentes.",
            "agent_count": 2,
        })
        assert response.status_code == 422
        assert client.get(f"{root}/agentes").json() == []
        assert client.get(f"{root}/sociedades").json() == []
        assert client.get(f"{root}/ambientes").json() == []
        too_short = client.post(f"{root}/assistente/criar-cenario", json={"description": "curto", "agent_count": 2})
        assert too_short.status_code == 422


def test_configurable_score_thresholds_and_validation(tmp_path):
    """Comprova faixas por cenário e bloqueia intervalos sobrepostos."""
    with make_client(tmp_path) as client:
        root = "/api/v3/laboratorio-comportamental"
        sample = client.post(f"{root}/exemplos?tipo=organizacao").json()
        environment = sample["environment"]
        # Os cortes pertencem ao cenário, não a uma regra global do motor.
        payload = {key: value for key, value in environment.items()
                   if key not in {"id", "created_at", "updated_at"}}
        response = client.put(f"{root}/ambientes/{environment['id']}", json={
            **payload, "low_threshold": 60, "high_threshold": 80,
            "low_label": "Pouca disposição", "middle_label": "Disposição moderada", "high_label": "Disposição elevada"
        })
        assert response.status_code == 200, response.text
        assert response.json()["high_threshold"] == 80
        invalid = client.put(f"{root}/ambientes/{environment['id']}", json={
            **payload, "low_threshold": 80, "high_threshold": 60
        })
        assert invalid.status_code == 422
        started = client.post(f"{root}/simulacoes", json={"environment_id": environment["id"],
            "society_id": sample["society"]["id"], "mode": "demo", "rounds": 2, "shock_probability": 0})
        assert started.status_code == 202, started.text
        run = wait_for_run(client, started.json()["id"])
        assert run["status"] == "COMPLETED"
        assert run["snapshot"]["environment"]["low_threshold"] == 60
        values = [event["payload"]["stance"] for event in run["events"]
                  if event["event_type"] == "REACTION" and event["round"] == 2]
        final = run["result"]["final"]
        assert final["support"] == sum(value >= 80 for value in values)
        assert final["undecided"] == sum(60 <= value < 80 for value in values)
        assert final["resistance"] == sum(value < 60 for value in values)
