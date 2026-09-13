---
name: dataset-fluig
description: Cria ou refatora datasets customizados do Fluig (datasets/ds_*.js) em ECMA5/Rhino, com JSDoc, exibeErro/createErrorStructure e valorNulo em Osync. Use ao criar ou padronizar um dataset. Se o projeto tiver Query Store própria, seguir o AGENTS.md do cliente — não inventar endpoint.
---

# Datasets Fluig — scaffold e refatoração (projeto Fluig)

Padroniza a criação e a refatoração de datasets customizados (`datasets/ds_*.js`) do
projeto Fluig. Escolhe o **tipo** de dataset e a **fonte de dados** correta, gera o
esqueleto no padrão do projeto e aplica todas as convenções obrigatórias (ECMA5/Rhino,
JSDoc, validação de constraints, tratamento de erro, `valorNulo` em Osync).

> Regras permanentes deste plugin: [AGENTS.md](../../AGENTS.md). O `AGENTS.md` do cliente vence em integração e nomes.

## Uso

```
/dataset-fluig novo ds_nome          → cria um dataset novo do zero
/dataset-fluig refatorar ds_nome     → traz um dataset existente ao padrão
/dataset-fluig ds_nome               → detecta: refatora se existir, senão cria novo
```

Se `ds_nome` não vier, **perguntar** o nome (prefixo `ds_` obrigatório, snake_case).

## Regra fundamental (inegociável)

Arquivos em `datasets/` rodam no **Rhino (ECMA 5)**. **Nunca** usar `let`/`const`,
arrow functions, template literals, `for...of`, destructuring, `class`, spread.
Usar sempre `var`, `function(){}`, concatenação com `+`, laço `for` indexado.

## Fluxo

### 1. Decidir TIPO e FONTE (perguntar se não estiver claro)

Duas decisões definem o template. Se o pedido do usuário não deixar ambas claras,
usar AskUserQuestion.

**TIPO de dataset:**

| Tipo | Quando usar | Estrutura |
|---|---|---|
| **on-demand** (`createDataset`) | consulta com filtros dinâmicos, sob demanda | `createDataset(fields, constraints, sortFields)` retornando `DatasetBuilder.newDataset()` |
| **Osync** | dados sincronizados por schedule, com cache local no Fluig | `defineStructure()` + `onSync(lastSyncDate)` + `createDataset` + `onMobileSync` |

**FONTE de dados:**

| Fonte | serviceCode / origem | Padrão |
|---|---|---|
| **Protheus — SQL direto** | `REST_PROTHEUS` `/FLGSELECT/EXECQUERY/SELECT` | SQL em `params.execquery` |
| **Protheus — REST / Query Store** | `REST_PROTHEUS` endpoint do cliente | Seguir o `AGENTS.md` do projeto (não inventar path) |
| **Sistema acadêmico (CSV)** | serviço cadastrado + `consultaDinamicaParams` | GET, parse de `vo.getResult()` se status 200 |
| **Fluig REST** | `fluig_rest` | ex. `/portal/api/rest/wcm/...` |
| **Dataset interno Fluig** | `DatasetFactory.getDataset` | `workflowProcess`, `colleague`, `processHistory` |

> Integrações com path específico do cliente (Query Store, Lyceum, etc.)
> ficam no `AGENTS.md` do repositório — não copiar endpoint de outro tenant.

### 2. Escrever o cabeçalho JSDoc (obrigatório, sempre primeiro)

Bloco JSDoc **antes** da função principal, no padrão do AGENTS.md:

```js
/**
 * Dataset: ds_nome                (idêntico ao nome do arquivo)
 * Projeto: <nome do projeto>
 * Versão: 1.0                     (incrementar em refatoração: 1.0 → 2.0)
 * Tipo: Osync                     (só quando for Osync)
 *
 * Descrição:
 * <o que consulta, qual serviço/endpoint, formato do retorno>
 *
 * Constraints esperadas:
 * - nome: descrição. Obrigatório | Opcional. (formato p/ datas: dd/MM/yyyy HH:mm:ss)
 *
 * Estrutura de retorno (colunas):
 * - COLUNA1: descrição
 * - COLUNA2: descrição
 */
```

`Constraints esperadas` lista **todas** as constraints lidas no código, marcando as
opcionais. `Estrutura de retorno` segue **a ordem** dos `addColumn`.

### 3. Montar o corpo no padrão do projeto

Copiar fielmente o dataset de referência da fonte escolhida (tabela acima). Pontos fixos:

**Objeto `init`** centralizando config (datasetName, fluigService, endpoint, method,
columns e — quando aplicável — primaryKey/Index/params). Ver `ds_itensplanilha_sql.js`.

