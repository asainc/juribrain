"""API do Behavior: CRUD, simulação, auditoria e exportação."""
from __future__ import annotations

import csv
import io
import json
import asyncio
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from fastapi import APIRouter, File, Query, Request, UploadFile
from fastapi.responses import Response, StreamingResponse
from pydantic import ValidationError

from applications.behavior.backend.contracts import AgentInput, EnvironmentInput, SimulationInput, SocietyInput, ExperimentInput, CalibrationInput
from applications.behavior.backend.repository import LabRepository
from applications.behavior.backend.simulator import LabSimulator
from applications.behavior.backend.experiments import ExperimentOrchestrator
from applications.behavior.backend.generator import ScenarioRequest, ScenarioGenerator
from backend.errors import ServiceError

router = APIRouter(prefix="/laboratorio-comportamental", tags=["Behavior"])

# A fila é propriedade da aplicação. O limite de dois workers evita custos e
# consumo de rede sem controle; cada execução conserva um snapshot próprio.
EXECUTOR_WORKERS = 2
CSV_CORE_COLUMNS = ["name", "entity_type", "group", "goal", "communication_style", "initial_stance", "influence", "susceptibility"]


def _repository(request: Request) -> LabRepository:
    return request.app.state.behavioral_lab_repository


def _validate_society(repository: LabRepository, society: SocietyInput) -> None:
    found = {agent["id"] for agent in repository.list_items("agents")}
    if missing := set(society.agent_ids) - found:
        raise ServiceError(f"A sociedade referencia {len(missing)} agente(s) inexistente(s).", 422, code="LAB_AGENT_REFERENCE_INVALID")


@router.get("/configuracao")
def configuration(request: Request) -> dict:
    """Retorna somente status técnico, sem expor deployment ou credenciais."""
    bridge = request.app.state.bridge
    settings = request.app.state.settings
    return {"bridge_available": bridge.configured, "bridge_status": bridge.text_generator_status()["code"],
            "demo_available": settings.environment == "local" and settings.behavioral_lab_demo_enabled,
            "max_agents": 30, "max_rounds": 6, "max_repetitions": 10, "max_model_calls": settings.behavioral_lab_max_calls,
            "warning": "Resultados sintéticos não substituem pesquisa com clientes nem validação jurídica/compliance."}


