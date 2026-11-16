"""Consulta catálogos CSV aprovados, sem expor arquivos privados ao navegador."""
from __future__ import annotations

import csv
import os
import re
from pathlib import Path

from backend.errors import ServiceError

DATA_ROOT = Path(__file__).resolve().parents[2] / "data" / "cadastros"
DEPARTMENT_PATTERN = re.compile(r"^\d{4} - \S.{0,113}$")
AGENCY_CODE_PATTERN = re.compile(r"^\d{4}$")
MAX_ROWS = 20_000


def _source(environment_key: str, filename: str) -> Path:
    """Local padrão é substituível por caminho privado de ambiente."""
    configured = os.environ.get(environment_key, "").strip()
    return Path(configured).expanduser() if configured else DATA_ROOT / filename


def _rows(path: Path) -> tuple[list[str], list[list[str]]]:
    """Lê CSV em UTF-8 com BOM opcional e identifica vírgula/ponto-e-vírgula."""
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            header = handle.readline()
            if not header:
                raise ValueError("Arquivo sem cabeçalho")
            delimiter = ";" if header.count(";") > header.count(",") else ","
            handle.seek(0)
            reader = csv.reader(handle, delimiter=delimiter, strict=True)
            headings = [part.strip().lower() for part in next(reader)]
            data = []
            for line_number, row in enumerate(reader, start=2):
                if not any(part.strip() for part in row):
                    continue
                if len(data) >= MAX_ROWS:
                    raise ValueError("Limite de registros excedido")
                if len(row) != len(headings):
                    raise ValueError(f"Quantidade de colunas inválida na linha {line_number}")
                data.append([part.strip() for part in row])
            return headings, data
    except (OSError, UnicodeError, csv.Error, ValueError) as exc:
        # Erro técnico identificado sem retornar conteúdo do catálogo ou caminhos locais.
        raise ServiceError("Cadastro corporativo indisponível ou inválido; consulte a administração.", 503, code="DIRECTORY_UNAVAILABLE") from exc


def departments() -> list[str]:
    """Retorna valores `NNNN - Nome` únicos, prontos para a lista suspensa."""
    headings, rows = _rows(_source("BJN_DEPARTMENTS_CSV", "departamentos.csv"))
    if headings not in (["departamento"], ["codigo", "nome"], ["numero_departamento", "nome_departamento"]):
        raise ServiceError("Cabeçalho de departamentos inválido.", 503, code="DIRECTORY_INVALID")
    values = [row[0] if len(row) == 1 else f"{row[0]} - {row[1]}" for row in rows]
    if (any(not DEPARTMENT_PATTERN.fullmatch(value) for value in values)
            or len(values) != len(set(values))
            or len({value[:4] for value in values}) != len(values)):
        raise ServiceError("Registros de departamentos inválidos ou duplicados.", 503, code="DIRECTORY_INVALID")
    return values


def agencies() -> list[str]:
    """Forma o rótulo de exibição a partir das duas colunas obrigatórias."""
    headings, rows = _rows(_source("BJN_AGENCIES_CSV", "agencias.csv"))
    if headings not in (["numero_agencia", "nome_agencia"], ["numero", "nome"]):
        raise ServiceError("Cabeçalho de agências inválido.", 503, code="DIRECTORY_INVALID")
    if any(not AGENCY_CODE_PATTERN.fullmatch(code) or not name or len(name) > 110 for code, name in rows):
        raise ServiceError("Registros de agências inválidos.", 503, code="DIRECTORY_INVALID")
    numbers = [code for code, _ in rows]
    if len(numbers) != len(set(numbers)):
        raise ServiceError("Códigos de agências duplicados.", 503, code="DIRECTORY_INVALID")
    return [f"{code} - {name}" for code, name in rows]
