"""Valida limites arquiteturais do Chatbot na aplicação jurídica integrada."""
from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
CHATBOT_ROOT = ROOT / "applications" / "chatbot"
EXPECTED_BACKEND_ROUTERS = {"__init__.py", "processes.py"}
EXPECTED_AI_SERVICES = {
    "__init__.py",
    "bradesco_bridge.py",
    "chat_service.py",
    "pdf_text_extractor.py",
    "process_intelligence.py",
    "prompt_loader.py",
    "workspace_store.py",
}


def main() -> int:
    """Confirma que a árvore executável corresponde ao escopo documental atual."""
    routers = {path.name for path in (CHATBOT_ROOT / "backend" / "routers").glob("*.py")}
    services = {path.name for path in (CHATBOT_ROOT / "backend" / "services").glob("*.py")}
    if routers != EXPECTED_BACKEND_ROUTERS:
        raise SystemExit(f"Routers inesperados no backend: {sorted(routers - EXPECTED_BACKEND_ROUTERS)}")
    if services != EXPECTED_AI_SERVICES:
        raise SystemExit(f"Serviços inesperados no backend: {sorted(services - EXPECTED_AI_SERVICES)}")

    source = (CHATBOT_ROOT / "backend" / "services" / "process_intelligence.py").read_text(encoding="utf-8")
    bridge = (CHATBOT_ROOT / "backend" / "services" / "bradesco_bridge.py").read_text(encoding="utf-8")
    chat = (CHATBOT_ROOT / "backend" / "services" / "chat_service.py").read_text(encoding="utf-8")
    gpt = (ROOT / "gpt_bradesco.py").read_text(encoding="utf-8")
    if "generate_text(" not in source or "text_generator" not in bridge:
        raise SystemExit("A análise documental deve continuar usando gpt_bradesco.text_generator.")
    if "answer_question(" not in chat or "agente_informacional" not in bridge or "def agente_informacional(" not in gpt:
        raise SystemExit("O chatbot deve usar gpt_bradesco.agente_informacional e retornar o campo answer.")
    # A separação de módulos evita acoplamento de contratos e regras financeiras.
    actual_applications = {folder.name for folder in (ROOT / "applications").iterdir() if folder.is_dir() and folder.name != "__pycache__"}
    if not {"bjn", "chatbot", "auditoria", "behavior"}.issubset(actual_applications):
        raise SystemExit("Aplicações obrigatórias ausentes no diretório applications/.")

    # Nenhuma regra de negócio BJN deve continuar no host FastAPI.
    bjn_root = ROOT / "applications" / "bjn"
    bjn_required = (
        bjn_root / "backend" / "module.py",
        bjn_root / "backend" / "routers" / "bjn.py",
        bjn_root / "backend" / "routers" / "bjn_demands.py",
        bjn_root / "backend" / "services" / "bjn_demand_store.py",
        bjn_root / "config" / "bjn_script_workflow.json",
        bjn_root / "config" / "catalogo_clausulas_bjn.xlsx",
        bjn_root / "prompts" / "naturezas" / "inventario.system.md",
        bjn_root / "data" / "cadastros" / "departamentos.csv",
    )
    if not all(path.is_file() for path in bjn_required):
        raise SystemExit("O pacote BJN não contém todos os componentes obrigatórios.")
    if list((ROOT / "backend" / "services").glob("bjn_*.py")) or list((ROOT / "backend" / "routers").glob("bjn*.py")):
        raise SystemExit("Serviços e roteadores do BJN devem existir apenas em applications/bjn/backend.")
    from applications.registry import api_extensions
    from backend.config import Settings
    from backend.services.bradesco_bridge import BradescoBridgeClient
    settings = Settings()
    extensions = api_extensions(settings, BradescoBridgeClient(settings))
    if [extension.key for extension in extensions] != ["bjn", "behavior"]:
        raise SystemExit("BJN e Behavior precisam estar registrados como extensões da API.")
    print("Arquitetura integrada validada: AI Ready, BJN, Auditoria e Behavior registrados.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