@router.post("/exemplos", status_code=201)
def create_example(request: Request, tipo: str = Query(default="comunidade", pattern="^(comunidade|mercado|organizacao)$")) -> dict:
    """Cria dataset estritamente fictício para testar o fluxo local de ponta a ponta."""
    settings = request.app.state.settings
    if settings.environment != "local" or not settings.behavioral_lab_demo_enabled:
        raise ServiceError("A criação de demonstrações está restrita ao ambiente local.", 403, code="LAB_DEMO_DISABLED")
    repository = _repository(request)
    # Exemplos inteiramente inventados, sem reproduzir perfis de pessoas reais.
    catalog = {
        "comunidade": {
            "title": "Mobilidade em cidade fictícia",
            "context": "Cidade imaginária avalia alterar a frequência de ônibus e criar uma linha noturna. Moradores, comércio e gestão pública são fictícios.",
            "decision": "Implementar um teste temporário de novas rotas, incluindo atendimento ao público e acessibilidade.",
            "target": "Apoiar a mudança nas rotas de transporte",
            "criterion": "Examinar como grupos artificiais reagem ao piloto de mobilidade.",
            "roles": [("Morador universitário", "PESSOA", "Moradores", "Reduzir tempo de deslocamento para estudar", 78),
                      ("Moradora idosa", "PESSOA", "Moradores", "Preservar acessibilidade e clareza das rotas", 38),
                      ("Trabalhador noturno", "PESSOA", "Moradores", "Dispor de transporte seguro na madrugada", 82),
                      ("Comércio local", "EMPRESA", "Economia local", "Manter circulação de clientes perto das lojas", 50),
                      ("Associação comunitária", "ORGANIZACAO", "Sociedade civil", "Dialogar com a comunidade e avaliar impacto social", 54),
                      ("Gestão municipal fictícia", "GOVERNO", "Instituições", "Equilibrar custos, acesso e prestação de contas", 61)],
            "variables": {"orçamento": "restrito", "linha_noturna": "proposta", "comunicação": "reuniões públicas"},
            "events": [{"round": 2, "name": "Anúncio de subsídio", "description": "Uma verba fictícia amplia o orçamento disponível para o piloto.", "impact": .35, "variable_updates": {"orçamento": "ampliado"}}],
        },
        "mercado": {
            "title": "Lançamento de produto fictício",
            "context": "Um mercado inventado testa a aceitação de um serviço digital opcional, sem dados de consumidores reais.",
            "decision": "Lançar um plano de assinatura piloto, com demonstração gratuita e cancelamento simples.",
            "target": "Experimentar o novo serviço de assinatura",
            "criterion": "Observar objeções e mudanças de interesse dos perfis simulados.",
            "roles": [("Pessoa pragmática", "PESSOA", "Consumidores", "Resolver tarefas de maneira simples", 68),
                      ("Pessoa preocupada com preço", "PESSOA", "Consumidores", "Evitar mensalidades desnecessárias", 25),
                      ("Pessoa entusiasta", "PESSOA", "Consumidores", "Experimentar novas funcionalidades", 87),
                      ("Parceiro comercial", "EMPRESA", "Mercado", "Identificar oportunidades sem risco operacional alto", 64),
                      ("Entidade de defesa fictícia", "ORGANIZACAO", "Instituições", "Priorizar informação clara e liberdade de escolha", 48),
                      ("Assistente simulado", "AGENTE_IA", "Tecnologia", "Explicar corretamente as características do serviço", 71)],
            "variables": {"preço": "baixo", "teste_gratuito": "sim", "cancelamento": "simples"},
            "events": [{"round": 2, "name": "Reajuste anunciado", "description": "A mensalidade estimada do serviço sofre aumento hipotético.", "impact": -.55, "variable_updates": {"preço": "médio"}}],
        },
        "organizacao": {
            "title": "Mudança de rotina organizacional",
            "context": "Organização fictícia considera adotar horários flexíveis de trabalho com objetivos de produtividade e colaboração.",
            "decision": "Realizar um piloto voluntário de horários flexíveis por oito semanas.",
            "target": "Apoiar o piloto de horários flexíveis",
            "criterion": "Observar cooperação, preocupações e resistência simuladas à mudança.",
            "roles": [("Analista focado", "PESSOA", "Equipes", "Ter janelas longas de concentração", 77),
                      ("Colaboradora colaborativa", "PESSOA", "Equipes", "Garantir comunicação e proximidade da equipe", 52),
                      ("Gestor de operação", "PESSOA", "Liderança", "Manter previsibilidade de entregas", 42),
                      ("RH fictício", "ORGANIZACAO", "Institucional", "Promover uma experiência acessível a todos", 73),
                      ("Fornecedor terceirizado", "EMPRESA", "Parceiros", "Coordenar escalas e canais de suporte", 47),
                      ("Facilitador digital", "AGENTE_IA", "Tecnologia", "Ajudar a esclarecer regras e processos", 64)],
            "variables": {"horários": "flexíveis", "canais": "assíncronos", "acompanhamento": "quinzenal"},
            "events": [{"round": 2, "name": "Nova necessidade operacional", "description": "Uma demanda fictícia exige colaboração síncrona em dois dias da semana.", "impact": -.25, "variable_updates": {"canais": "híbridos"}}],
        },
    }
    selected = catalog[tipo]
    profiles = [{"name": name, "entity_type": entity, "group": group, "goal": goal,
                 "initial_stance": stance, "characteristics": {"perfil": "inteiramente fictício", "motivação": goal}}
                for name, entity, group, goal, stance in selected["roles"]]
    agents = [repository.save_item("agents", AgentInput.model_validate(profile).model_dump()) for profile in profiles]
    environment = repository.save_item("environments", EnvironmentInput(
        name=selected["title"], context=selected["context"], decision=selected["decision"],
        target_behavior=selected["target"], success_criterion=selected["criterion"],
        variables=selected["variables"], events=selected["events"]).model_dump())
    society = repository.save_item("societies", SocietyInput(
        name=f"Sociedade · {tipo}", description="Perfis artificiais sem correspondência com indivíduos reais.",
        agent_ids=[agent["id"] for agent in agents]).model_dump())
    return {"agents": agents, "environment": environment, "society": society}