**Extração de constraints** — laço sobre `constraints[i].fieldName` /
`constraints[i].initialValue` (ou `getFieldName()`/`getInitialValue()`). Inicializar
cada filtro com `''`.

**Validar constraints obrigatórias** — antes de chamar o serviço, se um filtro
obrigatório vier vazio, `return exibeErro("Constraint obrigatória ausente: X", "...")`.
Ver `ds_cancelar_processo.js`. Filtros opcionais seguem como `''`.

**Invoke** via `fluigAPI.getAuthorizeClientService()` + `service.invoke(new
org.json.JSONObject(options).toString())`, com `timeoutService: '100'` e
`headers: { Connection: 'close' }`. (Fonte Lyceum: GET direto, ver `ds_lyceum_cursos.js`.)

**Parse + preenchimento** — iterar o array de resultado (`data.result[]`,
`data.items[]`, `objdata.invdata[]` conforme a fonte) e `dataset.addRow([...])`.
Fazer null-check em cada valor: `(v != null) ? String(v).trim() : ''`.

**Tratamento de erro** — `try/catch` em torno da chamada. No `catch`:
`log.error('Error to execute dataset "' + init.datasetName + '": ' + e.message)` e
retornar estrutura de erro. Dois formatos de erro coexistem no projeto — escolher **um**
por dataset e ser consistente:
- `exibeErro(msg, detalhes)` → colunas ERRO/MSG/DETALHES (bom quando o form/consumidor
  exibe a mensagem). Ver `ds_cancelar_processo.js`.
- `createErrorStructure()` → coluna única `error`. Ver `ds_itensplanilha_sql.js`.

Preferir `exibeErro()` quando houver validação de constraint (mantém um só padrão no
arquivo).

### 4. Especificidades por TIPO

**Osync** — além do `createDataset`, implementar:
- `defineStructure()`: `addColumn(nome, DatasetFieldType.STRING)`, `setKey([...])`,
  `addIndex([...])`.
- `onSync(lastSyncDate)`: montar via `createStructure()`, popular com `addOrUpdateRow`,
  e remover registros ausentes com `deleteRow` (padrão de reconciliação por primaryKey).
- `onMobileSync(user)`.
- **Usar `valorNulo(valor)`** em todo valor antes do `addOrUpdateRow` — evita `null`.
  Ver `ds_cursos_gOfertas.js`.

**on-demand** — apenas `createDataset` (os stubs `defineStructure`/`onSync`/
`onMobileSync` vazios são opcionais; incluir só se o padrão do arquivo-base os tiver).

### 5. Helpers reutilizáveis (copiar dos datasets existentes, não reinventar)

| Helper | O que faz | Referência |
|---|---|---|
| `exibeErro(msg, detalhes)` | dataset de erro ERRO/MSG/DETALHES + log | `ds_cancelar_processo.js` |
| `createErrorStructure()` | dataset de erro coluna `error` | `ds_itensplanilha_sql.js` |
| `valorNulo(valor)` | troca null por '' (Osync) | `ds_cursos_gOfertas.js` |
| `converteDataParaFluig` | `yyyy-MM-dd` → `dd/MM/yyyy HH:mm:ss` | `ds_bi_processos.js` |

### 6. Entregar ao usuário

Resumo final deve conter:
1. Tipo + fonte escolhidos e o dataset de referência copiado.
2. Constraints (obrigatórias/opcionais) e colunas de retorno.
3. Se o projeto tiver skill/docs de Query Store ou documentação de dataset, apontar.

## Checklist final (validar antes de entregar)

- [ ] Arquivo em `datasets/`, prefixo `ds_`, snake_case; nome do arquivo = `Dataset:` no JSDoc
- [ ] 100% ECMA 5 (sem let/const/arrow/template literal/for-of/destructuring/class/spread)
- [ ] Cabeçalho JSDoc completo (Dataset, Projeto, Versão, Tipo se Osync, Descrição, Constraints, Colunas na ordem)
- [ ] Constraints obrigatórias validadas com `exibeErro()`; opcionais toleram vazio
- [ ] Invoke com `org.json.JSONObject(options).toString()`, timeout e `Connection: close` (fontes REST)
- [ ] Null-check em cada valor gravado; `valorNulo()` se Osync
- [ ] `try/catch` com `log.error("<nome do dataset> - ...")` e estrutura de erro consistente (um só padrão)
- [ ] Osync: `defineStructure`/`onSync`/`onMobileSync` implementados; reconciliação por primaryKey
- [ ] Endpoints e serviceCodes batem com o `AGENTS.md` do projeto
