"""Regressão do hub cível/trabalhista com documentos e respostas inteiramente sintéticos."""
from __future__ import annotations

import json
from io import BytesIO

import pymupdf
import pytest
from fastapi.testclient import TestClient

from applications.chatbot.backend.config import Settings
from applications.chatbot.backend.principal import create_app


def create_synthetic_pdf() -> bytes:
    """Produz um PDF pesquisável sem dados pessoais, casos ou processos reais."""
    pdf = pymupdf.open()
    page = pdf.new_page()
    page.insert_text(
        (50, 70),
        'AUDIENCIA prevista em 10/10/2026. O documento sintetico trata de audiencia, '
        'testemunha, manifestacao e prova. Toda informacao e ficticia para teste.',
        fontsize=10,
    )
    content = pdf.tobytes()
    pdf.close()
    return content


class SyntheticBridge:
    """Retorna um esquema controlado sem consumir serviços corporativos."""

    configured = True
    qa_configured = False

    def __init__(self, *, invalid_source: bool = False):
        self.calls: list[str] = []
        self.invalid_source = invalid_source

    def generate_text(self, prompt: str, *, max_tokens: int) -> str:
        self.calls.append(prompt)
        if 'PERGUNTA DO ADVOGADO' in prompt:
            return 'O documento de teste menciona audiencia (autos-teste.pdf, p. 1).'
        source = {"documento": "arquivo-ausente.pdf" if self.invalid_source else "autos-teste.pdf", "pagina": 99 if self.invalid_source else 1}
        return json.dumps({
            "processo": {"resumo": "Resumo de processo integralmente sintetico.", "partes": [],
                         "proximas_acoes_sugeridas": ["Verificar registro da audiencia"]},
            "linha_tempo": [{"titulo": "Audiência", "descricao": "Evento sintético", "documento": "autos-teste.pdf", "pagina": 1, "categoria": "audiencia"}],
            "agenda_documental": [{"tipo": "audiencia", "titulo": "Audiência referida", "descricao": "Conferir data expressa", "data_mencionada": "10/10/2026", "fonte": source}],
            "provas_e_lacunas": [{"tipo": "prova", "titulo": "Testemunha citada", "descricao": "Conferir documentalmente", "fonte": source}],
        }, ensure_ascii=False)


def create_synthetic_app(*, invalid_source: bool = False):
    """Substitui apenas a integração externa para preservar o pipeline real."""
    app = create_app(Settings(bradesco_text_model="deployment-ficticio", bradesco_prompt_max_chars=12000))
    bridge = SyntheticBridge(invalid_source=invalid_source)
    app.state.bridge = bridge
    app.state.process_intelligence.bridge = bridge
    return app, bridge


def analyze(client: TestClient, area: str = 'trabalhista'):
    return client.post(
        '/api/v3/ai-ready/analisar',
        data={'tipo_processo': area},
        files={'files': ('autos-teste.pdf', BytesIO(create_synthetic_pdf()), 'application/pdf')},
    )


def test_hub_extracts_agenda_evidence_and_sources_in_labor_context() -> None:
    app, bridge = create_synthetic_app()
    with TestClient(app) as client:
        response = analyze(client)
        assert response.status_code == 200, response.text
        data = response.json()
        assert data['tipo_processo'] == 'trabalhista'
        assert data['agenda_documental'][0]['fonte'] == {'documento': 'autos-teste.pdf', 'pagina': 1, 'trecho': ''}
        assert data['agenda_documental'][0]['status_verificacao'] == 'conferir_nos_autos'
        assert data['provas_e_lacunas'][0]['tipo'] == 'prova'
        assert any('trabalhista' in prompt for prompt in bridge.calls)
        assert 'vencimento' not in data['agenda_documental'][0]

        workspace = data['workspace_id']
        search = client.get(f'/api/v3/ai-ready/{workspace}/buscar', params={'q': 'audiência testemunha'})
        assert search.status_code == 200
        hit = search.json()['resultados'][0]
        assert hit['documento'] == 'autos-teste.pdf' and hit['pagina'] == 1
        assert 'AUDIENCIA' in hit['trecho']

        answer = client.post('/api/v3/ai-ready/perguntar-autos', json={'workspace_id': workspace, 'pergunta': 'Qual audiencia foi citada?'})
        assert answer.status_code == 200
        assert 'p. 1' in answer.json()['resposta']
        assert answer.json()['fontes'][0]['pagina'] == 1
        assert any('PÁGINAS RECUPERADAS' in prompt for prompt in bridge.calls)

        assert client.delete(f'/api/v3/ai-ready/{workspace}').status_code == 204
        expired = client.get(f'/api/v3/ai-ready/{workspace}/buscar', params={'q': 'audiencia'})
        assert expired.status_code == 404


def test_hub_rejects_invalid_area_and_disregards_unverifiable_sources() -> None:
    app, _ = create_synthetic_app(invalid_source=True)
    with TestClient(app) as client:
        bad_area = analyze(client, 'penal')
        assert bad_area.status_code == 422
        valid = analyze(client, 'civel')
        assert valid.status_code == 200
        assert valid.json()['tipo_processo'] == 'civel'
        assert valid.json()['agenda_documental'] == []
        assert valid.json()['provas_e_lacunas'] == []


def test_hub_rejects_duplicate_filenames_to_preserve_source_identity() -> None:
    app, _ = create_synthetic_app()
    with TestClient(app) as client:
        body = client.post(
            '/api/v3/ai-ready/analisar',
            data={'tipo_processo': 'civel'},
            files=[('files', ('autos-teste.pdf', create_synthetic_pdf(), 'application/pdf')),
                   ('files', ('autos-teste.pdf', create_synthetic_pdf(), 'application/pdf'))],
        )
        assert body.status_code == 422
        assert body.json()['code'] == 'DOCUMENTOS_DUPLICADOS'


def test_hub_question_without_matching_pages_does_not_call_generation() -> None:
    app, bridge = create_synthetic_app()
    with TestClient(app) as client:
        response = analyze(client)
        workspace = response.json()['workspace_id']
        previous_calls = len(bridge.calls)
        question = client.post('/api/v3/ai-ready/perguntar-autos', json={'workspace_id': workspace, 'pergunta': 'Contratação de foguetes orbitais?'})
        assert question.status_code == 200
        assert question.json()['fontes'] == []
        assert len(bridge.calls) == previous_calls
