---
name: dataset-fluig
description: Cria ou refatora datasets customizados do Fluig (datasets/ds_*.js) em ECMA5/Rhino, com JSDoc, exibeErro/createErrorStructure e valorNulo em Osync; inclui datasets de ação (saveAndSendTask, startProcess). Use ao criar, auditar ou padronizar um dataset. Se o projeto tiver Query Store própria, seguir o AGENTS.md do cliente — não inventar endpoint.
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
| **Ação** | dataset chamado para executar algo no workflow (mover ou abrir solicitação) | `createDataset` usando `ECMWorkflowEngineService` (ver seção 4) |

**FONTE de dados:**

| Fonte | serviceCode / origem | Padrão |
|---|---|---|
| **ERP via SQL / REST** | serviço cadastrado no Fluig (ex.: `REST_SERVICO`) | endpoint, corpo e formato da resposta vêm do `AGENTS.md` do projeto |
| **Query Store do cliente** | serviço do cliente | Seguir o `AGENTS.md` do projeto (não inventar path) |
| **Sistema externo com retorno CSV/JSON** | serviço cadastrado + endpoint do cliente | GET, parse de `vo.getResult()` se `vo.getHttpStatusResult() == 200` |
| **Fluig REST** | `fluig_rest` | ex. `/portal/api/rest/wcm/...`, `/api/public/ecm/dataset/search` |
| **Dataset interno Fluig** | `DatasetFactory.getDataset` | `workflowProcess`, `colleague`, `processHistory` |

> Integrações com path específico do cliente (Query Store, sistemas externos etc.)
> ficam no `AGENTS.md` do repositório — não copiar endpoint de outro tenant.
> Se o `AGENTS.md` do cliente indicar um dataset de referência para a fonte,
> copiar o padrão dele.

> Assinaturas exatas de `DatasetFactory.getDataset` / `createConstraint` e
> `ConstraintType`: `context/architecture.md`, seção "API pública de Dataset —
> assinaturas". Para ler linhas de pai-filho de um formulário (constraints
> `documentid` + `tablename` + `metadata#active`): `context/conventions.md`,
> seção "Consumo via Dataset".

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

Exemplo completo de dataset on-demand (dataset interno + `exibeErro`):
[`examples/reference_dataset.js`](examples/reference_dataset.js).

### 3. Montar o corpo no padrão do projeto

Se o projeto já tiver um dataset da mesma fonte (ou o `AGENTS.md` do cliente indicar
um de referência), copiar o padrão dele. Pontos fixos:

**Objeto `init`** centralizando config:

```js
var init = {
    datasetName: 'ds_exemplo',
    fluigService: 'REST_SERVICO',          // serviceCode cadastrado no Fluig
    endpoint: '/caminho/do/endpoint',      // do AGENTS.md do cliente
    method: 'post',
    primaryKey: ['COD'],                   // Osync
    Index: [['DESCRICAO']],                // Osync
    columns: ['COD', 'DESCRICAO'],
    params: {}                             // corpo da requisição, se houver
};
```

Credencial (chave, token, senha) **não** vai no código: fica na configuração do
serviço no Fluig.

**Extração de constraints** — inicializar cada filtro com `''`.

Estilo 1 — propriedade direta (usar em código novo):

```js
var valor = '';
if (constraints != null) {
    for (var i = 0; i < constraints.length; i++) {
        if (constraints[i].fieldName == 'nomeCampo') {
            valor = constraints[i].initialValue;
        }
    }
}
```

Estilo 2 — getter Java (aparece em datasets legados; funciona no Rhino, manter ao
refatorar só se o arquivo inteiro usar):

```js
if (constraints) {
    for (var index in constraints) {
        if (constraints[index].getFieldName() == 'nomecampo') {
            valor = constraints[index].getInitialValue();
        }
    }
}
```

Helper opcional quando há várias constraints:

```js
function getConstraintValue(constraints, fieldName) {
    if (!constraints || constraints.length === 0) return '';
    for (var i = 0; i < constraints.length; i++) {
        if (constraints[i].fieldName && constraints[i].fieldName.toLowerCase() == (fieldName || '').toLowerCase()) {
            var val = constraints[i].initialValue;
            return (val !== null && val !== undefined) ? String(val).trim() : '';
        }
    }
    return '';
}
```

**Validar constraints obrigatórias** — antes de chamar o serviço, se um filtro
obrigatório vier vazio, `return exibeErro("Constraint obrigatória ausente: X", "...")`.
Filtros opcionais seguem como `''`.

