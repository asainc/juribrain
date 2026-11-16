"""Persistência SQLite do laboratório; dados de BJN ficam em outro banco.

Salva snapshots imutáveis da configuração, eventos por rodada e resultados.
Transações independentes por operação permitem que a interface consulte progresso
sem bloquear a chamada remota de geração de linguagem.
"""
from __future__ import annotations

import json
import hashlib
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4
from backend.errors import ServiceError


def utc_now() -> str:
    """Padroniza as datas para auditoria e facilita comparações."""
    return datetime.now(timezone.utc).isoformat()


class LabRepository:
    """CRUD validado, eventos append-only e estados atômicos de execução."""

    TABLES = {"agents": "lab_agents", "environments": "lab_environments", "societies": "lab_societies"}

    def __init__(self, database_path: Path):
        self.path = Path(database_path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        with self._db() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS lab_agents (
                    id TEXT PRIMARY KEY, payload TEXT NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS lab_environments (
                    id TEXT PRIMARY KEY, payload TEXT NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS lab_societies (
                    id TEXT PRIMARY KEY, payload TEXT NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS lab_runs (
                    id TEXT PRIMARY KEY, status TEXT NOT NULL, mode TEXT NOT NULL,
                    configuration TEXT NOT NULL, snapshot TEXT NOT NULL,
                    result TEXT, error_code TEXT, completed INTEGER NOT NULL DEFAULT 0,
                    total INTEGER NOT NULL, cancel_requested INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL, updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS lab_events (
                    sequence INTEGER PRIMARY KEY AUTOINCREMENT, run_id TEXT NOT NULL,
                    round INTEGER NOT NULL, event_type TEXT NOT NULL, agent_id TEXT,
                    peer_id TEXT, payload TEXT NOT NULL, created_at TEXT NOT NULL,
                    FOREIGN KEY(run_id) REFERENCES lab_runs(id)
                );
                CREATE INDEX IF NOT EXISTS lab_events_run_seq ON lab_events(run_id, sequence);
                CREATE TABLE IF NOT EXISTS lab_experiments (
                    id TEXT PRIMARY KEY, status TEXT NOT NULL, payload TEXT NOT NULL,
                    result TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS lab_item_revisions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, item_kind TEXT NOT NULL, item_id TEXT NOT NULL,
                    version INTEGER NOT NULL, payload TEXT NOT NULL, sha256 TEXT NOT NULL,
                    created_at TEXT NOT NULL, UNIQUE(item_kind, item_id, version)
                );
                CREATE INDEX IF NOT EXISTS lab_revisions_kind_id ON lab_item_revisions(item_kind,item_id);
                CREATE TABLE IF NOT EXISTS lab_calibrations (
                    id TEXT PRIMARY KEY, run_id TEXT NOT NULL, payload TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(run_id) REFERENCES lab_runs(id)
                );
            """)
            # Migração idempotente: bancos existentes não perdem histórico ou resultados.
            columns = {item["name"] for item in db.execute("PRAGMA table_info(lab_runs)")}
            if "pause_requested" not in columns:
                db.execute("ALTER TABLE lab_runs ADD COLUMN pause_requested INTEGER NOT NULL DEFAULT 0")
            # Workers são locais ao processo. Reiniciar o servidor interrompe inclusive
            # uma simulação pausada; não afirmamos que um worker inexistente possa retomar.
            db.execute("UPDATE lab_runs SET status = 'INTERRUPTED', error_code = 'SERVER_RESTART', "
                       "pause_requested = 0, updated_at = ? WHERE status IN ('RUNNING','PAUSE_REQUESTED','PAUSED')", (utc_now(),))
            db.execute("UPDATE lab_experiments SET status = 'INTERRUPTED', updated_at = ? WHERE status = 'RUNNING'", (utc_now(),))

    @contextmanager
    def _db(self):
        """Conexão por transação: commit/rollback e fechamento explícitos."""
        db = sqlite3.connect(self.path, timeout=15, check_same_thread=False)
        try:
            db.row_factory = sqlite3.Row
            db.execute("PRAGMA busy_timeout = 15000")
            db.execute("PRAGMA foreign_keys = ON")
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def list_items(self, kind: str) -> list[dict]:
        table = self.TABLES[kind]
        with self._lock, self._db() as db:
            records = db.execute(f"SELECT id,payload,created_at,updated_at FROM {table} ORDER BY created_at DESC").fetchall()
        return [dict(id=r["id"], **json.loads(r["payload"]), created_at=r["created_at"], updated_at=r["updated_at"]) for r in records]

    def get_item(self, kind: str, item_id: str) -> dict:
        table = self.TABLES[kind]
        with self._lock, self._db() as db:
            row = db.execute(f"SELECT * FROM {table} WHERE id = ?", (item_id,)).fetchone()
        if row is None:
            raise ServiceError(f"{kind}: registro não encontrado.", 404, code="LAB_ITEM_NOT_FOUND")
        return {"id": row["id"], **json.loads(row["payload"]), "created_at": row["created_at"], "updated_at": row["updated_at"]}

    def save_item(self, kind: str, payload: dict, item_id: str | None = None) -> dict:
        table = self.TABLES[kind]
        with self._lock, self._db() as db:
            now = utc_now()
            serialized = json.dumps(payload, ensure_ascii=False, sort_keys=True)
            if item_id:
                result = db.execute(f"UPDATE {table} SET payload = ?, updated_at = ? WHERE id = ?", (serialized, now, item_id))
                if result.rowcount == 0:
                    raise ServiceError("Registro não encontrado.", 404, code="LAB_ITEM_NOT_FOUND")
            else:
                item_id = uuid4().hex
                db.execute(f"INSERT INTO {table} VALUES (?,?,?,?)", (item_id, serialized, now, now))
            version = db.execute("SELECT COALESCE(MAX(version),0)+1 FROM lab_item_revisions WHERE item_kind=? AND item_id=?",
                                 (kind, item_id)).fetchone()[0]
            db.execute("INSERT INTO lab_item_revisions (item_kind,item_id,version,payload,sha256,created_at) VALUES (?,?,?,?,?,?)",
                       (kind, item_id, version, serialized, hashlib.sha256(serialized.encode('utf-8')).hexdigest(), now))
        return self.get_item(kind, item_id)

    def create_scenario_bundle(self, agents: list[dict], environment: dict,
                               society_name: str, society_description: str) -> dict:
        """Insere uma sociedade completa em uma única transação, sem estado parcial.

        Os dados chegam validados pelo contrato de saída da IA. Não retemos o
        prompt do usuário nem a resposta original da Bridge nas tabelas.
        """
        now = utc_now()
        with self._lock, self._db() as db:
            created_agents: list[dict] = []
            for agent in agents:
                agent_id = uuid4().hex
                db.execute("INSERT INTO lab_agents VALUES (?,?,?,?)",
                           (agent_id, json.dumps(agent, ensure_ascii=False), now, now))
                serialized = json.dumps(agent, ensure_ascii=False, sort_keys=True)
                db.execute("INSERT INTO lab_item_revisions (item_kind,item_id,version,payload,sha256,created_at) VALUES (?,?,?,?,?,?)",
                           ('agents', agent_id, 1, serialized, hashlib.sha256(serialized.encode()).hexdigest(), now))
                created_agents.append({"id": agent_id, **agent, "created_at": now, "updated_at": now})
            environment_id = uuid4().hex
            db.execute("INSERT INTO lab_environments VALUES (?,?,?,?)",
                       (environment_id, json.dumps(environment, ensure_ascii=False), now, now))
            society = {"name": society_name, "description": society_description,
                       "agent_ids": [agent["id"] for agent in created_agents]}
            serialized_environment = json.dumps(environment, ensure_ascii=False, sort_keys=True)
            db.execute("INSERT INTO lab_item_revisions (item_kind,item_id,version,payload,sha256,created_at) VALUES (?,?,?,?,?,?)",
                       ('environments', environment_id, 1, serialized_environment, hashlib.sha256(serialized_environment.encode()).hexdigest(), now))
            society_id = uuid4().hex
            db.execute("INSERT INTO lab_societies VALUES (?,?,?,?)",
                       (society_id, json.dumps(society, ensure_ascii=False), now, now))
            serialized_society = json.dumps(society, ensure_ascii=False, sort_keys=True)
            db.execute("INSERT INTO lab_item_revisions (item_kind,item_id,version,payload,sha256,created_at) VALUES (?,?,?,?,?,?)",
                       ('societies', society_id, 1, serialized_society, hashlib.sha256(serialized_society.encode()).hexdigest(), now))
        return {"agents": created_agents, "environment": {"id": environment_id, **environment,
                "created_at": now, "updated_at": now},
                "society": {"id": society_id, **society, "created_at": now, "updated_at": now}}

    def delete_item(self, kind: str, item_id: str) -> None:
        table = self.TABLES[kind]
        with self._lock, self._db() as db:
            result = db.execute(f"DELETE FROM {table} WHERE id = ?", (item_id,))
            if result.rowcount == 0:
                raise ServiceError("Registro não encontrado.", 404, code="LAB_ITEM_NOT_FOUND")

    def create_run(self, config: dict, snapshot: dict) -> dict:
        """Limita execuções concorrentes para prevenir consumo não previsto de IA."""
        now = utc_now()
        run_id = uuid4().hex
        with self._lock, self._db() as db:
            active = db.execute("SELECT COUNT(*) AS amount FROM lab_runs WHERE status IN ('QUEUED','RUNNING','PAUSE_REQUESTED','PAUSED')").fetchone()["amount"]
            if active >= 40:
                raise ServiceError("Fila do Behavior atingiu 40 execuções. Conclua ou cancele uma antes de iniciar outra.", 409, code="LAB_CAPACITY_REACHED")
            db.execute("INSERT INTO lab_runs (id,status,mode,configuration,snapshot,total,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?)",
                       (run_id, "QUEUED", config["mode"], json.dumps(config, ensure_ascii=False), json.dumps(snapshot, ensure_ascii=False),
                        len(snapshot["agents"]) * config["rounds"] * config.get("repetitions", 1), now, now))
        return self.get_run(run_id)

    def get_run(self, run_id: str, include_events: bool = False) -> dict:
        with self._lock, self._db() as db:
            row = db.execute("SELECT * FROM lab_runs WHERE id = ?", (run_id,)).fetchone()
            if row is None:
                raise ServiceError("Simulação não encontrada.", 404, code="LAB_RUN_NOT_FOUND")
            result = dict(row)
            result["configuration"] = json.loads(result["configuration"])
            result["snapshot"] = json.loads(result["snapshot"])
            result["result"] = json.loads(result["result"]) if result["result"] else None
            result["cancel_requested"] = bool(result["cancel_requested"])
            result["pause_requested"] = bool(result["pause_requested"])
            if include_events:
                result["events"] = self._events(db, run_id)
        return result

    def list_runs(self) -> list[dict]:
        with self._lock, self._db() as db:
            rows = db.execute("SELECT id,mode,status,completed,total,created_at,updated_at,error_code,configuration,result FROM lab_runs ORDER BY created_at DESC LIMIT 40").fetchall()
        return [dict(id=r["id"], mode=r["mode"], status=r["status"], completed=r["completed"], total=r["total"], created_at=r["created_at"],
                     updated_at=r["updated_at"], error_code=r["error_code"], configuration=json.loads(r["configuration"]),
                     result=json.loads(r["result"]) if r["result"] else None) for r in rows]

    @staticmethod
    def _events(db, run_id: str) -> list[dict]:
        rows = db.execute("SELECT sequence,round,event_type,agent_id,peer_id,payload,created_at FROM lab_events WHERE run_id = ? ORDER BY sequence", (run_id,)).fetchall()
        return [{"sequence": row["sequence"], "round": row["round"], "event_type": row["event_type"], "agent_id": row["agent_id"],
                 "peer_id": row["peer_id"], "payload": json.loads(row["payload"]), "created_at": row["created_at"]} for row in rows]

    def events(self, run_id: str, after: int = 0) -> list[dict]:
        with self._lock, self._db() as db:
            if not db.execute("SELECT 1 FROM lab_runs WHERE id = ?", (run_id,)).fetchone():
                raise ServiceError("Simulação não encontrada.", 404, code="LAB_RUN_NOT_FOUND")
            rows = db.execute("SELECT sequence,round,event_type,agent_id,peer_id,payload,created_at FROM lab_events WHERE run_id=? AND sequence>? ORDER BY sequence LIMIT 1000", (run_id, after)).fetchall()
        return [{"sequence": r["sequence"], "round": r["round"], "event_type": r["event_type"], "agent_id": r["agent_id"],
                 "peer_id": r["peer_id"], "payload": json.loads(r["payload"]), "created_at": r["created_at"]} for r in rows]

    def transition(self, run_id: str, status: str, *, result: dict | None = None, error_code: str | None = None) -> None:
        with self._lock, self._db() as db:
            db.execute("UPDATE lab_runs SET status=?, result=?, error_code=?, updated_at=? WHERE id=?",
                       (status, json.dumps(result, ensure_ascii=False) if result is not None else None, error_code, utc_now(), run_id))

    def append(self, run_id: str, round_index: int, event_type: str, payload: dict, *, agent_id: str | None = None, peer_id: str | None = None, progress: bool = False) -> None:
        with self._lock, self._db() as db:
            db.execute("INSERT INTO lab_events (run_id,round,event_type,agent_id,peer_id,payload,created_at) VALUES (?,?,?,?,?,?,?)",
                       (run_id, round_index, event_type, agent_id, peer_id, json.dumps(payload, ensure_ascii=False), utc_now()))
            if progress:
                db.execute("UPDATE lab_runs SET completed=completed+1,updated_at=? WHERE id=?", (utc_now(), run_id))

    def is_cancel_requested(self, run_id: str) -> bool:
        """Consulta um único campo, sem reler snapshots durante cada reação."""
        with self._lock, self._db() as db:
            row = db.execute("SELECT cancel_requested FROM lab_runs WHERE id = ?", (run_id,)).fetchone()
            return bool(row["cancel_requested"]) if row else True

    def execution_control(self, run_id: str) -> tuple[bool, bool]:
        """Lê os sinais persistentes para os checkpoints entre reações."""
        with self._lock, self._db() as db:
            row = db.execute("SELECT cancel_requested, pause_requested FROM lab_runs WHERE id=?", (run_id,)).fetchone()
        # Um worker órfão encerra em segurança em vez de seguir sem registro.
        return (bool(row["cancel_requested"]), bool(row["pause_requested"])) if row else (True, False)

    def pause(self, run_id: str) -> None:
        """Solicita pausa cooperativa, sem fingir interromper chamadas externas em andamento."""
        with self._lock, self._db() as db:
            result = db.execute(
                "UPDATE lab_runs SET pause_requested=1, status='PAUSE_REQUESTED', updated_at=? "
                "WHERE id=? AND status IN ('QUEUED','RUNNING') AND cancel_requested=0",
                (utc_now(), run_id),
            )
            if result.rowcount == 0:
                raise ServiceError("A simulação não está ativa ou já recebeu pedido de pausa.", 409, code="LAB_PAUSE_INVALID_STATE")

    def mark_paused(self, run_id: str) -> None:
        """Confirma pausa apenas após o worker atingir um checkpoint seguro."""
        with self._lock, self._db() as db:
            db.execute("UPDATE lab_runs SET status='PAUSED', updated_at=? "
                       "WHERE id=? AND pause_requested=1 AND cancel_requested=0 "
                       "AND status IN ('QUEUED','RUNNING','PAUSE_REQUESTED')",
                       (utc_now(), run_id))

    def resume(self, run_id: str) -> None:
        """Retoma a execução com seu snapshot, memória e trilha de eventos existentes."""
        with self._lock, self._db() as db:
            row = db.execute("SELECT completed FROM lab_runs WHERE id=?", (run_id,)).fetchone()
            if row is None:
                raise ServiceError("Simulação não encontrada.", 404, code="LAB_RUN_NOT_FOUND")
            # Execuções pausadas antes do primeiro evento retornam à fila.
            initial = db.execute("SELECT 1 FROM lab_events WHERE run_id=? LIMIT 1", (run_id,)).fetchone() is None
            status = "QUEUED" if initial and row["completed"] == 0 else "RUNNING"
            result = db.execute("UPDATE lab_runs SET pause_requested=0, status=?, updated_at=? "
                                "WHERE id=? AND status IN ('PAUSED','PAUSE_REQUESTED') AND cancel_requested=0",
                                (status, utc_now(), run_id))
            if result.rowcount == 0:
                raise ServiceError("A simulação não está pausada ou já foi cancelada.", 409, code="LAB_RESUME_INVALID_STATE")

    def cancel(self, run_id: str) -> None:
        """Solicita cancelamento mesmo se o worker estiver aguardando a retomada."""
        with self._lock, self._db() as db:
            result = db.execute("UPDATE lab_runs SET cancel_requested=1, pause_requested=0, updated_at=? "
                                "WHERE id=? AND status IN ('QUEUED','RUNNING','PAUSE_REQUESTED','PAUSED')",
                                (utc_now(), run_id))
            if result.rowcount == 0:
                raise ServiceError("Esta simulação não está mais em execução.", 409, code="LAB_NOT_RUNNING")

    def create_experiment(self, payload: dict) -> dict:
        """Grava a definição versionada antes de executar suas variantes."""
        experiment_id, now = uuid4().hex, utc_now()
        with self._lock, self._db() as db:
            db.execute("INSERT INTO lab_experiments VALUES (?,?,?,?,?,?)", (experiment_id, "QUEUED", json.dumps(payload, ensure_ascii=False), None, now, now))
        return self.get_experiment(experiment_id)

    def get_experiment(self, experiment_id: str) -> dict:
        with self._lock, self._db() as db:
            row = db.execute("SELECT * FROM lab_experiments WHERE id = ?", (experiment_id,)).fetchone()
        if row is None:
            raise ServiceError("Experimento não encontrado.", 404, code="LAB_EXPERIMENT_NOT_FOUND")
        return {"id": row["id"], "status": row["status"], "payload": json.loads(row["payload"]),
                "result": json.loads(row["result"]) if row["result"] else None,
                "created_at": row["created_at"], "updated_at": row["updated_at"]}

    def list_experiments(self) -> list[dict]:
        with self._lock, self._db() as db:
            rows = db.execute("SELECT id FROM lab_experiments ORDER BY created_at DESC LIMIT 40").fetchall()
        return [self.get_experiment(row["id"]) for row in rows]

    def update_experiment(self, experiment_id: str, status: str, result: dict) -> None:
        """Checkpoint persistente após cada variante, inclusive em interrupções."""
        with self._lock, self._db() as db:
            db.execute("UPDATE lab_experiments SET status=?, result=?, updated_at=? WHERE id=?",
                       (status, json.dumps(result, ensure_ascii=False), utc_now(), experiment_id))

    def add_calibration(self, run_id: str, payload: dict) -> dict:
        """Registra referência agregada; não armazena amostras individuais."""
        self.get_run(run_id)
        record = {"id": uuid4().hex, "run_id": run_id, **payload, "created_at": utc_now()}
        with self._lock, self._db() as db:
            db.execute("INSERT INTO lab_calibrations VALUES (?,?,?,?)",
                       (record["id"], run_id, json.dumps(payload, ensure_ascii=False), record["created_at"]))
        return record

    def list_calibrations(self, run_id: str) -> list[dict]:
        self.get_run(run_id)
        with self._lock, self._db() as db:
            rows = db.execute("SELECT * FROM lab_calibrations WHERE run_id=? ORDER BY created_at DESC", (run_id,)).fetchall()
        return [{"id": row["id"], "run_id": row["run_id"], **json.loads(row["payload"]), "created_at": row["created_at"]} for row in rows]


    def queued_run_ids(self) -> list[str]:
        """Permite retomar trabalhos ainda não iniciados após reiniciar a API."""
        with self._lock, self._db() as db:
            return [row['id'] for row in db.execute("SELECT id FROM lab_runs WHERE status='QUEUED' ORDER BY created_at").fetchall()]

    def queued_experiment_ids(self) -> list[str]:
        """Retoma planos de comparação ainda na fila, sem reexecutar os parciais."""
        with self._lock, self._db() as db:
            return [row['id'] for row in db.execute("SELECT id FROM lab_experiments WHERE status='QUEUED' ORDER BY created_at").fetchall()]


    def item_versions(self, kind: str, item_id: str) -> list[dict]:
        """Histórico somente-leitura de revisões, com SHA para auditoria."""
        self.get_item(kind, item_id)
        with self._lock, self._db() as db:
            rows = db.execute("SELECT version,payload,sha256,created_at FROM lab_item_revisions WHERE item_kind=? AND item_id=? ORDER BY version DESC",
                              (kind, item_id)).fetchall()
        return [{'version': row['version'], 'payload': json.loads(row['payload']),
                 'sha256': row['sha256'], 'created_at': row['created_at']} for row in rows]
