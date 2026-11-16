"""Motor de sociedades sintéticas com reações individuais e influência coletiva.

MODO BRIDGE: cada reação solicita uma saída estruturada ao `text_generator`
corporativo; mensagens da rodada anterior são fornecidas como contexto.
MODO DEMO: regras explicitamente demonstrativas e reproduzíveis, sem IA nem
pretensão de prever pessoas reais. Nenhuma decisão jurídica é automatizada.
"""
from __future__ import annotations

import hashlib
import json
import logging
import random
import re
import time
from copy import deepcopy
from collections import defaultdict
from pathlib import Path
from statistics import mean, pstdev

from pydantic import ValidationError
from applications.behavior.backend.contracts import Reaction
from applications.behavior.backend.repository import LabRepository
from backend.services.bradesco_bridge import BradescoBridgeClient, BradescoBridgeError

logger = logging.getLogger("behavioral_lab")
PROMPT_PATH = Path(__file__).resolve().parents[3] / "prompts" / "behavioral_lab" / "reaction.system.md"


class SimulationValidationError(ValueError):
    """Falha previsível de validação, com código estável e sem saída crua da IA."""

    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


class LabSimulator:
    """Constrói rede, roda as etapas e consolida trilhas de evidência sintéticas."""

    def __init__(self, repository: LabRepository, bridge: BradescoBridgeClient):
        self.repository = repository
        self.bridge = bridge

    @staticmethod
    def build_network(agents: list[dict], density: float, rng: random.Random) -> list[dict]:
        """Sorteia rede não-direcionada, respeitando parâmetros de densidade e influência."""
        edges: list[dict] = []
        for i, first in enumerate(agents):
            for second in agents[i + 1:]:
                if rng.random() < density:
                    edges.append({"source": first["id"], "target": second["id"], "weight": round(.25 + .75 * rng.random(), 3)})
        return edges

    @staticmethod
    def neighbors(agent_id: str, network: list[dict], prior: dict[str, dict], agents: dict[str, dict], rng: random.Random) -> list[dict]:
        """Expõe até três falas verificáveis da rodada anterior, sem gerar diálogos ocultos."""
        candidates = []
        for edge in network:
            peer_id = edge["target"] if edge["source"] == agent_id else edge["source"] if edge["target"] == agent_id else None
            if peer_id and peer_id in prior:
                candidates.append({"id": peer_id, "name": agents[peer_id]["name"], "weight": edge["weight"],
                                   "stance": prior[peer_id]["stance"], "message": prior[peer_id]["message"],
                                   "influence": agents[peer_id]["influence"]})
        rng.shuffle(candidates)
        return candidates[:3]

    @staticmethod
    def _extract_reaction(raw: str) -> Reaction:
        """Valida JSON do modelo; não inventa reações quando a resposta é inválida."""
        candidate = raw.strip()
        if candidate.startswith("```"):
            candidate = re.sub(r"^```(?:json)?\s*|\s*```$", "", candidate, flags=re.IGNORECASE)
        try:
            data = json.loads(candidate)
            return Reaction.model_validate(data)
        except (ValueError, TypeError, ValidationError) as exc:
            raise ValueError("A IA não retornou a reação no formato JSON exigido.") from exc

    def _bridge_reaction(self, agent: dict, environment: dict, config: dict, round_index: int, peers: list[dict], shock: dict | None, prior: dict | None, changes: list[dict] | None = None, repetition: int = 1) -> tuple[Reaction, dict]:
        """Envia apenas perfis fictícios, cenário e mensagens de simulação ao gateway."""
        prompt = PROMPT_PATH.read_text(encoding="utf-8")
        data = {"agent": agent, "environment": environment, "round": round_index,
                "peer_messages_previous_round": peers, "previous_reaction": prior,
                "uncertainty": config["uncertainty"], "social_pressure": config["social_pressure"],
                "shock": shock, "scheduled_changes": changes or [], "seed": config["seed"],
                "simulation_index": repetition}
        body = json.dumps(data, ensure_ascii=False)
        result = self.bridge.generate_text_with_metadata(
            f"<system>\n{prompt}\n</system>\n<simulation_data_untrusted>\n{body}\n</simulation_data_untrusted>\n"
            "Responda apenas JSON, no schema do sistema.",
            max_tokens=config["max_tokens_per_reaction"],
            temperature=config["temperature"],
        )
        return self._extract_reaction(result.text), {
            'input_tokens': result.input_tokens,
            'cached_input_tokens': result.cached_input_tokens,
            'output_tokens': result.output_tokens,
        }

    @staticmethod
    def _demo_reaction(agent: dict, environment: dict, config: dict, prior: dict | None, peers: list[dict],
                       shock: dict | None, rng: random.Random, changes: list[dict] | None = None,
                       trace: dict | None = None) -> Reaction:
        """Modelo de regras didático: nunca inferir que a saída prevê decisões reais.

        Atualizações programadas têm impacto parametrizado; aleatoriedade é gerada
        exclusivamente pelo gerador local associado à repetição atual.
        """
        base = prior["stance"] if prior else agent["initial_stance"]
        components: dict[str, float] = {}
        social_factor = config["social_pressure"] * agent["susceptibility"]
        if peers:
            total = sum(peer["weight"] * peer["influence"] for peer in peers)
            target = sum(peer["stance"] * peer["weight"] * peer["influence"] for peer in peers) / total if total else base
            change = (target - base) * social_factor
            components["influencia_social"] = round(change, 5)
            base += change
        change = rng.uniform(-18, 18) * config["uncertainty"]
        components["variacao_aleatoria"] = round(change, 5)
        base += change
        # Efeito hipotético e explícito de uma variante; o sistema não deduz
        # causalidade a partir do nome de uma variável textual.
        variant_effect = float(config.get("variant_impact", 0)) * 18 * (0.35 + agent["susceptibility"])
        components["variante"] = round(variant_effect, 5)
        base += variant_effect
        event_effect = sum(change["impact"] * 18 * (0.35 + agent["susceptibility"]) for change in changes or [])
        components["eventos_programados"] = round(event_effect, 5)
        base += event_effect
        shock_effect = shock["direction"] * 22 * config["shock_intensity"] * (0.35 + agent["susceptibility"]) if shock else 0
        components["choque_aleatorio"] = round(shock_effect, 5)
        base += shock_effect
        stance = int(max(0, min(100, round(base))))
        if trace is not None:
            # Componentes observados: detalham a fórmula, inclusive arredondamento e limite 0–100.
            trace.update({"components": components, "raw_stance": round(base, 5),
                          "rounding_or_clipping": round(stance - base, 5)})
        target_behavior = environment.get("target_behavior") or "a decisão proposta"
        goal = agent["goal"].rstrip(".")
        if stance >= environment.get("high_threshold", 65):
            action, emotion = f"Considerar: {target_behavior}"[:180], "interesse"
            message = f"Estou favorável a {target_behavior.lower()}. Minha prioridade é {goal.lower()}."
        elif stance >= environment.get("low_threshold", 40):
            action, emotion = "Solicitar mais informações", "cautela"
            message = f"Ainda estou avaliando {target_behavior.lower()}. Para mim, é importante {goal.lower()}."
        else:
            action, emotion = "Apontar riscos e alternativas", "reserva"
            message = f"Tenho objeções a {target_behavior.lower()}. Gostaria de assegurar que seja possível {goal.lower()}."
        if peers:
            message += f" Ouvi {peers[0]['name']} e quero ponderar os argumentos antes de decidir."
        allowed = environment.get('allowed_agent_effects') or {}
        updates = {}
        if environment.get('enable_agent_actions') and stance >= environment.get('high_threshold', 65) and rng.random() < 0.3:
            # A regra demonstra uma ação fictícia, limitada à lista de valores
            # permitidos; não altera sistemas ou dados externos.
            for key, options in allowed.items():
                if options:
                    updates[key] = rng.choice(options)
                    break
        return Reaction(stance=stance, emotion=emotion, action=action, message=message[:900],
                        reason="Reação demonstrativa baseada em estado, rede, parâmetros e eventos fictícios; sem calibração com comportamento real.",
                        environment_updates=updates)

    @staticmethod
    def decision_trace(agent: dict, reaction: Reaction, prior: dict | None, peers: list[dict],
                       shock: dict | None, scheduled: list[dict], config: dict,
                       calculation: dict) -> dict:
        """Registra evidências observáveis, distinguindo regra calculada de relato da IA.

        Esta trilha explica o que entrou no modelo, não afirma identificar uma
        causa real de comportamento humano. Nunca persiste prompt ou credenciais.
        """
        before = int(prior['stance'] if prior else agent['initial_stance'])
        delta = reaction.stance - before
        return {
            'schema_version': 1,
            'previous_stance': before, 'current_stance': reaction.stance, 'delta': delta,
            'changed': delta != 0, 'first_round': prior is None,
            'peer_signals': [{"agent_id": peer['id'], "name": peer['name'], "stance": peer['stance'],
                              "weight": peer['weight'], "influence": peer['influence']} for peer in peers],
            'scheduled_changes': [{"name": change['name'], "impact": change['impact']} for change in scheduled],
            'shock': {"label": shock['label'], "direction": shock['direction'],
                      "intensity": shock['intensity']} if shock else None,
            'source': 'REGRAS_DEMO' if config['mode'] == 'demo' else 'JUSTIFICATIVA_IA',
            'reason': reaction.reason,
            'calculation': calculation if config['mode'] == 'demo' else None,
            'interpretation': ('Componentes numéricos calculados por regras ilustrativas, sem validação empírica.'
                               if config['mode'] == 'demo' else
                               'A justificativa é a declaração do modelo. Os sinais listados foram fornecidos, '
                               'mas não é possível provar quais determinaram a resposta.'),
        }

    @staticmethod
    def evaluate_metrics(reaction: Reaction, environment: dict, mode: str) -> dict:
        """Valida saídas livres sem converter texto incorreto em um indicador inventado.

        No modo demonstrativo, a associação de métricas com stance é puramente
        algorítmica e explicitamente hipotética; não representa calibração.
        """
        result: dict = {}
        for definition in environment.get("metrics", []):
            key, kind = definition["key"], definition["kind"]
            if mode == "demo":
                if kind == "number":
                    low, high = definition["minimum"], definition["maximum"]
                    value = round(low + (high - low) * reaction.stance / 100, 3)
                elif kind == "boolean":
                    value = reaction.stance >= environment.get("high_threshold", 65)
                else:
                    categories = definition["categories"]
                    value = categories[min(len(categories) - 1, int(reaction.stance * len(categories) / 101))]
            else:
                value = reaction.metrics.get(key)
                if value is not None:
                    if kind == "number":
                        if isinstance(value, bool) or not isinstance(value, (int, float)) or not definition["minimum"] <= value <= definition["maximum"]:
                            raise SimulationValidationError("LAB_METRIC_INVALID")
                    elif kind == "boolean":
                        if not isinstance(value, bool):
                            raise SimulationValidationError("LAB_METRIC_INVALID")
                    elif not isinstance(value, str) or value not in definition["categories"]:
                        raise SimulationValidationError("LAB_METRIC_INVALID")
            result[key] = value
        unexpected = set(reaction.metrics) - {metric["key"] for metric in environment.get("metrics", [])}
        if unexpected:
            raise SimulationValidationError("LAB_METRIC_INVALID")
        return result

    @staticmethod
    def summarize_custom_metrics(reactions: list[dict], environment: dict) -> list[dict]:
        """Agrega números, booleanos e categorias apenas como estatística sintética."""
        output: list[dict] = []
        for definition in environment.get("metrics", []):
            key, kind = definition["key"], definition["kind"]
            values = [reaction.get("metrics", {}).get(key) for reaction in reactions]
            values = [value for value in values if value is not None]
            item = {"key": key, "label": definition["label"], "kind": kind, "observations": len(values)}
            if kind == "number":
                item.update({"mean": round(mean(values), 3) if values else None,
                             "minimum": min(values) if values else None, "maximum": max(values) if values else None})
            elif kind == "boolean":
                item.update({"true": sum(value is True for value in values), "false": sum(value is False for value in values)})
            else:
                item["counts"] = {category: sum(value == category for value in values) for category in definition["categories"]}
            output.append(item)
        return output

    @staticmethod
    def summarize(agents: list[dict], reactions: list[dict], network: list[dict], config: dict, environment: dict) -> dict:
        """Agrupa apenas fatos observados na simulação, sem falsa probabilidade real."""
        if not reactions:
            return {"total_agents": len(agents), "total_reactions": 0, "network_edges": len(network), "rounds": [], "final": None}
        history: dict[int, list[dict]] = defaultdict(list)
        for reaction in reactions:
            history[reaction["round"]].append(reaction)
        per_round = []
        low_threshold = environment.get("low_threshold", 40)
        high_threshold = environment.get("high_threshold", 65)
        for round_index, values in sorted(history.items()):
            stances = [value["stance"] for value in values]
            per_round.append({"round": round_index, "mean_stance": round(mean(stances), 2),
                              "support": sum(stance >= high_threshold for stance in stances),
                              "undecided": sum(low_threshold <= stance < high_threshold for stance in stances),
                              "resistance": sum(stance < low_threshold for stance in stances), "agents": len(values)})
        first_stance = {r["agent_id"]: r["stance"] for r in history[min(history)]}
        last_reactions = history[max(history)]
        groups: dict[str, list[int]] = defaultdict(list)
        for value in last_reactions:
            group = next(agent["group"] for agent in agents if agent["id"] == value["agent_id"])
            groups[group].append(value["stance"])
        return {
            "total_agents": len(agents), "total_reactions": len(reactions), "network_edges": len(network),
            "rounds": per_round, "final": per_round[-1],
            "mean_stance_change": round(mean(r["stance"] - first_stance[r["agent_id"]] for r in last_reactions), 2),
            "groups": [{"name": group, "mean_stance": round(mean(values), 2), "agents": len(values)} for group, values in sorted(groups.items())],
            "scenario": environment["name"], "mode": config["mode"], "seed": config["seed"],
            "method_note": ("Simulação ilustrativa por regras; não é previsão validada de clientes reais." if config["mode"] == "demo" else
                            "Saídas de IA de personas fictícias; calibrar contra dados reais antes de decisões."),
            "metrics": LabSimulator.summarize_custom_metrics(last_reactions, environment),
            "limitations": ["Sem representatividade estatística garantida", "Sem intervalo de confiança calibrado",
                            "Sem validação causal ou jurídica", "Não utilizar para decisões individuais automatizadas"],
        }

    @staticmethod
    def consolidate(repetitions: list[dict], agents: list[dict], network_edges: int, config: dict,
                    environment: dict, total_reactions: int) -> dict:
        """Resume repetições independentes e separa frequência sintética de probabilidade real.

        Cada repetição é uma nova rede e um novo fluxo de interações; nenhum agente
        compartilha memórias de uma repetição anterior do mesmo experimento.
        """
        if not repetitions:
            return {"repetitions": [], "repetitions_completed": 0, "total_reactions": total_reactions,
                    "total_agents": len(agents), "network_edges": network_edges, "rounds": [], "final": None}
        samples = [r["summary"] for r in repetitions]
        if len(samples) == 1:
            result = dict(samples[0])
        else:
            rounds = []
            for index in range(1, config["rounds"] + 1):
                values = [r["rounds"][index - 1] for r in samples if len(r["rounds"]) >= index]
                if not values:
                    continue
                rounds.append({"round": index, "mean_stance": round(mean(v["mean_stance"] for v in values), 2),
                               "support": sum(v["support"] for v in values),
                               "undecided": sum(v["undecided"] for v in values),
                               "resistance": sum(v["resistance"] for v in values),
                               "agents": sum(v["agents"] for v in values)})
            grouped = defaultdict(list)
            for sample in samples:
                for group in sample.get("groups", []):
                    grouped[group["name"]].append(group["mean_stance"])
            result = {"total_agents": len(agents), "total_reactions": total_reactions,
                      "network_edges": network_edges, "rounds": rounds,
                      "final": rounds[-1] if rounds else None,
                      "mean_stance_change": round(mean(s.get("mean_stance_change", 0) for s in samples), 2),
                      "groups": [{"name": name, "mean_stance": round(mean(values), 2), "agents": next(
                          (g["agents"] for g in samples[0].get("groups", []) if g["name"] == name), 0)}
                          for name, values in sorted(grouped.items())],
                      "scenario": environment["name"], "mode": config["mode"], "seed": config["seed"],
                      "method_note": samples[0].get("method_note"), "limitations": samples[0].get("limitations")}
        # A agregação de métricas considera apenas reações finais por repetição.
        metric_definitions = environment.get("metrics", [])
        if metric_definitions:
            result["metrics"] = []
            for metric in metric_definitions:
                entries = [next((item for item in sample.get("metrics", []) if item["key"] == metric["key"]), None) for sample in samples]
                entries = [item for item in entries if item]
                if not entries:
                    continue
                merged = {"key": metric["key"], "label": metric["label"], "kind": metric["kind"],
                          "observations": sum(item["observations"] for item in entries)}
                if metric["kind"] == "number":
                    total = sum(item["observations"] for item in entries)
                    merged["mean"] = round(sum(item["mean"] * item["observations"] for item in entries if item["mean"] is not None) / total, 3) if total else None
                    vals = [item for item in entries if item["minimum"] is not None]
                    merged["minimum"] = min(item["minimum"] for item in vals) if vals else None
                    merged["maximum"] = max(item["maximum"] for item in vals) if vals else None
                elif metric["kind"] == "boolean":
                    merged["true"] = sum(item["true"] for item in entries)
                    merged["false"] = sum(item["false"] for item in entries)
                else:
                    merged["counts"] = {category: sum(item["counts"].get(category, 0) for item in entries) for category in metric["categories"]}
                result.setdefault("metrics", []).append(merged)
        final_means = [s["final"]["mean_stance"] for s in samples if s["final"]]
        result.update({"repetitions_completed": len(repetitions), "repetitions_planned": config.get("repetitions", 1),
                       "repetitions": [{"index": r["index"], "seed": r["seed"], "final": r["summary"].get("final"),
                                        "rounds": r["summary"].get("rounds", [])} for r in repetitions],
                       "final_score_distribution": {"minimum": min(final_means) if final_means else None,
                                                    "maximum": max(final_means) if final_means else None,
                                                    "mean": round(mean(final_means), 2) if final_means else None,
                                                    "standard_deviation": round(pstdev(final_means), 2) if final_means else None},
                       "total_agents": len(agents), "total_reactions": total_reactions,
                       "network_edges": network_edges,
                       "interpretation": "Distribuição entre execuções sintéticas, não probabilidade populacional ou intervalo de confiança."})
        return result

    def _await_permission(self, run_id: str) -> bool:
        """Bloqueia entre reações; permite cancelar sem perder dados já persistidos.

        O controle mora no SQLite, por isso funciona também quando o comando HTTP
        de pausa/retomada ocorre em outro worker da API. A chamada de IA já
        iniciada não é interrompida à força.
        """
        while True:
            cancelled, pause_requested = self.repository.execution_control(run_id)
            if cancelled:
                return False
            if not pause_requested:
                return True
            self.repository.mark_paused(run_id)
            time.sleep(0.1)

    def execute(self, run_id: str) -> None:
        """Executa repetições isoladas; emite eventos incrementais para replay e auditoria."""
        try:
            run = self.repository.get_run(run_id)
            config, snapshot = run["configuration"], run["snapshot"]
            agents = snapshot["agents"]
            by_id = {agent["id"]: agent for agent in agents}
            environment = snapshot["environment"]
            repetitions_count = config.get("repetitions", 1)
            if not self._await_permission(run_id):
                self.repository.transition(run_id, "CANCELLED")
                return
            # A pausa pode ser solicitada enquanto a fila inicia. O controle
            # persistente será conferido de novo antes de produzir eventos.
            self.repository.transition(run_id, "RUNNING")
            prompt_fingerprint = hashlib.sha256(PROMPT_PATH.read_bytes()).hexdigest() if config["mode"] == "bridge" else None
            results: list[dict] = []
            total_reactions = 0
            total_edges = 0
            for repetition in range(1, repetitions_count + 1):
                if not self._await_permission(run_id):
                    result = self.consolidate(results, agents, total_edges, config, environment, total_reactions)
                    self.repository.transition(run_id, "CANCELLED", result=result)
                    return
                # Seeds distintas isolam os experimentos e tornam o modo demo reprodutível.
                repetition_seed = (config["seed"] + repetition - 1) % (2**31)
                rng = random.Random(repetition_seed)
                network = self.build_network(agents, config["network_density"], rng)
                total_edges += len(network)
                self.repository.append(run_id, 0, "NETWORK", {"edges": network, "agents": len(agents),
                    "repetition": repetition, "seed": repetition_seed})
                self.repository.append(run_id, 0, "REPETITION_STARTED", {"repetition": repetition,
                    "total_repetitions": repetitions_count, "seed": repetition_seed})
                current_environment = deepcopy(environment)
                # Eventos futuros ficam no cronograma, mas nunca entram no contexto
                # fornecido à IA antes de sua rodada de ocorrência.
                current_environment.pop("events", None)
                current_environment["variables"] = dict(environment.get("variables") or {})
                previous: dict[str, dict] = {}
                # A memória é local à repetição; cada agente recebe apenas seu
                # histórico recente e as mensagens dirigidas a ele.
                memories: dict[str, list[dict]] = {agent["id"]: [] for agent in agents}
                incoming_next: dict[str, list[dict]] = defaultdict(list)
                reactions: list[dict] = []
                for round_index in range(1, config["rounds"] + 1):
                    if not self._await_permission(run_id):
                        result = self.consolidate(results, agents, total_edges, config, environment, total_reactions)
                        self.repository.transition(run_id, "CANCELLED", result=result)
                        return
                    for recipient_id, messages in incoming_next.items():
                        memories[recipient_id].extend(messages)
                    incoming_next = defaultdict(list)
                    scheduled = []
                    for change in environment.get("events", []):
                        if change["round"] != round_index:
                            continue
                        current_environment["variables"].update(change.get("variable_updates") or {})
                        event = {**change, "repetition": repetition,
                                 "variables_after": dict(current_environment["variables"])}
                        scheduled.append(event)
                        self.repository.append(run_id, round_index, "ENVIRONMENT_CHANGE", event)
                    self.repository.append(run_id, round_index, "ENVIRONMENT_SNAPSHOT", {"repetition": repetition, "variables": dict(current_environment["variables"])})
                    shock = None
                    if rng.random() < config["shock_probability"]:
                        direction = rng.choice([-1, 1])
                        shock = {"direction": direction, "intensity": config["shock_intensity"],
                                 "repetition": repetition, "label": "Mudança de contexto adversa" if direction < 0 else "Mudança de contexto favorável"}
                        self.repository.append(run_id, round_index, "SHOCK", shock)
                    current: dict[str, dict] = {}
                    for agent in agents:
                        if not self._await_permission(run_id):
                            result = self.consolidate(results, agents, total_edges, config, environment, total_reactions)
                            self.repository.transition(run_id, "CANCELLED", result=result)
                            return
                        peers = self.neighbors(agent["id"], network, previous, by_id, rng)
                        for peer in peers:
                            self.repository.append(run_id, round_index, "INTERACTION", {"message": peer["message"],
                                "previous_stance": peer["stance"], "weight": peer["weight"], "repetition": repetition},
                                agent_id=peer["id"], peer_id=agent["id"])
                        calculation_trace: dict = {}
                        if config["mode"] == "bridge":
                            context_agent = {**agent, 'short_term_memory': memories[agent['id']][-config.get('memory_window', 4):]}
                            reaction, usage = self._bridge_reaction(context_agent, current_environment,
                                {**config, 'seed': repetition_seed}, round_index,
                                peers, shock, previous.get(agent['id']), scheduled, repetition)
                        else:
                            usage = {}
                            reaction = self._demo_reaction(agent, current_environment, config, previous.get(agent["id"]),
                                                           peers, shock, rng, scheduled, calculation_trace)
                        # Pausa solicitada durante uma chamada ao modelo: não
                        # acrescentar reação/eventos até retomar.
                        if not self._await_permission(run_id):
                            result = self.consolidate(results, agents, total_edges, config, environment, total_reactions)
                            self.repository.transition(run_id, "CANCELLED", result=result)
                            return
                        metrics = self.evaluate_metrics(reaction, current_environment, config["mode"])
                        if not current_environment.get('enable_agent_actions') and reaction.environment_updates:
                            raise SimulationValidationError("LAB_ACTION_INVALID")
                        if len(reaction.environment_updates) > 4:
                            raise SimulationValidationError("LAB_ACTION_INVALID")
                        value = {"agent_id": agent["id"], "agent_name": agent["name"], "round": round_index,
                                 "repetition": repetition, **reaction.model_dump(), "metrics": metrics,
                                 "token_usage": usage, "influenced_by": [p["id"] for p in peers],
                                 "decision_trace": self.decision_trace(agent, reaction, previous.get(agent['id']),
                                                                       peers, shock, scheduled, config, calculation_trace)}
                        current[agent["id"]] = value
                        reactions.append(value)
                        total_reactions += 1
                        self.repository.append(run_id, round_index, "REACTION", value, agent_id=agent["id"], progress=True)
                        memories[agent["id"]].append({"round": round_index, "action": reaction.action,
                            "message": reaction.message, "stance": reaction.stance, "metrics": metrics})
                        # Troca endereçada: o destinatário responderá na próxima rodada
                        # se a relação estiver ativa. Não apresentamos isso como
                        # diálogo em tempo real entre chamadas do modelo.
                        recipients = [edge["target"] if edge["source"] == agent["id"] else edge["source"]
                                      for edge in network if agent["id"] in (edge["source"], edge["target"])]
                        if recipients:
                            peer_id = rng.choice(recipients)
                            self.repository.append(run_id, round_index, "CONVERSATION", {
                                "repetition": repetition, "message": reaction.message,
                                "action": reaction.action, "source_name": agent["name"],
                                "target_name": by_id[peer_id]["name"], "reply_in_next_round": round_index < config["rounds"]},
                                agent_id=agent["id"], peer_id=peer_id)
                            incoming_next[peer_id].append({"round": round_index, "from": agent["name"], "message": reaction.message})
                    self.repository.append(run_id, round_index, "ROUND_SUMMARY", {"repetition": repetition,
                        "summary": self.summarize(agents, reactions, network, config, environment)["final"]})
                    # Ações propostas são aplicadas apenas depois que todos os
                    # agentes reagiram; nenhuma atualização indevida é aceita.
                    if current_environment.get('enable_agent_actions'):
                        allowed_effects = current_environment.get('allowed_agent_effects') or {}
                        for reaction_value in current.values():
                            for key, new_value in reaction_value.get('environment_updates', {}).items():
                                if key not in allowed_effects or new_value not in allowed_effects[key]:
                                    raise SimulationValidationError("LAB_ACTION_INVALID")
                                old_value = current_environment['variables'].get(key)
                                current_environment['variables'][key] = new_value
                                self.repository.append(run_id, round_index, 'AGENT_ACTION', {
                                    'repetition': repetition, 'name': 'Efeito da ação sintética', 'key': key,
                                    'previous_value': old_value, 'new_value': new_value,
                                    'description': f'Agente alterou a variável {key} conforme política fictícia.'},
                                    agent_id=reaction_value['agent_id'])
                    previous = current
                results.append({"index": repetition, "seed": repetition_seed,
                                "summary": self.summarize(agents, reactions, network, config, environment)})
                self.repository.append(run_id, config["rounds"], "REPETITION_COMPLETED", {"repetition": repetition})
            # Um pedido de pausa nos instantes finais ainda é respeitado.
            if not self._await_permission(run_id):
                result = self.consolidate(results, agents, total_edges, config, environment, total_reactions)
                self.repository.transition(run_id, "CANCELLED", result=result)
                return
            aggregate = self.consolidate(results, agents, total_edges, config, environment, total_reactions)
            # Tokens só podem ser informados como medidos quando a Bridge entrega
            # os contadores. Valores ausentes não são tratados como zero.
            token_events = [item['payload']['token_usage'] for item in self.repository.events(run_id)
                            if item['event_type'] == 'REACTION' and item['payload'].get('token_usage')]
            measured_usage = {}
            for field in ('input_tokens', 'cached_input_tokens', 'output_tokens'):
                values = [item[field] for item in token_events if item.get(field) is not None]
                measured_usage[field] = sum(values) if len(values) == total_reactions and values else None
            trace_hash = hashlib.sha256(json.dumps({"snapshot": snapshot, "config": config},
                ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()
            self.repository.transition(run_id, "COMPLETED", result={**aggregate,
                "prompt_sha256": prompt_fingerprint, "snapshot_sha256": trace_hash,
                "engine_version": "behavior-3.0", "actual_token_usage": measured_usage,
                "configured_model": getattr(getattr(self.bridge, 'settings', None), 'bradesco_text_model', None) if config['mode'] == 'bridge' else None,
                "configuration_note": "Sementes reproduzíveis em modo demo; a Bridge pode não ser determinística."})
            logger.info("lab_run_completed", extra={"run_id": run_id, "reactions": total_reactions,
                                                    "repetitions": repetitions_count, "mode": config["mode"]})
        except Exception as exc:
            # Não registramos argumentos/prompt nem respostas da Bridge.
            candidate = getattr(exc, "code", "")
            code = (candidate if isinstance(candidate, str) and re.fullmatch(r"[A-Za-z0-9_]{1,60}", candidate)
                    else "MODEL_OUTPUT_INVALID" if isinstance(exc, ValueError) else "LAB_EXECUTION_ERROR")
            stage = ("CHAMADA_IA" if isinstance(exc, BradescoBridgeError) else
                     "VALIDACAO_RESPOSTA" if isinstance(exc, ValueError) else "MOTOR_SIMULACAO")
            # Nunca registrar a mensagem crua da exceção: pode incluir entrada,
            # saída gerada, URL interna ou partes de uma credencial.
            logger.error("lab_run_failed", extra={"run_id": run_id, "error_type": type(exc).__name__,
                                                  "error_code": code, "stage": stage})
            self.repository.transition(run_id, "FAILED", error_code=code, failure_stage=stage)
