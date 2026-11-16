# Validação da integração Behavior — 16/11/2026

## Escopo e origem

- **Base preservada:** primeiro ZIP enviado (`ecossistema_juridico_bjn_rotulo_todos_status(2).zip`), com os ajustes recentes do BJN.
- **Fonte do módulo novo:** segundo ZIP (`Ecossistema_Juridico_Behavior_3_Projeto_Completo(1).zip`). O Behavior 3.0 foi migrado para `applications/behavior/backend`, `frontend/src/app/behavioral-lab` e seus prompts/documentação.
- **Pontos de acoplamento:** `applications/registry.py` (APIs), `frontend/src/app/core/application-registry.ts` (menu/home), `frontend/src/app/app.routes.ts` (rota lazy), `backend/central_environment.py` (ambiente).
- **Integração corporativa:** `gpt_bradesco.py` único na raiz; sem cópias de `.env` em subaplicações. Os módulos usam as mesmas variáveis de identidade, senha e Q&A. O valor do workflow não possui fallback efetivo nos JSONs dos produtos.

## Evidências de testes neste ambiente

| Verificação | Resultado | Escopo e observações |
|---|---|---|
| `python -m pytest -q tests` | **122 testes aprovados** na validação final | Backend, integração dos roteadores e configurações, Behavior V3 e regressão principal |
| `cd frontend && npm test` | **69 verificações aprovadas** | Testes estáticos/estruturais disponibilizados no repositório, não testes Angular E2E |
| `python scripts/validate_architecture.py` | **Aprovado** | Contratos de diretório, integração Bridge, distribuição do projeto |
| `cd frontend && npm run build` | **Não executável neste ambiente** | Dependências Angular (`@angular/core`, `@angular/cli`) ausentes de `node_modules`; executar em ambiente com `npm ci` autorizado |
| Teste live da Bridge corporativa | **Não executado** | Exige rede, credenciais e workflow corporativo válidos; não houve tentativa de chamadas reais |

**Observação sobre suítes históricas:** as pastas `applications/auditoria/tests_original` e `applications/chatbot/tests_original` são artefatos de projetos anteriores e não integram a suíte raiz. Uma tentativa de executá-las separadamente apresentou falhas de importação com namespaces legados (`backend.models`). Isso não foi corrigido nesta integração para evitar alteração não solicitada dos produtos originais. Teste as funcionalidades respectivas em homologação.

## Checklist obrigatório antes de publicação

1. Copiar `.env.example` para `.env`, configurar os valores **somente nesse arquivo** ou em um gerenciador de segredos aprovado e reiniciar a API. Não armazenar segredos no frontend ou no código versionado.
2. Instalar as dependências conforme README e compilar Angular (`npm ci` e `npm run build`, de acordo com o registry corporativo).
3. Validar rotas `/behavior`, `/bjn`, `/auditoria` e `/chatbot`; confirmar que o menu e os cartões estão consistentes.
4. Rodar uma simulação *demo* sintética, criar agentes/cenários/eventos, verificar conversas e replay e inspecionar exportação de resultados. Revisar persistência e limites.
5. Homologar separadamente as integrações reais de `text_generator` e Q&A, com dados sintéticos e usuários autorizados. Testar falhas de autenticação e workflow inválido.
6. Revisar segregação de acesso, logs, retenção, limites de uso, LGPD, conformidade e eventual validação jurídica antes da entrada em operação.

## Arquivos de orientação

- `docs/COMO_ADICIONAR_APLICACOES.md`: passo a passo de novos módulos e exemplo Triagem.
- `docs/BEHAVIOR_V3_GUIDE.md`: cenários, agentes, experimentos, módulos, endpoints e limites do Behavior.
- `docs/ARQUITETURA_ECOSSISTEMA.md`: decisões de extensão e configuração central.
- `scripts/scaffold_application.py`: criação do esqueleto de uma aplicação.