@router.post("/assistente/criar-cenario", status_code=201)
def generate_scenario(body: ScenarioRequest, request: Request) -> dict:
    """Gera um conjunto fictício com IA e só persiste depois de validar tudo.

    Uma chamada de geração não executa simulação nem implica validação dos
    perfis sugeridos. O usuário deve revisar o mundo e os agentes gerados.
    """
    bridge = request.app.state.bridge
    if not bridge.configured:
        raise ServiceError("A geração assistida exige gpt_bradesco configurado. Use o editor manual ou o CSV.",
                           503, code="LAB_BRIDGE_UNAVAILABLE")
    proposal = ScenarioGenerator(bridge).propose(body)
    result = _repository(request).create_scenario_bundle(
        [agent.model_dump() for agent in proposal.agents], proposal.environment.model_dump(),
        proposal.society_name, proposal.society_description,
    )
    return result


@router.get("/agentes")
def list_agents(request: Request) -> list[dict]:
    return _repository(request).list_items("agents")


@router.post("/agentes", status_code=201)
def create_agent(body: AgentInput, request: Request) -> dict:
    return _repository(request).save_item("agents", body.model_dump())


@router.put("/agentes/{agent_id}")
def update_agent(agent_id: str, body: AgentInput, request: Request) -> dict:
    return _repository(request).save_item("agents", body.model_dump(), agent_id)


@router.delete("/agentes/{agent_id}", status_code=204)
def delete_agent(agent_id: str, request: Request) -> Response:
    _repository(request).delete_item("agents", agent_id)
    return Response(status_code=204)


def _csv_text(value: object) -> str:
    """Neutraliza células que poderiam ser interpretadas como fórmulas ao abrir CSV."""
    raw = str(value)
    return "'" + raw if raw.lstrip().startswith(("=", "+", "-", "@", "\t", "\r")) else raw


@router.get("/agentes/exportar-csv")
def export_agents(request: Request) -> Response:
    agents = _repository(request).list_items("agents")
    extra = sorted({column for agent in agents for column in agent["characteristics"]})
    columns = CSV_CORE_COLUMNS + extra
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=columns)
    writer.writeheader()
    for agent in agents:
        row = {column: _csv_text(agent.get(column, "")) for column in CSV_CORE_COLUMNS}
        row.update({column: _csv_text(agent["characteristics"].get(column, "")) for column in extra})
        writer.writerow(row)
    return Response("\ufeff" + buffer.getvalue(), media_type="text/csv; charset=utf-8",
                    headers={"Content-Disposition": 'attachment; filename="agentes_sinteticos.csv"'})


