# Execução de testes — Hub Processual

Data: 2026-10-29 (America/Sao_Paulo).

- Suíte Python completa: 70 testes aprovados, incluindo 4 testes novos com PDFs e respostas sintéticos.
- Testes de frontend com Node: 36 aprovados, incluindo verificação sintática de TypeScript dos componentes alterados.
- `python scripts/validate_architecture.py`: passou após corrigir o validador para apontar para a subaplicação Chatbot, não para o backend BJN.
- `python -m compileall`: passou.

**Não medido / não executado:** build Angular com dependências reais, ensaio de ponta a ponta por browser, execução do gerador corporativo, testes com documentos reais autorizados, medição de alucinação e qualidade das referências. O ambiente de construção não contém `node_modules` e o download de dependências não foi concluído; portanto testes estruturais não substituem `npm run build` na estação do usuário.

## Roteiro de homologação

1. Configurar conectividade e credenciais autorizadas do `text_generator` no backend Chatbot.
2. Executar `npm run setup`, `npm run doctor` e `npm run build` dentro de `frontend`.
3. Iniciar API e Angular conforme `docs/INSTALACAO.md` e navegar até `/chatbot`.
4. Enviar PDF cível sintético e PDF trabalhista sintético, em análises distintas; inspecionar campos e links para páginas.
5. Exercitar busca textual e pergunta contextual; confirmar com os PDFs originais e testar ausência de resultados.
6. Confirmar que o chat flutuante continua separado do contexto documental.
7. Encerrar sessão e conferir exclusão do workspace; verificar políticas de retenção e exportação com Segurança e Jurídico.
