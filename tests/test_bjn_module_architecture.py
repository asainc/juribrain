"""Garantias estruturais após separação do BJN (dados somente sintéticos)."""
from pathlib import Path

from fastapi.testclient import TestClient

from applications.bjn.backend.module import BjnModule
from applications.behavior.backend.module import BehaviorModule
from applications.registry import api_extensions
from backend.config import Settings
from backend.principal import create_app
from backend.services.bradesco_bridge import BradescoBridgeClient


def test_all_products_live_under_applications():
    """Evita que regras BJN voltem para a pasta compartilhada do host."""
    root = Path(__file__).resolve().parents[1]
    for name in ('bjn', 'behavior', 'auditoria', 'chatbot'):
        assert (root / 'applications' / name / 'backend').is_dir()
    assert not list((root / 'backend' / 'services').glob('bjn_*.py'))
    assert not list((root / 'backend' / 'routers').glob('bjn*.py'))
    assert sorted(path.relative_to(root).as_posix() for path in root.rglob('gpt_bradesco.py')) == ['gpt_bradesco.py']
    assert not list((root / 'applications').glob('*/.env'))


def test_bjn_module_uses_shared_extension_contract(tmp_path):
    """BJN e Behavior são carregados sem importar serviços BJN no host."""
    settings = Settings(
        bjn_database_path=tmp_path / 'bjn.sqlite3',
        bjn_upload_directory=tmp_path / 'uploads',
        behavioral_lab_database_path=tmp_path / 'behavior.sqlite3',
    )
    bridge = BradescoBridgeClient(settings)
    modules = api_extensions(settings, bridge)
    assert [module.key for module in modules] == ['bjn', 'behavior']
    assert isinstance(modules[0], BjnModule)
    assert isinstance(modules[1], BehaviorModule)
    assert modules[0].bridge is modules[1].simulator.bridge


def test_bjn_http_routes_kept_unchanged(tmp_path):
    """Preserva questionário, catálogo e configuração de demandas no /api/v3."""
    settings = Settings(
        bjn_database_path=tmp_path / 'bjn.sqlite3',
        bjn_upload_directory=tmp_path / 'uploads',
        behavioral_lab_database_path=tmp_path / 'behavior.sqlite3',
    )
    with TestClient(create_app(settings)) as client:
        schema = client.get('/api/v3/bjn/questionario')
        assert schema.status_code == 200
        assert schema.json()['questions']
        catalog = client.get('/api/v3/bjn/catalogo')
        assert catalog.status_code == 200
        assert catalog.json()['total'] == 152
        config = client.get('/api/v3/bjn/demandas/configuracao')
        assert config.status_code == 200
        assert 'department_options' in config.json()
        assert client.get('/api/v3/saude').status_code == 200
