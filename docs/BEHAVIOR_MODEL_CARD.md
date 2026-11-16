# Model card — Behavior / agentes sintéticos

| Campo | Situação documentada |
|---|---|
| Sistema | Behavior 3.0 — motor multiagente com opção demonstrativa ou `gpt_bradesco.text_generator` |
| Data | 2026-11-12 |
| Uso pretendido | Exploração de cenários hipotéticos, teste de integração, comparação de reações sintéticas e ensino de experimentação |
| Não utilizar | Decisão automatizada sobre pessoas, concessão de crédito, políticas públicas reais, interpretação jurídica, previsão de mercados reais, testes regulatórios sem homologação |
| Dados de treino | **Não aplicável** ao motor demo; as regras são programadas. Dados de treinamento do modelo corporativo não foram fornecidos nem verificados. |
| População | Perfis inteiramente fictícios, descritos por atributos livres, objetivos e parâmetros sociais |
| Evidências disponíveis | Testes unitários e de integração sintéticos; sem validação preditiva contra amostras reais |
| Métricas técnicas | Reações estruturadas, eventos por rodada, limites, comparação de médias sintéticas, métricas tipadas quando configuradas |
| Métricas de validade externa | Não medidas. A comparação agregada opcional é diagnóstica, não um laudo de validação. |
| Explicabilidade | Snapshot, mensagens, ação, `reason` gerado, grafo e eventos. Justificativas de LLM não são provas causais de processos internos. |
| Riscos conhecidos | Generalizações não comprovadas, viés de prompts, alucinações, sensibilidade a parâmetros, prompt injection, falsa precisão de simulações |
| Calibração | Não realizada; requer conjunto agregado de validação apropriado, amostragem, testes de viés e aprovação de governança |
| Drift | Comparação entre runs de mesma configuração de ambiente com limite escolhido pelo usuário; não representa drift de dados de produção |
| Reprodutibilidade | Seed demo, snapshots, eventos e hashes; não garantida no LLM mesmo com temperatura/seed iguais |
| Status de homologação | Pendente validação da Bridge, build Angular no ambiente-alvo, revisão de segurança e controle de acesso |
| Responsável técnico | A definir pela equipe proprietária |
| Próxima revisão | Antes da implantação corporativa ou de qualquer mudança de modelo/prompt/dados/uso pretendido |

O **Behavior não possui desempenho preditivo aferido**. Nenhuma métrica apresentada nesta ficha deve ser interpretada como acurácia, fairness, causalidade ou representatividade comprovada.
