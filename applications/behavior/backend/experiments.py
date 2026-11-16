"""Orquestra comparações de cenários sem substituir validação experimental real.

Cada variante recebe o mesmo conjunto de agentes e a mesma semente.
O motor preserva snapshots independentes; resultados são apenas sintéticos.
"""
from __future__ import annotations

import logging
from copy import deepcopy
from statistics import mean

from applications.behavior.backend.repository import LabRepository
from applications.behavior.backend.simulator import LabSimulator
from applications.behavior.backend.contracts import ExperimentInput

logger = logging.getLogger('behavior_experiments')


class ExperimentOrchestrator:
    """Strategy simples: execução sequencial e checkpoints persistentes por variante."""

    def __init__(self, repository: LabRepository, simulator: LabSimulator):
        self.repository = repository
        self.simulator = simulator

    @staticmethod
    def compare(rows: list[dict]) -> dict:
        """Computa diferenças descritivas, nunca incrementos causais ou p-valores."""
        reference = next((row for row in rows if row['name'] == 'Base'), None)
        baseline_value = (reference or {}).get('mean_stance')
        output = []
        for row in rows:
            value = row.get('mean_stance')
            output.append({**row, 'delta_to_base': round(value - baseline_value, 3)
                           if value is not None and baseline_value is not None else None})
        return {'comparison': output, 'baseline': baseline_value,
                'disclaimer': 'Diferenças entre simulações sintéticas; não indicam causalidade, validade externa ou probabilidade de comportamento real.'}

    def execute(self, experiment_id: str) -> None:
        """Retoma apenas dentro do processo atual; reinício marca INTERRUPTED.

        Checkpoints são salvos ao fim de cada execução; em falha, os runs
        anteriores continuam auditáveis sem inventar dados ausentes.
        """
        rows: list[dict] = []
        try:
            experiment = self.repository.get_experiment(experiment_id)
            payload = ExperimentInput.model_validate({key: experiment['payload'][key] for key in ('name', 'hypothesis', 'baseline', 'variants')})
            baseline = payload.baseline.model_dump()
            frozen = experiment['payload']['snapshot']
            environment, society, agents = frozen['environment'], frozen['society'], frozen['agents']
            variants = [('Base', {}, {}, 0.0)] + [(variant.name, variant.parameter_updates, variant.variable_updates, variant.impact)
                                            for variant in payload.variants]
            self.repository.update_experiment(experiment_id, 'RUNNING', self.compare(rows))
            for name, parameters, variables, impact in variants:
                configuration = {**baseline, **parameters, "variant_impact": impact}
                snapshot = {'environment': deepcopy(environment), 'society': deepcopy(society), 'agents': deepcopy(agents)}
                snapshot['environment']['variables'].update(variables)
                try:
                    run = self.repository.create_run(configuration, snapshot)
                    self.simulator.execute(run['id'])
                    completed = self.repository.get_run(run['id'])
                    final = (completed.get('result') or {}).get('final') or {}
                    distribution = (completed.get('result') or {}).get('final_score_distribution') or {}
                    metrics = (completed.get('result') or {}).get('metrics') or []
                    rows.append({'name': name, 'run_id': run['id'], 'status': completed['status'],
                                 'mean_stance': final.get('mean_stance') if completed['status'] == 'COMPLETED' else None,
                                 'distribution': distribution, 'metrics': metrics, 'parameters': parameters,
                                 'variables': variables, 'impact': impact, 'repetitions': configuration.get('repetitions', 1)})
                    self.repository.update_experiment(experiment_id, 'RUNNING', self.compare(rows))
                    if completed['status'] != 'COMPLETED':
                        self.repository.update_experiment(experiment_id, 'PARTIAL', self.compare(rows))
                        return
                except Exception as error:
                    logger.error('behavior_experiment_variant_failed', extra={'experiment_id': experiment_id,
                        'variant': name, 'error_type': type(error).__name__})
                    rows.append({'name': name, 'run_id': None, 'status': 'FAILED', 'mean_stance': None,
                                 'parameters': parameters, 'variables': variables, 'metrics': []})
                    self.repository.update_experiment(experiment_id, 'PARTIAL', self.compare(rows))
                    return
            self.repository.update_experiment(experiment_id, 'COMPLETED', self.compare(rows))
        except Exception as error:
            logger.error('behavior_experiment_failed', extra={'experiment_id': experiment_id, 'error_type': type(error).__name__})
            self.repository.update_experiment(experiment_id, 'FAILED', self.compare(rows))
