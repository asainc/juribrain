"""Testes integrados do Behavior Intelligence sem dados ou serviços reais."""
from __future__ import annotations

import json
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from applications.behavior.backend.contracts import EnvironmentInput, MetricDefinition
from applications.behavior.backend.repository import LabRepository
from backend.config import Settings
from backend.principal import create_app

ROOT = '/api/v3/laboratorio-comportamental'


def completed(client: TestClient, endpoint: str, timeout: float = 10) -> dict:
    """Consulta o worker local; interrompe o teste ao exceder seu horizonte."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        response = client.get(endpoint)
        assert response.status_code == 200, response.text
        result = response.json()
        if result['status'] not in ('QUEUED', 'RUNNING'):
            return result
        time.sleep(.02)
    raise AssertionError('Execução não terminou no horizonte do teste.')


def fixture_world(client: TestClient) -> dict:
    """Cria uma população fictícia isolada por banco temporário."""
    response = client.post(f'{ROOT}/exemplos?tipo=mercado')
    assert response.status_code == 201, response.text
    return response.json()


def test_flexible_metrics_and_transcripts(tmp_path: Path):
    """Métricas de três tipos, conversas endereçadas, replay e relatório íntegros."""
    settings = Settings(behavioral_lab_database_path=tmp_path / 'behavior.sqlite3')
    with TestClient(create_app(settings)) as client:
        data = fixture_world(client)
        environment = data['environment']
        environment['metrics'] = [
            {'key': 'preco', 'label': 'Valor de referência', 'kind': 'number', 'minimum': 5, 'maximum': 75},
            {'key': 'aceita', 'label': 'Concordância', 'kind': 'boolean'},
            {'key': 'atitude', 'label': 'Atitude', 'kind': 'category', 'categories': ['Recusa', 'Negocia', 'Aceita']},
        ]
        response = client.put(f"{ROOT}/ambientes/{environment['id']}", json={key: value for key, value in environment.items() if key not in ("id", "created_at", "updated_at")})
        assert response.status_code == 200, response.text
        config = {'environment_id': environment['id'], 'society_id': data['society']['id'],
                  'rounds': 2, 'seed': 24, 'network_density': 1, 'shock_probability': 0,
                  'repetitions': 2, 'mode': 'demo', 'memory_window': 2}
        response = client.post(f'{ROOT}/simulacoes', json=config)
        assert response.status_code == 202, response.text
        run = completed(client, f"{ROOT}/simulacoes/{response.json()['id']}")
        assert run['status'] == 'COMPLETED', run['error_code']
        assert run['result']['engine_version'] == 'behavior-3.0'
        assert len(run['result']['metrics']) == 3, 'Não duplicar métricas no consolidado.'
        assert {item['kind'] for item in run['result']['metrics']} == {'number', 'boolean', 'category'}
        assert len([e for e in run['events'] if e['event_type'] == 'CONVERSATION']) > 0
        assert len([e for e in run['events'] if e['event_type'] == 'ENVIRONMENT_SNAPSHOT']) == 4
        assert len(run['result']['snapshot_sha256']) == 64
        for event in run['events']:
            if event['event_type'] != 'REACTION':
                continue
            metrics = event['payload']['metrics']
            assert 5 <= metrics['preco'] <= 75
            assert isinstance(metrics['aceita'], bool)
            assert metrics['atitude'] in {'Recusa', 'Negocia', 'Aceita'}
        report = client.get(f"{ROOT}/simulacoes/{run['id']}/relatorio")
        assert report.status_code == 200
        assert 'Resultados personalizados' in report.text
        assert 'Hash de configuração:' in report.text
        exported = client.get(f"{ROOT}/simulacoes/{run['id']}/exportar?format=csv")
        assert 'metricas_json' in exported.text
        calibration = client.post(f"{ROOT}/simulacoes/{run['id']}/calibracoes", json={
            'observed_mean': 54, 'source_description': 'Média agregada fictícia em teste local',
            'sample_size': 100, 'validated_by': 'Pessoa revisora fictícia'})
        assert calibration.status_code == 201, calibration.text
        assert calibration.json()['absolute_deviation'] == round(abs(run['result']['final']['mean_stance'] - 54), 3)
        assert len(client.get(f"{ROOT}/simulacoes/{run['id']}/calibracoes").json()) == 1
        drift = client.get(f"{ROOT}/simulacoes/{run['id']}/drift?threshold=12").json()
        assert drift['previous_run_id'] is None
        assert drift['flagged'] is None


def test_experiment_ab_and_sensitivity_persistence(tmp_path: Path):
    """Executa variantes reais (no motor demo), não apenas cria um registro visual."""
    settings = Settings(behavioral_lab_database_path=tmp_path / 'lab.sqlite3')
    with TestClient(create_app(settings)) as client:
        data = fixture_world(client)
        baseline = {'environment_id': data['environment']['id'], 'society_id': data['society']['id'],
                    'mode': 'demo', 'rounds': 2, 'repetitions': 2, 'seed': 37,
                    'network_density': 1, 'shock_probability': 0, 'uncertainty': 0.25}
        payload = {'name': 'Teste de alternativas fictícias',
                   'hypothesis': 'A mudança parametrizada altera o índice sintético médio.',
                   'baseline': baseline, 'variants': [
                       {'name': 'Incerteza maior', 'parameter_updates': {'uncertainty': 0.9}},
                       {'name': 'Aumento ilustrativo', 'variable_updates': {'preco': 'baixo'}, 'impact': 0.8},
                   ]}
        response = client.post(f'{ROOT}/experimentos', json=payload)
        assert response.status_code == 202, response.text
        experiment = completed(client, f"{ROOT}/experimentos/{response.json()['id']}")
        assert experiment['status'] == 'COMPLETED', experiment
        assert [v['name'] for v in experiment['result']['comparison']] == ['Base', 'Incerteza maior', 'Aumento ilustrativo']
        assert all(v['status'] == 'COMPLETED' for v in experiment['result']['comparison'])
        assert all(v['run_id'] for v in experiment['result']['comparison'])
        base, uncertain, impact = experiment['result']['comparison']
        assert impact['mean_stance'] > base['mean_stance'], 'Impacto explícito deve atuar no modo demo.'
        assert impact['delta_to_base'] == round(impact['mean_stance'] - base['mean_stance'], 3)
        assert experiment['payload']['snapshot']['society']['id'] == data['society']['id']
        assert len(client.get(f'{ROOT}/experimentos').json()) == 1
        # Após simular, alterações no cadastro não podem alterar o snapshot antigo.
        altered = {**data['environment'], 'name': 'Outro nome', 'context': 'Um novo contexto fictício inteiramente alterado.'}
        assert client.put(f"{ROOT}/ambientes/{data['environment']['id']}", json={key: value for key, value in altered.items() if key not in ("id", "created_at", "updated_at")}).status_code == 200
        assert experiment['payload']['snapshot']['environment']['name'] != altered['name']
        versions = client.get(f"{ROOT}/versoes/environments/{data['environment']['id']}")
        assert versions.status_code == 200
        assert [v['version'] for v in versions.json()] == [2, 1]
        previous_run = client.get(f"{ROOT}/simulacoes/{base['run_id']}").json()
        assert previous_run['snapshot']['environment']['name'] != altered['name']
        assert len(previous_run['result']['snapshot_sha256']) == 64


def test_limits_schema_and_batch_budget(tmp_path: Path):
    """Rejeita entradas inválidas e custo agregado acima do teto configurado."""
    with pytest.raises(ValueError):
        EnvironmentInput(name='Mundo de teste', context='Contexto fictício suficiente.',
            decision='Proposta fictícia completa.', success_criterion='Comparação ilustrativa',
            metrics=[{'key': 'mesmo', 'label': 'Primeiro'}, {'key': 'mesmo', 'label': 'Segundo'}])
    with pytest.raises(ValueError):
        MetricDefinition(key='classe', label='Classe', kind='category', categories=['repetido', 'repetido'])
    with TestClient(create_app(Settings(behavioral_lab_database_path=tmp_path / 'lab.sqlite3'))) as client:
        data = fixture_world(client)
        base = {'environment_id': data['environment']['id'], 'society_id': data['society']['id'],
                'mode': 'demo', 'rounds': 6, 'repetitions': 10}
        payload = {'name': 'Custo descontrolado', 'hypothesis': 'Comparação intencionalmente acima do limite.',
                   'baseline': base, 'variants': [{'name': 'A', 'parameter_updates': {'uncertainty': .5}}]}
        response = client.post(f'{ROOT}/experimentos', json=payload)
        assert response.status_code == 422
        invalid = {**payload, 'variants': [{'name': 'A', 'parameter_updates': {'invalid': .5}}]}
        assert client.post(f'{ROOT}/experimentos', json=invalid).status_code == 422
        assert client.get(f'{ROOT}/versoes/invalid/{data["environment"]["id"]}').status_code == 422


def test_persistent_queue_is_recoverable(tmp_path: Path):
    """Uma tarefa ainda não iniciada sobrevive ao reinício e é reencaminhada."""
    database = tmp_path / 'queue.sqlite3'
    with TestClient(create_app(Settings(behavioral_lab_database_path=database))) as client:
        world = fixture_world(client)
        repository = LabRepository(database)
        config = {'environment_id': world['environment']['id'], 'society_id': world['society']['id'],
                  'rounds': 1, 'repetitions': 1, 'seed': 42, 'mode': 'demo', 'network_density': .5,
                  'shock_probability': 0, 'shock_intensity': .2, 'uncertainty': .2,
                  'social_pressure': .5, 'temperature': .2, 'max_tokens_per_reaction': 420, 'memory_window': 4}
        frozen = {'environment': world['environment'], 'society': world['society'], 'agents': world['agents']}
        queued = repository.create_run(config, frozen)
        assert queued['status'] == 'QUEUED'
    with TestClient(create_app(Settings(behavioral_lab_database_path=database))) as recovered:
        result = completed(recovered, f"{ROOT}/simulacoes/{queued['id']}")
        assert result['status'] == 'COMPLETED'
        assert result['completed'] == 6


def test_authorized_agent_actions_change_only_allowlisted_world(tmp_path: Path):
    """Ações do agente modificam somente variáveis e valores permitidos pelo cenário."""
    with TestClient(create_app(Settings(behavioral_lab_database_path=tmp_path / 'actions.sqlite3'))) as client:
        world = fixture_world(client)
        environment = {key: value for key, value in world['environment'].items()
                       if key not in ('id', 'created_at', 'updated_at')}
        environment['variables']['negociacao'] = 'aberta'
        environment['enable_agent_actions'] = True
        environment['allowed_agent_effects'] = {'negociacao': ['aberta', 'em_dialogo', 'fechada']}
        saved = client.put(f"{ROOT}/ambientes/{world['environment']['id']}", json=environment)
        assert saved.status_code == 200, saved.text
        run_config = {'environment_id': world['environment']['id'], 'society_id': world['society']['id'],
                      'rounds': 4, 'repetitions': 3, 'seed': 42, 'mode': 'demo', 'network_density': 1}
        started = client.post(f'{ROOT}/simulacoes', json=run_config)
        assert started.status_code == 202, started.text
        result = completed(client, f"{ROOT}/simulacoes/{started.json()['id']}")
        assert result['status'] == 'COMPLETED', result.get('error_code')
        changes = [event for event in result['events'] if event['event_type'] == 'AGENT_ACTION']
        assert changes, 'O teste ilustrativo deve emitir alguma ação com esta semente.'
        assert {event['payload']['key'] for event in changes} == {'negociacao'}
        assert all(event['payload']['new_value'] in {'aberta', 'em_dialogo', 'fechada'} for event in changes)
        assert {event['payload']['repetition'] for event in changes} <= {1, 2, 3}
        # Uma alteração de ambiente definida por agente nunca modifica o snapshot original.
        assert result['snapshot']['environment']['variables']['negociacao'] == 'aberta'
        assert result['result']['total_reactions'] == 72


def test_drift_between_two_comparable_runs(tmp_path: Path):
    """Um alerta parametrizado compara execuções, sem declarar drift real."""
    with TestClient(create_app(Settings(behavioral_lab_database_path=tmp_path / 'drift.sqlite3'))) as client:
        world = fixture_world(client)
        config = {'environment_id': world['environment']['id'], 'society_id': world['society']['id'],
                  'mode': 'demo', 'rounds': 2, 'seed': 7, 'network_density': 1, 'shock_probability': 0}
        first = client.post(f'{ROOT}/simulacoes', json=config)
        first_run = completed(client, f"{ROOT}/simulacoes/{first.json()['id']}")
        time.sleep(.02)
        second = client.post(f'{ROOT}/simulacoes', json={**config, 'seed': 10})
        second_run = completed(client, f"{ROOT}/simulacoes/{second.json()['id']}")
        drift = client.get(f"{ROOT}/simulacoes/{second_run['id']}/drift?threshold=0").json()
        assert drift['previous_run_id'] == first_run['id']
        assert drift['absolute_difference'] >= 0
        assert drift['flagged'] is True
        assert 'não corresponde a validação estatística' in drift['method_note']
