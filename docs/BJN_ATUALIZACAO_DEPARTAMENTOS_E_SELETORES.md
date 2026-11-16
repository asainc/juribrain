# BJN Demandas — Seleção de departamentos e atualização do catálogo

**Data:** 2026-11-16. **Escopo:** interface de cadastro e catálogo local de departamentos.

## Causa da lista limitada

O CSV incluído no projeto contém somente `4040 - Jurídico`. A interface não gera unidades automaticamente: os campos **Departamento consultado** e **Solicitante** recebem a lista aprovada do backend, por `GET /api/v3/bjn/demandas/configuracao`, atributo `department_options`.

## Adicionar departamentos

Na **raiz do projeto**, a forma mais segura é utilizar o comando local abaixo com **códigos e nomes verdadeiros e autorizados**. Os valores são exemplos fictícios:

```powershell
python scripts/manage_bjn_departments.py list
python scripts/manage_bjn_departments.py add --code 1234 --name "Departamento Exemplo"
```

O script consulta e atualiza `data/cadastros/departamentos.csv` ou o caminho autorizado pela variável `BJN_DEPARTMENTS_CSV`. Evita códigos repetidos, valida o formato e grava o arquivo por substituição atômica. Requer permissão de escrita; faça backup antes de atualizações corporativas. Não altere o CSV diretamente em múltiplos processos ao mesmo tempo.

Alternativamente, edite o CSV como texto UTF-8:

```csv
departamento
4040 - Jurídico
1234 - Departamento Exemplo
5678 - Unidade Exemplo
```

São aceitos os cabeçalhos `departamento`, `codigo,nome` ou `numero_departamento,nome_departamento` (delimitador `,` ou `;`). Cada código deve conter quatro dígitos, ser único e estar acompanhado de nome não vazio. Não inclua dados pessoais, senhas ou credenciais.

## Usar os novos valores

1. Salve o CSV no caminho do backend. Caso tenha definido `BJN_DEPARTMENTS_CSV`, edite esse arquivo, **não** o arquivo-modelo padrão.
2. Na tela **Nova demanda**, clique em **Atualizar lista**. Também é possível atualizar a página. O backend lê o CSV novamente em cada requisição.
3. Abra **Departamento consultado** ou **Solicitante** e clique na opção desejada, ou procure digitando parte do código ou do nome. Use Enter para confirmar a opção destacada. Digitação sem escolha válida não efetiva a seleção.
4. O campo **Solicitante** aceita qualquer unidade aprovada no CSV. O campo **Departamento consultado** também apresenta as unidades, porém o fluxo operacional configurado atende somente `4040 - Jurídico`.

## Segurança e limitações

- A interface não permite criar registros pelo navegador; inclusão de unidades é uma ação administrativa local que deve seguir a governança dos cadastros.
- Escolher outro departamento consultado não encaminha uma demanda automaticamente. O negócio precisa definir a rota e as permissões antes de habilitar esses fluxos.
- O botão **Atualizar lista** preserva o formulário, mas limpa escolhas que tenham sido excluídas do cadastro.
- O seletor foi alterado para opções acionadas por botão, com confirmação única no clique, além de busca ao focar/clicar no campo.
- Os testes estruturais não substituem teste visual e funcional com o Angular compilado no navegador.

## Registro de decisões

- **Um CSV controlado pelo servidor:** evita edição não autorizada de rotas pelo frontend.
- **Inclusão atômica com validação:** reduz o risco de catálogo parcial ou duplicado.
- **Atualização sem perda de formulário:** permite disponibilizar novos cadastros durante a sessão.
- **Bloqueio de outros destinos:** preserva o escopo aprovado para o fluxo jurídico até decisão de negócio.
