"""Cria um módulo de exemplo sem editar a aplicação principal.

Todas as credenciais e o gpt_bradesco permanecem na raiz da plataforma.
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def create_scaffold(name: str, label: str) -> list[Path]:
    """Valida identificadores e evita sobrescrever qualquer módulo existente."""
    if not re.fullmatch(r"[a-z][a-z0-9_]{1,31}", name):
        raise ValueError("Identificador inválido: use 2–32 letras minúsculas, dígitos ou _.")
    if not re.fullmatch(r'[\wÀ-ÿ -]{2,80}', label.strip(), flags=re.UNICODE):
        raise ValueError("O título aceita somente letras, números, espaços, _ e - (2 a 80 caracteres).")
    label = label.strip()
    class_name = ''.join(part.capitalize() for part in name.split('_'))
    application_dir = PROJECT_ROOT / 'applications' / name
    frontend_dir = PROJECT_ROOT / 'frontend' / 'src' / 'app' / name
    package = f'applications.{name}.backend'

    # Cada arquivo é intencionalmente pequeno; o desenvolvedor acrescenta
    # validação de contratos, serviços e persistência após criar o esqueleto.
    targets: dict[Path,str] = {
        application_dir / '__init__.py': f'"""Produto {label}."""\n',
        application_dir / 'backend' / '__init__.py': f'"""API do produto {label}."""\n',
        application_dir / 'backend' / 'router.py': f'''"""Roteador de {label}: somente dados sintéticos no exemplo."""
from fastapi import APIRouter

router = APIRouter(prefix="/{name}", tags=[{label!r}])


@router.get("/saude")
def health() -> dict[str, str]:
    """Confirma que o roteador está registrado sem consultar serviços externos."""
    return {{"status": "ok", "module": {name!r}}}
''',
        application_dir / 'backend' / 'module.py': f'''"""Contrato de instalação do módulo {label}."""
from contextlib import asynccontextmanager
from typing import AsyncIterator
from fastapi import FastAPI
from {package}.router import router


class {class_name}Module:
    """Define o estado e o ciclo de vida sem criar instâncias corporativas."""
    key = {name!r}
    router = router

    def __init__(self, settings, bridge):
        """Recebe apenas dependências já configuradas pelo host."""
        self.settings = settings
        self.bridge = bridge

    def attach(self, app: FastAPI) -> None:
        """Adicione aqui dependências específicas, se necessárias."""
        return None

    @asynccontextmanager
    async def lifespan(self) -> AsyncIterator[None]:
        """Abra e feche recursos do módulo aqui, quando necessários."""
        yield
''',
        frontend_dir / f'{name}-page.component.ts': f'''/** Página de {label} integrada ao visual do ecossistema. */
import {{ Component }} from '@angular/core';
import {{ RouterLink }} from '@angular/router';

@Component({{
  selector: 'app-{name}-page', standalone: true, imports: [RouterLink],
  template: `<main class="ecosystem-home"><div class="ecosystem-container">
    <section class="ecosystem-intro"><div class="ecosystem-intro-copy">
      <span class="eyebrow">NOVA APLICAÇÃO</span>
      <h1>{label}</h1><p>Substitua pelo conteúdo do novo produto.</p>
      <a routerLink="/" class="ecosystem-primary-action">Voltar ao portal</a>
    </div></section>
  </div></main>`,
}})
export class {class_name}PageComponent {{}}
''',
        PROJECT_ROOT / 'tests' / f'test_{name}_integration.py': f'''"""Teste mínimo isolado de {label}, sem rede ou credenciais."""
from fastapi import FastAPI
from fastapi.testclient import TestClient
from {package}.module import {class_name}Module


def test_{name}_health():
    """Valida o contrato do endpoint recém-criado."""
    module = {class_name}Module(None, None)
    app = FastAPI()
    module.attach(app)
    app.include_router(module.router)
    with TestClient(app) as client:
        response = client.get("/{name}/saude")
        assert response.status_code == 200
        assert response.json() == {{"status": "ok", "module": {name!r}}}
''',
    }

    # A verificação ocorre ANTES de qualquer escrita para evitar sobrescrever
    # um módulo existente ou deixar parte de uma instalação incompleta.
    for target in targets:
        if target.exists():
            raise FileExistsError(f"Arquivo já existente: {target}. A operação não substitui código.")
    for target, content in targets.items():
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding='utf-8')
    return list(targets)


def main() -> None:
    """Expõe o utilitário de criação de produtos para o mantenedor."""
    parser = argparse.ArgumentParser(description="Gerar um esqueleto de aplicação")
    parser.add_argument('name', help='Identificador, por exemplo triagem')
    parser.add_argument('--label', required=True, help='Nome no menu, por exemplo Triagem')
    args = parser.parse_args()
    for target in create_scaffold(args.name, args.label):
        print(target.relative_to(PROJECT_ROOT))
    print('Registre o backend em applications/registry.py.')
    print('Registre a rota em frontend/src/app/app.routes.ts.')
    print('Adicione o item em frontend/src/app/core/application-registry.ts.')


if __name__ == '__main__':
    main()