**Invoke** via `fluigAPI.getAuthorizeClientService()` + `service.invoke(new
org.json.JSONObject(options).toString())`, com `timeoutService: '100'` e
`headers: { Connection: 'close' }`:

```js
var options = {
    companyId: getValue('WKCompany') + '',
    serviceCode: init.fluigService,
    endpoint: init.endpoint,
    method: init.method,
    params: init.params,
    timeoutService: '100',
    headers: { Connection: 'close' }
};
var service = fluigAPI.getAuthorizeClientService();
var vo = service.invoke(new org.json.JSONObject(options).toString());
if (vo.getHttpStatusResult() == 200) {
    var data = JSON.parse(vo.getResult());
    // percorrer o array de resultado no formato documentado pelo cliente
}
```

Alguns serviços devolvem o status no corpo (ex.: `data.Code == 200`) em vez do
HTTP status; conferir no `AGENTS.md` do cliente qual vale.

**Parse + preenchimento** — iterar o array de resultado (`data.result[]`,
`data.items[]`, `objdata.content[]`, `objdata.invdata[]` conforme a fonte) e
`dataset.addRow([...])`. Fazer null-check em cada valor:
`(v != null) ? String(v).trim() : ''`. Ler as colunas por **nome**, nunca por posição.

**Tratamento de erro** — `try/catch` em torno da chamada. No `catch`:
`log.error('Error to execute dataset "' + init.datasetName + '": ' + e.message)` e
retornar estrutura de erro. Dois formatos de erro coexistem — escolher **um** por
dataset e ser consistente (código na seção 5):
- `exibeErro(msg, detalhes)` → colunas ERRO/MSG/DETALHES (bom quando o form/consumidor
  exibe a mensagem).
- `createErrorStructure()` → coluna única `error`.

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

```js
function defineStructure() {
    for (var i = 0; i < init.columns.length; i++) {
        addColumn(init.columns[i], DatasetFieldType.STRING);
    }
    setKey(init.primaryKey);
    for (var j = 0; j < init.Index.length; j++) {
        addIndex(init.Index[j]);
    }
}

function createStructure() {
    var dataset = DatasetBuilder.newDataset();
    for (var i = 0; i < init.columns.length; i++) {
        dataset.addColumn(init.columns[i]);
    }
    return dataset;
}

function onMobileSync(user) {
    return { 'fields': init.columns, 'constraints': new Array(), 'sortFields': new Array() };
}
```

Reconciliação no fim do `onSync`: guardar as chaves recebidas num objeto
(`primaryKeyCodes[chave] = true`), reler o próprio dataset com
`DatasetFactory.getDataset(init.datasetName, null, null, null)` e chamar
`dataset.deleteRow(row)` para cada registro cuja chave não veio da fonte.

**on-demand** — apenas `createDataset` (os stubs `defineStructure`/`onSync`/
`onMobileSync` vazios são opcionais; incluir só se o padrão do arquivo-base os tiver).

**Ação — mover processo existente (`saveAndSendTask`)**. Avança a tarefa de uma
solicitação já aberta. `username`, `password`, `companyId`, `processInstanceId`,
`choosedState`, `comments` e `colleagueId` vêm das constraints ou da configuração do
projeto (nunca senha fixa no código).

```js
function createDataset(fields, constraints, sortFields) {
    var dataset = DatasetBuilder.newDataset();
    try {
        var serviceHelper = ServiceManager.getService('ECMWorkflowEngineService').getBean();
        var service = serviceHelper
            .instantiate('com.totvs.technology.ecm.workflow.ws.ECMWorkflowEngineServiceService')
            .getWorkflowEngineServicePort();

        var attachments = serviceHelper.instantiate('com.totvs.technology.ecm.workflow.ws.ProcessAttachmentDtoArray');
        var appointment = serviceHelper.instantiate('com.totvs.technology.ecm.workflow.ws.ProcessTaskAppointmentDtoArray');
        var colleagueIds = serviceHelper.instantiate('net.java.dev.jaxb.array.StringArray');

        // cardData: array de [chave, valor] com os campos do formulário a gravar
        var cardData = serviceHelper.instantiate('net.java.dev.jaxb.array.StringArrayArray');
        var jsonCardData = [{ key: 'campo1', value: 'valor1' }];
        for (var i = 0; i < jsonCardData.length; i++) {
            var stringArray = serviceHelper.instantiate('net.java.dev.jaxb.array.StringArray');
            stringArray.getItem().add(String(jsonCardData[i].key));
            stringArray.getItem().add(String(jsonCardData[i].value));
            cardData.getItem().add(stringArray);
        }

        var retorno = service.saveAndSendTask(
            username, password, companyId, processInstanceId,
            choosedState, colleagueIds, comments, colleagueId,
            /*completeTask*/ true, attachments, cardData, appointment,
            /*managerMode*/ true, /*threadSequence*/ 0
        );

        var colunas = retorno.getItem();
        var registro = new Array();
        for (var i = 0; i < colunas.size(); i++) {
            dataset.addColumn(colunas.get(i).getItem().get(0).toString());
            registro.push(colunas.get(i).getItem().get(1).toString());
        }
        dataset.addRow(registro);
    } catch (error) {
        dataset.addColumn('ERROR');
        dataset.addRow([error.toString()]);
    }
    return dataset;
}
```

