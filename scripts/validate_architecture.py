"""Valida limites arquiteturais do Chatbot na aplicação jurídica integrada."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
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
    gpt = (CHATBOT_ROOT / "gpt_bradesco.py").read_text(encoding="utf-8")
    if "generate_text(" not in source or "text_generator" not in bridge:
        raise SystemExit("A análise documental deve continuar usando gpt_bradesco.text_generator.")
    if "answer_question(" not in chat or "agente_informacional" not in bridge or "def agente_informacional(" not in gpt:
        raise SystemExit("O chatbot deve usar gpt_bradesco.agente_informacional e retornar o campo answer.")
    # A separação de módulos evita acoplamento de contratos e regras financeiras.
    actual_applications = {folder.name for folder in (ROOT / "applications").iterdir() if folder.is_dir() and folder.name != "__pycache__"}
    if not {"chatbot", "auditoria"}.issubset(actual_applications) or not (ROOT / "backend" / "routers" / "bjn.py").is_file():
        raise SystemExit("Estrutura integrada de BJN, Auditoria e Chatbot está incompleta.")
    print("Arquitetura integrada validada: AI Ready isolado de BJN e Auditoria.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
