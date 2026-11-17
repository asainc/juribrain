# BJN Demandas — Catálogos CSV e geração automática de parecer

Data: 2026-11-13. Escopo: módulo BJN/Demandas. Responsável pela homologação: equipe mantenedora, Jurídico e Segurança da Informação.

## Funcionalidades

1. **Departamento consultado primeiro:** a rota `/bjn/demandas/nova` apresenta um seletor, alimentado por `applications/bjn/data/cadastros/departamentos.csv`. A escolha **4040 - Jurídico** habilita a triagem original (ofícios/intimações etc.). Para outros departamentos é exibido aviso de encaminhamento ainda não configurado; nenhuma ação externa é realizada ou presumida.
2. **Solicitante:** substitui o texto “Departamento Solicitante” por **Solicitante** e utiliza a mesma lista corporativa CSV, sem digitação livre. A identificação da pessoa autenticada continua separada e aparece como **Usuário solicitante**.
3. **Agências no filtro:** os dados do autocomplete vêm de `applications/bjn/data/cadastros/agencias.csv`. O usuário pode escolher uma opção ou digitar **qualquer trecho** do número ou do nome; o SQL utiliza busca parcial `LIKE` com escape dos curingas `%`, `_` e `\\`, sempre com parâmetros. A agência registrada no cadastro pode ser selecionada a partir do mesmo catálogo, mas os cadastros antigos continuam consultáveis.
4. **Parecer automático:** quando o **advogado atribuído** abre pela primeira vez um protocolo que ainda não tenha rascunho, o frontend inicia automaticamente `POST /api/v3/bjn/demandas/{id}/parecer/rascunho`. O backend utiliza o text_generator conforme natureza e documentos. Reabertura não sobrescreve o rascunho. O rascunho não é publicado sem revisão humana explícita. Falhas deixam o editor disponível para parecer manual.

## Estrutura dos CSVs

Arquivo `applications/bjn/data/cadastros/departamentos.csv`:

```csv
departamento
4040 - Jurídico
```

Também aceita `codigo,nome` ou `numero_departamento,nome_departamento`. O código deve ter **exatamente quatro dígitos**; cada linha forma `NNNN - Nome`.

Arquivo `applications/bjn/data/cadastros/agencias.csv`:

```csv
numero_agencia,nome_agencia
```

Este arquivo é intencionalmente **sem agências reais**, porque o cadastro não foi fornecido. Preencha suas linhas, por exemplo utilizando valores sintéticos em homologação. O arquivo aceita `;` ou `,` como separador, cabeçalho `numero_agencia,nome_agencia` ou `numero,nome`, UTF-8 com ou sem BOM. Códigos precisam de quatro dígitos; duplicatas e linhas malformadas geram erro explícito de configuração. O backend não aceita CSV arbitrário enviado pelo navegador; somente arquivos configurados pelo servidor.

Para arquivos fora da pasta padrão, configure em `.env` (ou no gerenciador de configuração do ambiente):

```
BJN_DEPARTMENTS_CSV=/caminho/privado/departamentos.csv
BJN_AGENCIES_CSV=/caminho/privado/agencias.csv
```

Em Windows, utilize caminhos absolutos adequados ao servidor (por exemplo `C:\\diretorios\\bjn\\departamentos.csv`). Não registre catálogos de produção em Git. Se os arquivos forem substituídos, a próxima consulta a `/configuracao` utilizará a versão atual. Para atualizar a lista no navegador, recarregue a página.

## Arquitetura, segurança e compatibilidade

- Serviço leitor/validador: `applications/bjn/backend/services/bjn_directory.py`.
- Exposição controlada ao frontend: `GET /api/v3/bjn/demandas/configuracao`, campos `department_options` e `agency_options`.
- Campos novos: `consulted_department` em `DemandCreate` e em `bjn_demand_context`. Migração SQLite aditiva e idempotente, sem alteração dos dados anteriores.
- Validação no backend: o fluxo `/fluxo` em ambiente publicado exige departamentos existentes no CSV e consultado **4040 - Jurídico**. Para manter a suíte e a API local legadas, cadastros sem `consulted_department` permanecem aceitos **somente em APP_ENV=local**.
- A decisão de direcionar departamentos diferentes de 4040 fica pendente de especificação de canais pelo negócio; não se deve encaminhar material automaticamente sem autorização.
- O endpoint do parecer verifica a identidade do advogado responsável e a fase da demanda; não publica parecer em nome de administrador ou IA. Dados e documentos enviados ao modelo exigem tratamento de LGPD e regras de retenção definidas pela organização.
- O texto do parecer é proposta preliminar e não substitui validação do profissional jurídico.

## Verificação

Na raiz do projeto:

```bash
python -m pytest -q tests
cd frontend
npm test
npm run build
```

O build Angular exige pacotes npm do registry corporativo; testes estruturais isolados não o substituem. Cenários adicionais de homologação: catálogo corporativo completo, atualização de CSV em execução, acesso de usuários solicitante/advogado/gestor, PDF sem camada de texto, indisponibilidade do text_generator, pesquisas parciais, CPF protegido e não divulgação de parecer não publicado.

## Registro de decisões

- **Catálogo e não texto livre para departamento:** evita variações e erros de roteamento; exige governança do arquivo.
- **Um único CSV para origem e destino:** reduz inconsistência de nomenclatura entre telas.
- **Agência com busca parcial:** permite encontrar protocolos históricos que não utilizaram opções do novo catálogo.
- **Geração na abertura pelo advogado:** evita aumentar a latência da distribuição em lote e limita leitura/geração ao responsável autorizado. A chamada de IA não ocorre no navegador sem contexto autorizado.
- **Preservar revisão humana:** evita publicação automática de texto juridicamente não validado.