**Ação — iniciar novo processo (`startProcess`)**. Cria uma solicitação de
`nome_processo`; `cardData` usa `ObjectFactory`. Retorna `iProcess` (número da nova
solicitação) ou a mensagem de `ERROR`.

```js
function startProcess(fields, colleagueId) {
    var serviceHelper = ServiceManager.getService('ECMWorkflowEngineService').getBean();
    var service = serviceHelper
        .instantiate('com.totvs.technology.ecm.workflow.ws.ECMWorkflowEngineServiceService')
        .getWorkflowEngineServicePort();

    var colleagueIds = serviceHelper.instantiate('net.java.dev.jaxb.array.StringArray');
    colleagueIds.getItem().add(colleagueId);

    // cardData via ObjectFactory (padrão para startProcess)
    var factory = serviceHelper.instantiate('net.java.dev.jaxb.array.ObjectFactory');
    var cardData = factory.createStringArrayArray();
    for (var c = 0; c < fields.length; c++) {
        var campo = factory.createStringArray();
        campo.getItem().add(fields[c].fieldName);
        campo.getItem().add(fields[c].fieldValue);
        cardData.getItem().add(campo);
    }

    var attachments = serviceHelper.instantiate('com.totvs.technology.ecm.workflow.ws.ProcessAttachmentDtoArray');
    var appointments = serviceHelper.instantiate('com.totvs.technology.ecm.workflow.ws.ProcessTaskAppointmentDtoArray');

    var processId = 'nome_processo';
    var retorno = service.startProcess(
        username, password, companyId,
        processId, choosedState, colleagueIds,
        comments, colleagueId,
        /*completeTask*/ true, attachments, cardData, appointments,
        /*managerMode*/ false
    );

    // Converte o retorno StringArrayArray em objeto simples
    var obj = {};
    for (var i = 0; i < retorno.getItem().size(); i++) {
        var item = retorno.getItem().get(i).getItem();
        obj[item.get(0)] = item.get(1);
    }
    return obj.ERROR ? obj.ERROR : obj.iProcess;
}
```

### 5. Helpers reutilizáveis

Se o projeto já tiver esses helpers num dataset existente, copiar de lá para manter
o mesmo formato; senão, usar estes. Incluir só os relevantes ao tipo (não injetar
`valorNulo` em `createDataset` puro).

| Helper | Retorno | Uso |
|---|---|---|
| `exibeErro(msg, detalhes)` | dataset com colunas `ERRO`/`MSG`/`DETALHES` e uma linha `['1', msg, detalhes]` | erro de validação ou de chamada, quando o consumidor exibe a mensagem |
| `createErrorStructure()` | dataset vazio com a coluna `error` (preencher com `addRow`) | erro no padrão de coluna única |
| `valorNulo(valor)` | `''` para `null`/`undefined`, senão `String(valor)` | todo valor gravado em Osync |
| `getConstraintValue(constraints, fieldName)` | valor da constraint (nome sem diferenciar maiúsculas), com `trim`, ou `''` | ler várias constraints em `createDataset` |
| `converteDataParaFluig(dataStr, isInicio)` | `dd/MM/yyyy HH:mm:ss`; lança erro se a entrada for inválida | constraints de data do `workflowProcess` (`isInicio` true = 00:00:00, false = 23:59:59) |

