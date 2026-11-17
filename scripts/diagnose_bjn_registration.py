"""Diagnóstico seguro do cadastro BJN sem consultar dados dos processos.

Uso: python scripts/diagnose_bjn_registration.py
Saída: JSON somente com estados e códigos, sem caminhos, documentos ou segredos.
"""
from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path
from tempfile import NamedTemporaryFile

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.config import load_settings  # noqa: E402
from applications.bjn.backend.services.bjn_directory import agencies, departments  # noqa: E402
from backend.errors import ServiceError  # noqa: E402

EXPECTED_TABLES = {
    "bjn_demands", "bjn_demand_context", "bjn_documents", "bjn_events",
    "bjn_involved", "bjn_opinions", "bjn_document_suggestions",
}


def check_write_directory(path: Path) -> str:
    """Verifica escrita com arquivo temporário descartado, sem alterar dados jurídicos."""
    if not path.is_dir():
        return "DIRECTORY_MISSING"
    try:
        with NamedTemporaryFile(dir=path, prefix=".bjn-check-", delete=True) as handle:
            handle.write(b"bjn-test")
            handle.flush()
        return "OK"
    except OSError:
        return "NOT_WRITABLE"


def check_database(path: Path) -> str:
    """Confere apenas metadados de schema em acesso SQLite somente leitura."""
    if not path.is_file():
        return "DATABASE_MISSING"
    try:
        uri = path.resolve().as_uri() + "?mode=ro"
        with sqlite3.connect(uri, uri=True, timeout=2) as conn:
            rows = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        available = {name for (name,) in rows}
        return "OK" if EXPECTED_TABLES.issubset(available) else "SCHEMA_INCOMPLETE"
    except sqlite3.Error:
        return "DATABASE_READ_ERROR"


def catalog_result(reader, required: str | None = None) -> dict[str, object]:
    """Confere o catálogo sem divulgar códigos ou nomes de unidades."""
    try:
        values = reader()
        return {"status": "OK" if (required is None or required in values) else "REQUIRED_ITEM_MISSING",
                "count": len(values)}
    except ServiceError as exc:
        return {"status": exc.code, "count": 0}


def run_diagnostic() -> dict[str, object]:
    """Agrega checagens que não dependem da API corporativa nem criam demandas."""
    try:
        settings = load_settings()
    except Exception:
        return {"configuration": "CONFIGURATION_INVALID"}
    return {
        "configuration": "OK",
        "environment": "local" if settings.environment == "local" else "corporate",
        "database_directory": check_write_directory(settings.bjn_database_path.parent),
        "database_schema": check_database(settings.bjn_database_path),
        "upload_directory": check_write_directory(settings.bjn_upload_directory),
        "departments": catalog_result(departments, "4040 - Jurídico"),
        "agencies": catalog_result(agencies),
    }


if __name__ == "__main__":
    print(json.dumps(run_diagnostic(), indent=2, ensure_ascii=False))
