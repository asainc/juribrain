"""Duração auditável de simulações: relógio efetivo e pausa persistida."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from applications.behavior.backend.repository import LabRepository


def _run(repository: LabRepository) -> str:
    """Cria execução de laboratório sem depender de uma Bridge externa."""
    return repository.create_run({"mode": "demo", "rounds": 1}, {"agents": [{"id": "synthetic"}]})["id"]


def test_elapsed_excludes_confirmed_pause_and_persists_after_completion(tmp_path):
    """A pausa confirmada não deve ser contada como tempo de trabalho."""
    repository = LabRepository(tmp_path / "timing.sqlite3")
    run_id = _run(repository)
    repository.transition(run_id, "RUNNING")
    repository.append(run_id, 1, "NETWORK", {"edges": [], "repetition": 1})
    now = datetime.now(timezone.utc)
    with repository._db() as db:
        db.execute("UPDATE lab_runs SET started_at=? WHERE id=?", ((now-timedelta(seconds=120)).isoformat(), run_id))
    repository.pause(run_id)
    repository.mark_paused(run_id)
    with repository._db() as db:
        db.execute("UPDATE lab_runs SET paused_at=? WHERE id=?", ((now-timedelta(seconds=90)).isoformat(), run_id))
    paused = repository.get_run(run_id)
    assert paused["status"] == "PAUSED"
    assert 29 <= paused["elapsed_seconds"] <= 32
    repository.resume(run_id)
    active = repository.get_run(run_id)
    assert active["status"] == "RUNNING"
    assert 29 <= active["elapsed_seconds"] <= 32
    repository.transition(run_id, "COMPLETED")
    completed = repository.get_run(run_id)
    assert completed["finished_at"]
    assert 29 <= completed["elapsed_seconds"] <= 32


def test_pause_before_first_reaction_does_not_subtract_prestart_queue_time(tmp_path):
    """Aguardar em fila/pausa antes do início não gera duração negativa."""
    repository = LabRepository(tmp_path / "queue.sqlite3")
    run_id = _run(repository)
    repository.pause(run_id)
    repository.mark_paused(run_id)
    assert repository.get_run(run_id)["elapsed_seconds"] == 0
    repository.resume(run_id)
    assert repository.get_run(run_id)["status"] == "QUEUED"
    repository.transition(run_id, "RUNNING")
    assert repository.get_run(run_id)["elapsed_seconds"] >= 0