```js
// Dataset de erro com colunas ERRO/MSG/DETALHES + log
function exibeErro(msg, detalhes) {
    if (detalhes == null || detalhes == '') msg = 'Erro desconhecido, verifique o log do servidor.';
    log.error('ds_exemplo - msg: ' + msg);
    log.error('ds_exemplo - detalhes: ' + detalhes);
    var dataset = DatasetBuilder.newDataset();
    dataset.addColumn('ERRO');
    dataset.addColumn('MSG');
    dataset.addColumn('DETALHES');
    dataset.addRow(new Array('1', msg, detalhes));
    return dataset;
}

// Dataset de erro com coluna única "error" (preencher com addRow(['mensagem']))
function createErrorStructure() {
    var dataset = DatasetBuilder.newDataset();
    dataset.addColumn('error');
    return dataset;
}

// Troca null/undefined por '' (Osync)
function valorNulo(valor) {
    if (valor == null || valor === undefined) return '';
    return String(valor);
}

// 'yyyy-MM-dd' ou 'yyyy-MM-dd HH:mm:ss' / 'yyyy-MM-ddTHH:mm:ss' → 'dd/MM/yyyy HH:mm:ss'
// (formato das constraints de data do workflowProcess).
// isInicio: true = 00:00:00, false = 23:59:59, usado só quando a hora não vem na entrada.
// Entrada inválida lança erro: melhor falhar do que filtrar com data errada.
function converteDataParaFluig(dataStr, isInicio) {
    var regex = /^(\d{4})-(\d{2})-(\d{2})(?:[ T](\d{2}):(\d{2}):(\d{2}))?$/;
    var match = String(dataStr == null ? '' : dataStr).trim().match(regex);
    if (!match) {
        throw new Error("Data inválida '" + dataStr + "'. Use yyyy-MM-dd ou yyyy-MM-dd HH:mm:ss");
    }
    var hora = match[4]
        ? match[4] + ":" + match[5] + ":" + match[6]
        : (isInicio ? "00:00:00" : "23:59:59");
    return match[3] + "/" + match[2] + "/" + match[1] + " " + hora;
}
```

### 6. Datasets internos do Fluig

| Dataset | Descrição | Colunas comuns |
|---------|-----------|----------------|
| `workflowProcess` | Instâncias de solicitação | `workflowProcessPK.processInstanceId`, `processId`, `status` (0=Aberta, 1=Cancelada, 2=Finalizada), `startDateProcess`, `requesterId`, `cardDocumentId` |
| `processHistory` | Movimentações do workflow | `movementSequence`, `stateSequence`, `movementDate` |
| `processTask` | Tarefas das instâncias | `status`, `active`, `deadline`, `colleagueId` |
| `colleague` | Usuários | `colleaguePK.colleagueId`, `colleagueName`, `mail` |
| `workflowColleagueRole` | Usuários por papel | `colleagueId`, `roleId` |

Constraints de data em `workflowProcess`: formato `dd/MM/yyyy HH:mm:ss`.
**Não usar** `startDateProcessFromHistory` nem `expired` (descontinuados).

### 7. Entregar ao usuário

Resumo final deve conter:
1. Tipo + fonte escolhidos e o dataset de referência copiado (se houver).
2. Constraints (obrigatórias/opcionais) e colunas de retorno.
3. Se o projeto tiver skill/docs de Query Store ou documentação de dataset, apontar.

## Auditoria de um dataset existente

Ao revisar sem reescrever, sinalizar:
1. `let`, `const`, `=>`, template literals, `for...of`, destructuring, `class`, spread.
2. JSDoc ausente ou com `Dataset:` diferente do nome do arquivo.
3. Retorno que não vem de `DatasetBuilder.newDataset()`.
4. Datas para `workflowProcess` fora do formato `dd/MM/yyyy HH:mm:ss`.
5. Credenciais (senha, token, chave) fixas no código — devem ficar na configuração do serviço.
6. Status conferido do jeito errado para o serviço (HTTP status × status no corpo, conforme o `AGENTS.md` do cliente).
7. `addOrUpdateRow` em Osync sem `valorNulo()`.

## Checklist final (validar antes de entregar)

- [ ] Arquivo em `datasets/`, prefixo `ds_`, snake_case; nome do arquivo = `Dataset:` no JSDoc
- [ ] 100% ECMA 5 (sem let/const/arrow/template literal/for-of/destructuring/class/spread)
- [ ] Cabeçalho JSDoc completo (Dataset, Projeto, Versão, Tipo se Osync, Descrição, Constraints, Colunas na ordem)
- [ ] Constraints obrigatórias validadas com `exibeErro()`; opcionais toleram vazio
- [ ] Invoke com `org.json.JSONObject(options).toString()`, timeout e `Connection: close` (fontes REST)
- [ ] Null-check em cada valor gravado; `valorNulo()` se Osync
- [ ] `try/catch` com `log.error("<nome do dataset> - ...")` e estrutura de erro consistente (um só padrão)
- [ ] Osync: `defineStructure`/`onSync`/`onMobileSync` implementados; reconciliação por primaryKey
- [ ] Sem credencial fixa no código
- [ ] Endpoints e serviceCodes batem com o `AGENTS.md` do projeto