@router.post("/agentes/importar-csv", status_code=201)
async def import_agents(request: Request, file: UploadFile = File(...)) -> dict:
    """Importa até 30 registros de CSV UTF-8 com colunas dinâmicas de perfil."""
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise ServiceError("Selecione um arquivo .csv codificado em UTF-8.", 422, code="LAB_INVALID_CSV")
    contents = await file.read(256 * 1024 + 1)
    if len(contents) > 256 * 1024:
        raise ServiceError("O CSV deve ter no máximo 256 KB.", 413, code="LAB_CSV_TOO_LARGE")
    try:
        text = contents.decode("utf-8-sig")
        reader = csv.DictReader(io.StringIO(text))
        if not reader.fieldnames or len(reader.fieldnames) != len(set(reader.fieldnames)) or not {"name", "goal"}.issubset(set(reader.fieldnames)):
            raise ValueError("Cabeçalhos name e goal são obrigatórios e não podem existir duplicatas.")
        if len(reader.fieldnames) > 32:
            raise ValueError("O CSV excede o limite de 32 colunas.")
        rows = list(reader)
        if not 1 <= len(rows) <= 30:
            raise ValueError("Importe entre 1 e 30 linhas por arquivo.")
        prepared = []
        for index, row in enumerate(rows, start=2):
            if None in row or any(value is None for value in row.values()):
                raise ValueError(f"Linha {index}: quantidade de colunas inválida.")
            extra = {key: value or "" for key, value in row.items() if key not in CSV_CORE_COLUMNS and value}
            prepared.append(AgentInput.model_validate({
                "name": row["name"], "goal": row["goal"],
                "entity_type": row.get("entity_type") or "PESSOA", "group": row.get("group") or "Geral",
                "communication_style": row.get("communication_style") or "objetivo",
                "initial_stance": row.get("initial_stance") or 50,
                "influence": row.get("influence") or .5, "susceptibility": row.get("susceptibility") or .5,
                "characteristics": extra,
            }))
    except (UnicodeDecodeError, ValueError, ValidationError, csv.Error) as exc:
        raise ServiceError("CSV inválido. Verifique UTF-8, campos obrigatórios e limites de valores. " + str(exc)[:220], 422, code="LAB_INVALID_CSV") from None
    repository = _repository(request)
    agents = [repository.save_item("agents", item.model_dump()) for item in prepared]
    return {"imported": len(agents), "agents": agents}


@router.get("/ambientes")
def list_environments(request: Request) -> list[dict]:
    return _repository(request).list_items("environments")


@router.post("/ambientes", status_code=201)
def create_environment(body: EnvironmentInput, request: Request) -> dict:
    return _repository(request).save_item("environments", body.model_dump())


@router.put("/ambientes/{environment_id}")
def update_environment(environment_id: str, body: EnvironmentInput, request: Request) -> dict:
    return _repository(request).save_item("environments", body.model_dump(), environment_id)


@router.delete("/ambientes/{environment_id}", status_code=204)
def delete_environment(environment_id: str, request: Request) -> Response:
    _repository(request).delete_item("environments", environment_id)
    return Response(status_code=204)


@router.get("/sociedades")
def list_societies(request: Request) -> list[dict]:
    return _repository(request).list_items("societies")


@router.post("/sociedades", status_code=201)
def create_society(body: SocietyInput, request: Request) -> dict:
    repository = _repository(request)
    _validate_society(repository, body)
    return repository.save_item("societies", body.model_dump())


@router.put("/sociedades/{society_id}")
def update_society(society_id: str, body: SocietyInput, request: Request) -> dict:
    repository = _repository(request)
    _validate_society(repository, body)
    return repository.save_item("societies", body.model_dump(), society_id)


@router.delete("/sociedades/{society_id}", status_code=204)
def delete_society(society_id: str, request: Request) -> Response:
    _repository(request).delete_item("societies", society_id)
    return Response(status_code=204)


@router.get("/simulacoes")
def list_runs(request: Request) -> list[dict]:
    return _repository(request).list_runs()


@router.post("/simulacoes", status_code=202)
def start_run(body: SimulationInput, request: Request) -> dict:
    """Congela o experimento e devolve ID; frontend acompanha por polling."""
    repository = _repository(request)
    settings = request.app.state.settings
    if body.mode == "demo" and not (settings.environment == "local" and settings.behavioral_lab_demo_enabled):
        raise ServiceError("O modo demonstrativo somente é permitido em desenvolvimento local.", 403, code="LAB_DEMO_DISABLED")
    if body.mode == "bridge" and not request.app.state.bridge.configured:
        raise ServiceError("Configure a geração de texto do gpt_bradesco no backend antes de iniciar o modo IA.", 503, code="LAB_BRIDGE_UNAVAILABLE")
    environment = repository.get_item("environments", body.environment_id)
    society = repository.get_item("societies", body.society_id)
    agents = [repository.get_item("agents", item_id) for item_id in society["agent_ids"]]
    # Evita uma execução em que acontecimentos importantes ficariam silenciosamente fora do horizonte.
    if any(event["round"] > body.rounds for event in environment.get("events", [])):
        raise ServiceError("Há acontecimentos programados para depois da última rodada. Aumente as rodadas ou edite o ambiente.",
                           422, code="LAB_EVENT_OUT_OF_HORIZON")
    calls = len(agents) * body.rounds * body.repetitions
    if calls > settings.behavioral_lab_max_calls:
        raise ServiceError(f"O experimento exige {calls} reações e o limite configurado é {settings.behavioral_lab_max_calls}.", 422, code="LAB_CALL_LIMIT")
    snapshot = {"environment": environment, "society": society, "agents": agents}
    run = repository.create_run(body.model_dump(), snapshot)
    request.app.state.behavioral_lab_executor.submit(request.app.state.behavioral_lab_simulator.execute, run["id"])
    return run


