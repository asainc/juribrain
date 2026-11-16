"""Consulta e acrescenta departamentos aprovados ao catálogo CSV local do BJN.

Exemplos:
    python scripts/manage_bjn_departments.py list
    python scripts/manage_bjn_departments.py add --code 1234 --name "Unidade de exemplo"

O script não altera bancos de dados, permissões ou regras de roteamento.
"""
from __future__ import annotations

import argparse
import csv
import os
import re
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.services.bjn_directory import DATA_ROOT, departments  # noqa: E402


def catalog_path() -> Path:
    """Retorna o catálogo efetivamente utilizado pela API, respeitando o ambiente."""
    configured = os.getenv("BJN_DEPARTMENTS_CSV", "").strip()
    return Path(configured).expanduser() if configured else DATA_ROOT / "departamentos.csv"


def add_department(code: str, name: str) -> list[str]:
    """Valida a unidade, impede códigos repetidos e regrava o CSV atomicamente."""
    code = code.strip()
    name = name.strip()
    if not re.fullmatch(r"\d{4}", code):
        raise ValueError("O código do departamento deve conter exatamente quatro dígitos.")
    if not name or len(name) > 110 or "\n" in name or "\r" in name:
        raise ValueError("Informe um nome de departamento válido (1 a 110 caracteres, sem quebras de linha).")
    entry = f"{code} - {name}"
    existing = departments()
    if any(value[:4] == code for value in existing):
        raise ValueError("Este código já está cadastrado. Não foram feitas alterações.")
    updated = [*existing, entry]
    destination = catalog_path()
    if not destination.is_file():
        raise ValueError("O catálogo não existe. Nenhuma alteração foi realizada.")

    # O arquivo temporário é criado na mesma pasta para permitir troca atômica.
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", newline="", dir=destination.parent,
            prefix=".departamentos-", suffix=".tmp", delete=False,
        ) as stream:
            temporary = Path(stream.name)
            writer = csv.writer(stream, lineterminator="\n")
            writer.writerow(["departamento"])
            for value in updated:
                writer.writerow([value])
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, destination)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return updated


def main(argv: list[str] | None = None) -> int:
    """Oferece operações locais controladas, sem endpoints para alterações no navegador."""
    parser = argparse.ArgumentParser(description="Administração local do catálogo de departamentos BJN")
    sub = parser.add_subparsers(dest="action", required=True)
    sub.add_parser("list", help="Exibir departamentos disponíveis")
    add = sub.add_parser("add", help="Incluir departamento aprovado")
    add.add_argument("--code", required=True, help="Código de quatro dígitos")
    add.add_argument("--name", required=True, help="Nome oficial")
    options = parser.parse_args(argv)
    try:
        values = departments() if options.action == "list" else add_department(options.code, options.name)
    except Exception as exc:
        # O texto completo do CSV e possíveis caminhos sensíveis não são exibidos.
        if isinstance(exc, ValueError):
            print(f"Erro: {exc}", file=sys.stderr)
        else:
            print("Erro: não foi possível consultar ou atualizar o catálogo. Verifique o CSV e as permissões.", file=sys.stderr)
        return 1
    print(f"Departamentos cadastrados: {len(values)}")
    for value in values:
        print(value)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
