"""Fonte única de credenciais para todas as aplicações da plataforma."""
from __future__ import annotations

import os
from pathlib import Path

from starlette.config import Config

ROOT = Path(__file__).resolve().parents[1]


def environment_file_path(root: Path | None = None) -> Path:
    """Resolve o único .env relativo à raiz, mesmo fora da pasta do projeto."""
    base = root if root is not None else ROOT
    raw = os.environ.get("APP_ENV_FILE", "").strip()
    candidate = Path(raw).expanduser() if raw else base / ".env"
    resolved = (base / candidate if not candidate.is_absolute() else candidate).resolve()
    if raw and not resolved.is_file():
        raise ValueError("APP_ENV_FILE aponta para arquivo inexistente; revise o caminho.")
    return resolved


def read_environment_file(root: Path | None = None) -> dict[str, str]:
    """Carrega configurações sem publicar segredos em os.environ ou em logs."""
    path = environment_file_path(root)
    return Config(path if path.is_file() else None, environ={}, encoding="utf-8-sig").file_values
