"""Testes com catálogo sintético, sem alterar o cadastro de produção."""
from __future__ import annotations

import os
from pathlib import Path

import pytest

from backend.services.bjn_directory import departments
from scripts.manage_bjn_departments import add_department, main


def test_add_department_updates_catalog(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Permite novos departamentos e mantém o destino jurídico existente."""
    csv_file = tmp_path / "departamentos.csv"
    csv_file.write_text("departamento\n4040 - Jurídico\n", encoding="utf-8")
    monkeypatch.setenv("BJN_DEPARTMENTS_CSV", str(csv_file))
    assert add_department("1234", "Departamento Fictício") == ["4040 - Jurídico", "1234 - Departamento Fictício"]
    assert departments() == ["4040 - Jurídico", "1234 - Departamento Fictício"]
    assert csv_file.read_text(encoding="utf-8").startswith("departamento\n")


def test_reject_duplicate_and_invalid_codes(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Rejeita duplicidade e códigos incorretos sem alterar o catálogo."""
    csv_file = tmp_path / "departamentos.csv"
    original = "departamento\n4040 - Jurídico\n"
    csv_file.write_text(original, encoding="utf-8")
    monkeypatch.setenv("BJN_DEPARTMENTS_CSV", str(csv_file))
    with pytest.raises(ValueError, match="já está cadastrado"):
        add_department("4040", "Outro nome")
    with pytest.raises(ValueError, match="quatro dígitos"):
        add_department("42", "Unidade")
    with pytest.raises(ValueError, match="nome"):
        add_department("1234", "")
    assert csv_file.read_text(encoding="utf-8") == original


def test_cli_lists_and_adds(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """O comando local utiliza o mesmo catálogo carregado pela aplicação."""
    csv_file = tmp_path / "departamentos.csv"
    csv_file.write_text("departamento\n4040 - Jurídico\n", encoding="utf-8")
    monkeypatch.setenv("BJN_DEPARTMENTS_CSV", str(csv_file))
    assert main(["add", "--code", "9999", "--name", "Unidade de Teste"]) == 0
    assert "9999 - Unidade de Teste" in capsys.readouterr().out
    assert main(["list"]) == 0
    assert "Departamentos cadastrados: 2" in capsys.readouterr().out


def test_reject_duplicate_codes_in_csv(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Nomes distintos não devem mascarar duplicação do código corporativo."""
    from backend.errors import ServiceError

    csv_file = tmp_path / "departamentos.csv"
    csv_file.write_text("departamento\n4040 - Jurídico\n4040 - Nome divergente\n", encoding="utf-8")
    monkeypatch.setenv("BJN_DEPARTMENTS_CSV", str(csv_file))
    with pytest.raises(ServiceError):
        departments()