@router.get("/simulacoes/{run_id}")
def get_run(run_id: str, request: Request) -> dict:
    return _repository(request).get_run(run_id, include_events=True)


@router.get("/simulacoes/{run_id}/eventos")
def run_events(run_id: str, request: Request, after: int = Query(default=0, ge=0)) -> dict:
    return {"events": _repository(request).events(run_id, after)}


@router.post("/simulacoes/{run_id}/pausar")
def pause_run(run_id: str, request: Request) -> dict:
    """Solicita pausa efetiva no próximo checkpoint, sem perder reações anteriores."""
    _repository(request).pause(run_id)
    return {"status": "PAUSE_REQUESTED"}


@router.post("/simulacoes/{run_id}/retomar")
def resume_run(run_id: str, request: Request) -> dict:
    """Remove o bloqueio cooperativo e preserva o experimento original."""
    _repository(request).resume(run_id)
    return {"status": "RESUMED"}


@router.post("/simulacoes/{run_id}/cancelar")
def cancel_run(run_id: str, request: Request) -> dict:
    _repository(request).cancel(run_id)
    return {"status": "CANCELLATION_REQUESTED"}


@router.get("/simulacoes/{run_id}/exportar")
def export_run(run_id: str, request: Request, format: str = Query(default="json", pattern="^(json|csv)$")) -> Response:
    """Exporta snapshot, decisões, eventos, metadados e limitações do experimento."""
    run = _repository(request).get_run(run_id, include_events=True)
    if format == "json":
        return Response(json.dumps(run, ensure_ascii=False, indent=2), media_type="application/json",
                        headers={"Content-Disposition": f'attachment; filename="simulacao_{run_id}.json"'})
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["rodada", "agente_id", "agente", "posicao", "emocao", "acao", "mensagem", "justificativa", "modo", "semente", "simulacao", "metricas_json"])
    for event in run["events"]:
        if event["event_type"] == "REACTION":
            reaction = event["payload"]
            writer.writerow([reaction["round"], reaction["agent_id"], _csv_text(reaction["agent_name"]), reaction["stance"],
                             _csv_text(reaction["emotion"]), _csv_text(reaction["action"]), _csv_text(reaction["message"]),
                             _csv_text(reaction["reason"]), run["mode"], run["configuration"]["seed"], reaction.get("repetition", 1), _csv_text(json.dumps(reaction.get("metrics", {}), ensure_ascii=False))])
    return Response("\ufeff" + buffer.getvalue(), media_type="text/csv; charset=utf-8",
                    headers={"Content-Disposition": f'attachment; filename="simulacao_{run_id}.csv"'})


@router.get("/experimentos")
def list_experiments(request: Request) -> list[dict]:
    """Biblioteca de experimentos com configuração e resultado persistentes."""
    return _repository(request).list_experiments()


@router.get("/experimentos/{experiment_id}")
def get_experiment(experiment_id: str, request: Request) -> dict:
    return _repository(request).get_experiment(experiment_id)


