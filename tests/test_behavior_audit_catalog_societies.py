"""Regressões do Behavior: entidades abertas, sociedades consistentes e trilha de decisão."""
from __future__ import annotations

import csv
import io
import time
from pathlib import Path

from fastapi.testclient import TestClient

from backend.config import Settings
from backend.principal import create_app

ROOT = '/api/v3/laboratorio-comportamental'


def _client(tmp_path: Path) -> TestClient:
    """Usa somente SQLite efêmero, sem serviços ou dados corporativos."""
    return TestClient(create_app(Settings(behavioral_lab_database_path=tmp_path / 'behavior-tests.sqlite3')))


def _completed(client: TestClient, run_id: str) -> dict:
    """Consulta estado terminal com limite explícito para evitar teste preso."""
    for _ in range(250):
        result = client.get(f'{ROOT}/simulacoes/{run_id}').json()
        if result['status'] in {'COMPLETED', 'FAILED', 'INTERRUPTED'}:
            return result
        time.sleep(.02)
    raise AssertionError('Simulação não terminou dentro do prazo de teste')


def test_custom_entity_catalog_and_custom_world(tmp_path):
    """Cadastro e persistência do tipo independem do navegador e de presets fixos."""
    with _client(tmp_path) as client:
        original = client.get(f'{ROOT}/tipos-entidade').json()
        assert any(row['value'] == 'PESSOA' and row['is_builtin'] for row in original)
        bad = client.post(f'{ROOT}/tipos-entidade', json={'value': 'with spaces', 'label': 'Inválido'})
        assert bad.status_code == 422
        custom = client.post(f'{ROOT}/tipos-entidade', json={'value': 'COOPERATIVA', 'label': 'Cooperativa fictícia'})
        assert custom.status_code == 201, custom.text
        assert client.post(f'{ROOT}/tipos-entidade', json={'value': 'COOPERATIVA', 'label': 'Repetido'}).status_code == 409
        profile = {'name': 'Cooperativa modelo', 'goal': 'Examinar cenários artificiais', 'entity_type': 'COOPERATIVA'}
        created = client.post(f'{ROOT}/agentes', json=profile)
        assert created.status_code == 201, created.text
        assert client.delete(f'{ROOT}/tipos-entidade/COOPERATIVA').status_code == 409
        world = {
            'name': 'Mundo fictício oceânico', 'world_type': 'Exploração marítima',
            'context': 'Experimento hipotético com agentes artificiais em uma ilha imaginária.',
            'decision': 'Introduzir uma estratégia colaborativa de coleta de energia sustentável.',
            'success_criterion': 'Observar como grupos simulados chegam a um acordo.'
        }
        new_world = client.post(f'{ROOT}/ambientes', json=world)
        assert new_world.status_code == 201, new_world.text
        assert new_world.json()['world_type'] == 'Exploração marítima'
        assert client.get(f'{ROOT}/ambientes').json()[0]['world_type'] == 'Exploração marítima'
        assert client.delete(f'{ROOT}/agentes/{created.json()["id"]}').status_code == 204
        assert client.delete(f'{ROOT}/tipos-entidade/COOPERATIVA').status_code == 204
        assert client.delete(f'{ROOT}/tipos-entidade/PESSOA').status_code == 409


def test_society_membership_crud_integrity_and_snapshots(tmp_path):
    """Editar uma sociedade não reescreve snapshots e impede cadastro inconsistente."""
    with _client(tmp_path) as client:
        world = client.post(f'{ROOT}/exemplos').json()
        society = world['society']
        agent_id = society['agent_ids'][0]
        assert client.delete(f'{ROOT}/agentes/{agent_id}').status_code == 409
        new_agent = client.post(f'{ROOT}/agentes', json={'name': 'Agente extra', 'goal': 'Ponderar alterações simuladas'})
        assert new_agent.status_code == 201
        payload = {'name': 'Nova sociedade sintética', 'description': 'Cenário sem pessoas reais',
                   'agent_ids': [new_agent.json()['id'], agent_id]}
        created = client.post(f'{ROOT}/sociedades', json=payload)
        assert created.status_code == 201, created.text
        run = client.post(f'{ROOT}/simulacoes', json={'environment_id': world['environment']['id'],
                           'society_id': created.json()['id'], 'mode': 'demo', 'rounds': 2,
                           'network_density': 1.0, 'uncertainty': 0, 'shock_probability': 0})
        assert run.status_code == 202, run.text
        before = _completed(client, run.json()['id'])
        assert before['status'] == 'COMPLETED'
        assert before['snapshot']['society']['agent_ids'] == payload['agent_ids']
        edited = client.put(f'{ROOT}/sociedades/{created.json()["id"]}', json={**payload, 'agent_ids': [agent_id]})
        assert edited.status_code == 200, edited.text
        after = client.get(f'{ROOT}/simulacoes/{run.json()["id"]}').json()
        assert after['snapshot']['society']['agent_ids'] == payload['agent_ids']
        revisions = client.get(f'{ROOT}/versoes/societies/{created.json()["id"]}').json()
        assert len(revisions) == 2
        assert client.delete(f'{ROOT}/agentes/{new_agent.json()["id"]}').status_code == 204
        assert client.delete(f'{ROOT}/sociedades/{created.json()["id"]}').status_code == 204


def test_demo_audit_traces_exact_reaction_inputs_and_export(tmp_path):
    """Cada mudança de posição registra o antes/depois e fatores calculados."""
    with _client(tmp_path) as client:
        example = client.post(f'{ROOT}/exemplos').json()
        config = {'environment_id': example['environment']['id'], 'society_id': example['society']['id'],
                  'mode': 'demo', 'rounds': 2, 'network_density': 1, 'shock_probability': 0,
                  'uncertainty': 0, 'seed': 11}
        created = client.post(f'{ROOT}/simulacoes', json=config)
        assert created.status_code == 202, created.text
        run = _completed(client, created.json()['id'])
        assert run['status'] == 'COMPLETED'
        events = [e for e in run['events'] if e['event_type'] == 'REACTION']
        assert len(events) == 12
        for event in events:
            payload = event['payload']
            trace = payload['decision_trace']
            assert trace['current_stance'] == payload['stance']
            assert trace['delta'] == payload['stance'] - trace['previous_stance']
            assert trace['changed'] is (trace['delta'] != 0)
            assert trace['source'] == 'REGRAS_DEMO'
            assert trace['calculation']['components']
            assert abs(trace['calculation']['raw_stance'] - sum([trace['previous_stance'],
                *trace['calculation']['components'].values()])) < 0.0002
            if event['round'] == 1:
                assert trace['first_round'] and trace['peer_signals'] == []
            else:
                assert not trace['first_round']
                assert trace['peer_signals']
        exported = client.get(f'{ROOT}/simulacoes/{run["id"]}/exportar?format=csv')
        assert exported.status_code == 200, exported.text
        rows = list(csv.DictReader(io.StringIO(exported.content.decode('utf-8-sig'))))
        assert len(rows) == len(events)
        assert 'trilha_decisao_json' in rows[0]
        report = client.get(f'{ROOT}/simulacoes/{run["id"]}/relatorio')
        assert 'Decisões por interação' in report.text
