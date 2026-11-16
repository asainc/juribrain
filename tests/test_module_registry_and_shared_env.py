"""Testes de extensibilidade e configuração com dados exclusivamente fictícios."""
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from applications.registry import mounted_applications
from backend.config import Settings, load_settings as load_core_settings
from applications.auditoria.backend.config import load_settings as load_audit_settings
from applications.chatbot.backend.config import load_settings as load_chatbot_settings
from backend.principal import create_app
from scripts.scaffold_application import create_scaffold


def test_all_modules_share_environment_file(monkeypatch, tmp_path):
    """A mesma configuração sintética chega aos três produtos originais."""
    example = tmp_path / 'synthetic.env'
    example.write_text('APP_ENV=local\nBRADESCO_IDENTIFICADOR=teste-sem-credencial\n'
                       'BRADESCO_SENHA=apenas-mock\nBRADESCO_QA_WORKFLOW_CODE=workflow-teste\n'
                       'BRADESCO_TEXT_MODEL=modelo-teste\n', encoding='utf-8')
    monkeypatch.setenv('APP_ENV_FILE', str(example))
    configs = [load_core_settings(), load_audit_settings(), load_chatbot_settings()]
    assert {config.bradesco_identificador.get_secret_value() for config in configs} == {'teste-sem-credencial'}
    assert {config.bradesco_senha.get_secret_value() for config in configs} == {'apenas-mock'}
    assert {config.bradesco_text_model for config in configs} == {'modelo-teste'}
    assert configs[0].bradesco_qa_workflow_code == configs[2].bradesco_qa_workflow_code == 'workflow-teste'


def test_corporate_module_is_unique():
    """Evita regressões que restabeleçam cópias da Bridge em cada pacote."""
    project = Path(__file__).resolve().parents[1]
    assert sorted(str(path.relative_to(project)) for path in project.rglob('gpt_bradesco.py')) == ['gpt_bradesco.py']
    assert not list((project / 'applications').glob('*/.env.example'))


def test_app_registry_and_behavior_route(tmp_path):
    """Valida que as APIs originais continuam montadas e Behavior está acessível."""
    mounts = mounted_applications()
    assert {(item.key, item.mount_path) for item in mounts} == {
        ('auditoria', '/services/auditoria'), ('chatbot', '/services/chatbot')}
    app = create_app(Settings(behavioral_lab_database_path=tmp_path / 'behavior.sqlite3'))
    with TestClient(app) as client:
        assert client.get('/api/v3/laboratorio-comportamental/configuracao').status_code == 200
        assert client.get('/api/v3/laboratorio-comportamental/agentes').json() == []
        assert client.get('/services/auditoria/api/v2/saude').status_code == 200
        assert client.get('/services/chatbot/api/v3/saude').status_code == 200


def test_scaffold_rejects_bad_name():
    """Não aceita atravessar diretórios ou sobrescrever outros projetos."""
    with pytest.raises(ValueError):
        create_scaffold('../fora', 'Falha simulada')


def test_scaffold_creates_testable_module(monkeypatch, tmp_path):
    """Gera o módulo em diretório temporário e verifica os contratos mínimos."""
    import importlib.util
    import scripts.scaffold_application as tool

    monkeypatch.setattr(tool, 'PROJECT_ROOT', tmp_path)
    paths = tool.create_scaffold('triagem', 'Triagem')
    assert len(paths) == 6
    assert all(path.is_file() for path in paths)
    assert (tmp_path / 'frontend/src/app/triagem/triagem-page.component.ts').is_file()
    assert b'@router.get("/saude")' in (tmp_path / 'applications/triagem/backend/router.py').read_bytes()
    with pytest.raises(FileExistsError):
        tool.create_scaffold('triagem', 'Triagem')