@router.post("/experimentos", status_code=202)
def create_experiment(body: ExperimentInput, request: Request) -> dict:
    """Executa cenário base e variantes com população/semente comuns.

    O orçamento agregado é conferido antes de persistir o plano para reduzir
    surpresas de custo. Todos os dados pessoais devem ser fictícios.
    """
    settings = request.app.state.settings
    repo = _repository(request)
    config = body.baseline
    if config.mode == 'demo' and not (settings.environment == 'local' and settings.behavioral_lab_demo_enabled):
        raise ServiceError('Modo demonstrativo desabilitado.', 403, code='LAB_DEMO_DISABLED')
    if config.mode == 'bridge' and not request.app.state.bridge.configured:
        raise ServiceError('Bridge corporativa não configurada.', 503, code='LAB_BRIDGE_UNAVAILABLE')
    environment = repo.get_item('environments', config.environment_id)
    society = repo.get_item('societies', config.society_id)
    _validate_society(repo, SocietyInput.model_validate({key: society[key] for key in ("name", "description", "agent_ids")}))
    if any(event['round'] > config.rounds for event in environment.get('events', [])):
        raise ServiceError('Há eventos fora das rodadas configuradas.', 422, code='LAB_EVENT_OUT_OF_HORIZON')
    per_variant = len(society['agent_ids']) * config.rounds * config.repetitions
    total_calls = per_variant * (1 + len(body.variants))
    if per_variant > settings.behavioral_lab_max_calls or total_calls > settings.behavioral_lab_max_calls * 3:
        raise ServiceError(f'Orçamento excedido: {total_calls} reações previstas. Reduza agentes, rodadas ou variantes.',
                           422, code='LAB_EXPERIMENT_BUDGET')
    data = body.model_dump()
    # Congela perfis e ambiente antes de entrar na fila: mudanças posteriores
    # no cadastro não alteram a interpretação do experimento.
    data['snapshot'] = {'environment': environment, 'society': society,
                        'agents': [repo.get_item('agents', agent_id) for agent_id in society['agent_ids']]}
    data['budget'] = {'model_reactions': total_calls,
                      'maximum_output_tokens': total_calls * config.max_tokens_per_reaction,
                      'is_estimate': True, 'includes_input_tokens': False}
    record = repo.create_experiment(data)
    executor = request.app.state.behavioral_lab_executor
    executor.submit(ExperimentOrchestrator(repo, request.app.state.behavioral_lab_simulator).execute, record['id'])
    return record


@router.post("/simulacoes/{run_id}/calibracoes", status_code=201)
def calibrate_run(run_id: str, body: CalibrationInput, request: Request) -> dict:
    """Compara uma média observada agregada com a média sintética.

    Somente a referência resumida e a fonte textual são registradas. A validação
    de origem, privacidade e representatividade é responsabilidade humana.
    """
    repo = _repository(request)
    run = repo.get_run(run_id)
    if run['status'] != 'COMPLETED' or not run.get('result') or not run['result'].get('final'):
        raise ServiceError('Apenas simulações concluídas podem ser comparadas.', 409, code='LAB_RUN_NOT_COMPLETED')
    predicted = float(run['result']['final']['mean_stance'])
    payload = {**body.model_dump(), 'simulated_mean': predicted,
               'absolute_deviation': round(abs(predicted - body.observed_mean), 3),
               'metric': 'stance', 'interpretation': 'Divergência descritiva; uma única referência não valida o simulador.'}
    return repo.add_calibration(run_id, payload)


@router.get("/simulacoes/{run_id}/calibracoes")
def list_calibrations(run_id: str, request: Request) -> list[dict]:
    return _repository(request).list_calibrations(run_id)


@router.get("/simulacoes/{run_id}/stream")
async def stream_run(run_id: str, request: Request, after: int = Query(default=0, ge=0)):
    """Canal SSE opcional; Angular preserva polling quando não há streaming.

    O cliente pode reconectar usando o último número de sequência recebido.
    """
    repo = _repository(request)
    repo.get_run(run_id)

    async def events():
        last = after
        for _ in range(900):
            if await request.is_disconnected():
                return
            records = repo.events(run_id, last)
            for record in records:
                last = record['sequence']
                yield f'id: {last}\nevent: lab-event\ndata: {json.dumps(record, ensure_ascii=False)}\n\n'
            status = repo.get_run(run_id)['status']
            if status not in ('QUEUED', 'RUNNING', 'PAUSE_REQUESTED', 'PAUSED') and not records:
                yield f'event: completed\ndata: {json.dumps({"status": status})}\n\n'
                return
            if not records:
                yield ': heartbeat\n\n'
            await asyncio.sleep(1)

    return StreamingResponse(events(), media_type='text/event-stream', headers={'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no'})


