# Diagnóstico de falha HTTP 5xx no cadastro de demandas BJN

## O que foi constatado

A mensagem `O servidor não conseguiu concluir o cadastro. Identificador: ...` corresponde a uma resposta HTTP 5xx. O identificador é uma referência de correlação da requisição, **não revela a causa técnica**. Sem o log correspondente do ambiente do usuário, não é possível afirmar qual condição originou a ocorrência.

Na revisão de código, havia um cenário concreto de risco: uma exceção imprevista na classificação de PDF ou geração de sugestão documental, executadas **depois do commit da demanda**, podia causar erro HTTP 500 apesar de existir um protocolo salvo. Esse ponto foi corrigido e testado com falhas sintéticas. Não significa que tenha sido necessariamente a origem do erro informado.

## Fluxo de cadastro atualizado

1. Validação do formulário, prova de triagem e vínculo ao departamento consultado.
2. Recepção e checagem dos anexos, com retorno controlado se o diretório de uploads estiver inacessível.
3. Gravação transacional no banco SQLite. Falhas de banco ocupado ou banco indisponível retornam erro estruturado. Não existe criação parcial.
4. Resposta de sucesso com o protocolo. A classificação da natureza e a sugestão documental são **operações auxiliares**: se falharem após o commit, a resposta de cadastro não é substituída por erro genérico. A interface deve apontar a necessidade de revisão manual.
5. Logs registram `request_id`, `stage`, `error_type` ou `error_code`, sem CPF, conteúdo de PDF, SQL nem credenciais.

## Verificação no ambiente Windows

Na pasta raiz `ecossistema-juridico`, execute com o mesmo Python do backend:

```powershell
python scripts/diagnose_bjn_registration.py
```

O diagnóstico retorna somente códigos e contagens de departamentos/agências, sem exibir nomes, caminhos ou segredos. `DATABASE_MISSING` em uma instalação ainda sem cadastros pode ser esperado. Se a aplicação já tinha dados, verifique a configuração `BJN_DATABASE_PATH` com o responsável pela implantação antes de iniciar uma base nova.

- `DATABASE_BUSY`: SQLite ocupado por outro processo; encerre instâncias duplicadas após preservar os trabalhos em andamento.
- `DATABASE_UNAVAILABLE`/`SCHEMA_INCOMPLETE`: revisar versão do backend, banco e migrações; **não apague o arquivo SQLite**.
- `UPLOAD_STORAGE_UNAVAILABLE`/`NOT_WRITABLE`: conferir permissões de gravação e espaço disponível nos diretórios configurados.
- `DIRECTORY_UNAVAILABLE`/`DIRECTORY_INVALID`: verificar o CSV corporativo e seu esquema, sem publicar listas completas em logs.
- `bjn_post_registration_analysis_failed`: o cadastro já foi realizado; revisar a integração do serviço de IA e o protocolo gerado.
- `request_failed` com `stage=registration_persistence`: recuperar a classe `error_type` registrada no backend e correlacionar com o identificador completo da requisição.

**Importante:** antes de repetir um cadastro após erro 5xx, verifique em *Todas as demandas* se ele já foi registrado para evitar duplicidade. Não compartilhe conteúdo de processos, CPF, arquivos `.env`, tokens, bancos ou rastros completos contendo dados sensíveis para diagnóstico.

## Limitações e homologação

Foram executados testes Python com bancos e documentos sintéticos e testes estruturais de frontend. Não foi reproduzida a falha original do ambiente do usuário, nem executada integração corporativa real. A compilação Angular integral requer pacotes npm instalados. Em produção, a adoção de SQLite como banco operacional e os controles de armazenamento dependem de homologação de infraestrutura, segurança e DPO.
