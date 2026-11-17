# BJN — backend e recursos de domínio

Este diretório contém o BJN completo e segue o mesmo contrato de módulo de
`applications/behavior`. A API pública existente permanece sob `/api/v3/bjn`.

```text
applications/bjn/
├── backend/
│   ├── module.py                  injeta dependências, conecta ao host
│   ├── routers/                   contratos HTTP de minutas e demandas
│   └── services/                  decisões, persistência e integração do domínio
├── config/                        questionário, mapeamento e catálogo Excel
├── data/cadastros/                catálogos de departamentos e agências
├── evidence/                      fontes e imagens íntegras das cláusulas
└── prompts/                       prompts específicos da natureza jurídica
```

**Como funciona:** `backend.principal.create_app()` lê as configurações do
`.env` central, cria `BradescoBridgeClient` e solicita o módulo BJN a
`applications.registry.api_extensions`. O host chama `attach(app)`, injeta o
`DemandStore` e serviços de IA no estado FastAPI e monta as rotas com autorização.

**Arquivos privados:** o banco SQLite e os uploads continuam no diretório
configurado por `bjn_database_path`/`bjn_upload_directory`, por padrão
`.runtime/bjn`. Nenhuma migração de dados do SQLite é exigida. Preserve as pastas
privadas existentes ao atualizar. O CSV de agência fornecido neste pacote é
apenas um template; configure arquivos autorizados externamente caso necessário.

**Testes:** `python -m pytest -q tests/test_bjn*.py` e
`python -m pytest -q tests/test_bjn_module_architecture.py`.

Não altere a matriz jurídica, catálogos homologados ou regras do questionário
sem validação do Jurídico/Compliance e controle de versão da fonte original.