@router.get("/simulacoes/{run_id}/relatorio")
def report_run(run_id: str, request: Request) -> Response:
    """Relatório textual simples para auditoria sem incluir prompts ou segredos."""
    run = _repository(request).get_run(run_id)
    summary = run.get('result') or {}
    world = run['snapshot']['environment']
    final = summary.get('final') or {}
    metrics = summary.get('metrics') or []
    lines = [f'# Behavior — {world["name"]}', '', f'Identificador: {run_id}',
             f'Status: {run["status"]}', f'Modo: {run["mode"]}',
             f'Reações registradas: {run["completed"]}/{run["total"]}',
             f'Semente: {run["configuration"]["seed"]}',
             f'Pontuação sintética final (média): {final.get("mean_stance", "Indisponível")}', '',
             '## Resultados personalizados']
    for metric in metrics:
        lines.append(f'- {metric["label"]}: {json.dumps(metric, ensure_ascii=False)}')
    lines += ['', '## Rastreabilidade',
              f'Hash de configuração: {summary.get("snapshot_sha256") or "Indisponível"}',
              f'Hash do prompt: {summary.get("prompt_sha256") or "Não aplicável"}', '',
              '## Limitações',
              'Simulações não são amostras de clientes reais; os resultados não demonstram causalidade, validade externa ou representatividade.']
    return Response('\n'.join(lines) + '\n', media_type='text/markdown; charset=utf-8',
                    headers={'Content-Disposition': f'attachment; filename="behavior_{run_id}.md"'})


@router.get("/versoes/{kind}/{item_id}")
def item_versions(kind: str, item_id: str, request: Request) -> list[dict]:
    """Expõe versões dos cadastros sem permitir gravação retroativa."""
    if kind not in ('agents', 'environments', 'societies'):
        raise ServiceError('Categoria de versões inválida.', 422, code='LAB_INVALID_KIND')
    return _repository(request).item_versions(kind, item_id)


@router.get("/simulacoes/{run_id}/drift")
def drift_check(run_id: str, request: Request, threshold: float = Query(default=10, ge=0, le=100)) -> dict:
    """Alerta operacional descritivo entre runs, sem teste de significância."""
    repository = _repository(request)
    current = repository.get_run(run_id)
    if current['status'] != 'COMPLETED' or not current['result'] or not current['result'].get('final'):
        raise ServiceError('Execute e conclua o experimento antes da comparação.', 409, code='LAB_RUN_NOT_COMPLETED')
    previous = None
    for candidate in repository.list_runs():
        if candidate['id'] == run_id or candidate['status'] != 'COMPLETED' or candidate['created_at'] >= current['created_at']:
            continue
        full = repository.get_run(candidate['id'])
        if full['snapshot']['environment']['id'] == current['snapshot']['environment']['id']:
            if previous is None or full['created_at'] > previous['created_at']:
                previous = full
    baseline = float(previous['result']['final']['mean_stance']) if previous else None
    value = float(current['result']['final']['mean_stance'])
    gap = abs(value - baseline) if baseline is not None else None
    return {'run_id': run_id, 'previous_run_id': previous['id'] if previous else None,
            'current_mean': value, 'previous_mean': baseline, 'absolute_difference': round(gap, 3) if gap is not None else None,
            'threshold': threshold, 'flagged': gap >= threshold if gap is not None else None,
            'method_note': 'Comparação operacional entre médias sintéticas. Limite de alerta escolhido pelo usuário; não corresponde a validação estatística, drift de dados reais ou significância.'}
