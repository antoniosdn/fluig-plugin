---
name: fluig-dataset
description: Skill especializada para desenvolvimento de Datasets Fluig usando Rhino (ECMA 5) e padrões JSDoc em Português (BR).
---

# Fluig Dataset Expert

Esta skill habilita engenharia avançada para Datasets do TOTVS Fluig, garantindo aderência estrita aos requisitos do motor Rhino (ECMA 5) e aos padrões de documentação corporativa em Português (BR).

## Restrições Core (ECMA 5 / Rhino)

Os scripts de backend do Fluig rodam no motor **Rhino** (JavaScript em Java).
**CRÍTICO: Você NÃO DEVE usar sintaxe ES6+.**

- **Variáveis**: Use apenas `var`. Nunca `let` ou `const`.
- **Funções**: Use `function nome() {}`. Nunca arrow functions `() => {}`.
- **Strings**: Use concatenação `"a" + b`. Nunca template literals `` `a ${b}` ``.
- **Loops**: Use `for (var i = 0; i < arr.length; i++)`. Nunca `for...of`.
- **Objetos**: Sem destructuring, sem spread operator, sem classes.

> **Escopo**: Esta restrição aplica-se APENAS a `datasets/` e `workflow/scripts/`. Formulários em `forms/` rodam no browser e suportam ES6+ normalmente.

---

## Tipos de Dataset

### Tipo 1 — createDataset (Consulta Sob Demanda)

```javascript
/**
 * Dataset: ds_nome
 * Projeto: <nome do projeto>
 * Versão: 1.0
 *
 * Descrição: Propósito do dataset.
 *
 * Constraints esperadas:
 * - nomeCampo: Descrição (Obrigatório/Opcional)
 *
 * Estrutura de retorno (colunas):
 * - nomeColuna: Descrição
 */
function createDataset(fields, constraints, sortFields) {
    var dataset = DatasetBuilder.newDataset();
    dataset.addColumn("coluna1");
    // ...
    return dataset;
}
```

### Tipo 2 — Osync Lyceum (defineStructure + onSync simples)

Usado para sincronizar dados do Lyceum. Não usa objeto `init`. Colunas definidas em `defineStructure` — `onSync` não chama `addColumn`.

```javascript
/**
 * Dataset: ds_nome
 * Projeto: <nome do projeto>
 * Versão: 1.0
 * Tipo: Osync
 *
 * Descrição: O que sincroniza, de qual API e com qual frequência.
 *
 * Colunas (defineStructure):
 * - CHAVE: Descrição
 * - CAMPO1: Descrição
 */
function defineStructure() {
    addColumn("CHAVE");
    addColumn("CAMPO1");
    setKey(["CHAVE"]);
    addIndex(["CAMPO1"]);
}

function onSync(lastSyncDate) {
    var dataset = DatasetBuilder.newDataset();
    var dadosLyceum = consultarLyceum();

    if (dadosLyceum.status == 200 && dadosLyceum.objdata && dadosLyceum.objdata.dados) {
        var arrDados = dadosLyceum.objdata.dados;
        for (var i = 0; i < arrDados.length; i++) {
            var row = arrDados[i];
            dataset.addOrUpdateRow([
                valorNulo(row.CHAVE),
                valorNulo(row.CAMPO1)
            ]);
        }
    } else {
        if (log) {
            log.info("ds_nome - ERRO: " + (dadosLyceum.message || dadosLyceum.status));
        }
    }
    return dataset;
}

function consultarLyceum() {
    var clientService = fluigAPI.getAuthorizeClientService();
    var objRet = { status: 0, message: "", objdata: {} };
    var data = {
        companyId: getValue("WKCompany") + "",
        serviceCode: "rest_lyceum",
        endpoint: "/comum/tipo/csv/titulo/NOME_CONSULTA/consultaDinamicaParams",
        method: "get",
        timeoutService: "100"
    };
    var vo = clientService.invoke(JSON.stringify(data));
    if (vo.getHttpStatusResult() == 200) {
        objRet.status = vo.getHttpStatusResult();
        objRet.message = "SUCESSO";
        objRet.objdata = JSON.parse(vo.getResult());
    } else {
        objRet.status = vo.getHttpStatusResult();
        objRet.message = vo.getResult();
        if (log) log.info("ds_nome - ERRO Lyceum: " + vo.getResult());
    }
    return objRet;
}

function valorNulo(valor) {
    if (valor == null || valor === undefined) return "";
    return String(valor);
}
```

### Tipo 3 — Osync Protheus (padrão init object) ← dominante no projeto

Usado para sincronizar dados do Protheus via SQL. Inclui `createStructure`, `createErrorStructure`, `onMobileSync` e limpeza de registros obsoletos no `onSync`.

```javascript
var init = {
    datasetName: 'ds_nome',
    fluigService: 'REST_PROTHEUS',
    endpoint: '/FLGSELECT/EXECQUERY/SELECT',
    method: 'post',
    primaryKey: ['COL_CHAVE1', 'COL_CHAVE2'],
    Index: [['COL_IDX1'], ['COL_IDX2']],
    columns: ['COL_CHAVE1', 'COL_CHAVE2', 'CAMPO1', 'CAMPO2'],
    params: {
        chave: "c8ZKRwZz8HyPMPQIlziDc8ZKRwZz8HyPMPQIlziD",
        execquery: ""
    }
}

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

function createErrorStructure() {
    var dataset = DatasetBuilder.newDataset();
    dataset.addColumn('error');
    return dataset;
}

function onSync(lastSyncDate) {
    var dataset = createStructure();
    var query = createDataset();

    if (!query.values) return query;

    // Mapeia chaves existentes e insere/atualiza
    var primaryKeyCodes = [];
    for (var currentRow = 0; currentRow < query.values.length; currentRow++) {
        var primaryKey = '';
        for (var i = 0; i < init.primaryKey.length; i++) {
            primaryKey += query.getValue(currentRow, init.primaryKey[i]);
        }
        primaryKeyCodes[primaryKey] = true;

        var row = new Array();
        for (var j = 0; j < init.columns.length; j++) {
            var value = query.getValue(currentRow, init.columns[j]);
            row.push(value ? value : '');
        }
        dataset.addOrUpdateRow(row);
    }

    // Remove registros que não existem mais na fonte
    query = DatasetFactory.getDataset(init.datasetName, null, null, null);
    if (query && query.values) {
        for (var currentRow = 0; currentRow < query.values.length; currentRow++) {
            var primaryKey = '';
            for (var i = 0; i < init.primaryKey.length; i++) {
                primaryKey += query.getValue(currentRow, init.primaryKey[i]);
            }
            if (primaryKeyCodes[primaryKey] === undefined) {
                var row = new Array();
                for (var j = 0; j < init.columns.length; j++) {
                    row.push(query.getValue(currentRow, init.columns[j]));
                }
                dataset.deleteRow(row);
            }
        }
    }
    return dataset;
}

function onMobileSync(user) {
    return {
        'fields': init.columns,
        'constraints': new Array(),
        'sortFields': new Array()
    };
}

function createDataset(fields, constraints, sortFields) {
    var dataset = createStructure();
    try {
        init.params.execquery = "SELECT ... FROM ... WHERE ...";

        var service = fluigAPI.getAuthorizeClientService();
        var options = {
            companyId: getValue('WKCompany') + '',
            serviceCode: init.fluigService,
            endpoint: init.endpoint,
            method: init.method,
            params: init.params,
            timeoutService: '100'
        };
        var response = service.invoke(new org.json.JSONObject(options).toString());
        var data = JSON.parse(response.getResult());

        if (data && data.Code == 200) {
            for (var j = 0; j < data.result.length; j++) {
                var row = new Array();
                for (var k = 0; k < init.columns.length; k++) {
                    row.push(data.result[j][init.columns[k]]);
                }
                dataset.addRow(row);
            }
        } else {
            dataset = createErrorStructure();
            dataset.addRow(['Erro Protheus: ' + response.getResult()]);
        }
    } catch (exception) {
        dataset = createErrorStructure();
        dataset.addRow(['Erro: ' + exception.message]);
        log.info('ds_nome - erro: ' + exception.message);
    }
    return dataset;
}
```

### Tipo 4a — Dataset de Ação: mover processo existente (saveAndSendTask)

Usado para avançar/mover tarefa de processo já aberto.

```javascript
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

        // Monta cardData: array de [key, value] para campos do formulário
        var cardData = serviceHelper.instantiate('net.java.dev.jaxb.array.StringArrayArray');
        var jsonCardData = [{ key: "campo1", value: "valor1" }];
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
        dataset.addColumn("ERROR");
        dataset.addRow([error.toString()]);
    }
    return dataset;
}
```

### Tipo 4b — Dataset de Ação: iniciar novo processo (startProcess)

Usado para criar nova instância de processo. `cardData` usa `ObjectFactory`. Retorna `iProcess` (número da nova solicitação).

```javascript
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

    var retorno = service.startProcess(
        username, password, companyId,
        processId, choosedState, colleagueIds,
        comments, colleagueId,
        /*completeTask*/ true, attachments, cardData, appointments,
        /*managerMode*/ false
    );

    // Converte retorno StringArrayArray em objeto simples
    var obj = {};
    for (var i = 0; i < retorno.getItem().size(); i++) {
        var item = retorno.getItem().get(i).getItem();
        obj[item.get(0)] = item.get(1);
    }
    return obj.ERROR ? obj.ERROR : obj.iProcess;
}
```

---

## Integrações

### Lyceum (rest_lyceum)

Resposta via `getHttpStatusResult() == 200`. Resultado em `objRet.objdata.dados` (array de objetos). Sempre retornar wrapper `{status, message, objdata}` — o `onSync` depende desse formato.

```javascript
function consultarLyceum(endpoint) {
    var clientService = fluigAPI.getAuthorizeClientService();
    var objRet = { status: 0, message: "", objdata: {} };
    var data = {
        companyId: getValue("WKCompany") + "",
        serviceCode: "rest_lyceum",
        endpoint: endpoint,
        method: "get",
        timeoutService: "100"
    };
    var vo = clientService.invoke(JSON.stringify(data));
    if (vo.getHttpStatusResult() == 200) {
        objRet.status = vo.getHttpStatusResult();
        objRet.message = "SUCESSO";
        objRet.objdata = JSON.parse(vo.getResult());
    } else {
        objRet.status = vo.getHttpStatusResult();
        objRet.message = vo.getResult();
        if (log) log.info("ds_nome - ERRO Lyceum: " + vo.getResult());
    }
    return objRet;
}
// Uso: var ret = consultarLyceum("/endpoint");
// if (ret.status == 200 && ret.objdata && ret.objdata.dados) { ... }
```

### Fluig REST interno (fluig_rest)

Usado para consultar datasets publicados do próprio Fluig ou APIs internas (`/api/public/ecm/dataset/search`, papéis, etc.). Resposta via `getHttpStatusResult() == 200`. Resultado em `objdata.content` (array).

```javascript
function consultarFluigRest(endpoint) {
    var clientService = fluigAPI.getAuthorizeClientService();
    var data = {
        companyId: getValue('WKCompany') + '',
        serviceCode: 'fluig_rest',
        endpoint: endpoint,
        method: 'GET',
        timeoutService: '100'
    };
    var vo = clientService.invoke(JSON.stringify(data));
    var objdata = JSON.parse(vo.getResult());
    if (vo.getHttpStatusResult() == 200) {
        return objdata; // objdata.content = array de resultados
    }
    log.info('ds_nome - ERRO fluig_rest: ' + vo.getResult());
    return null;
}
// Exemplo de endpoint de busca em dataset publicado:
// '/api/public/ecm/dataset/search?datasetId=NOME&filterFields=campo,valor'
```

### Protheus (REST_PROTHEUS)

Resposta via `data.Code == 200` (não HTTP status). Resultado em `data.result` (array de objetos).

```javascript
var options = {
    companyId: getValue('WKCompany') + '',
    serviceCode: 'REST_PROTHEUS',
    endpoint: '/FLGSELECT/EXECQUERY/SELECT',
    method: 'post',
    params: {
        chave: "c8ZKRwZz8HyPMPQIlziDc8ZKRwZz8HyPMPQIlziD",
        execquery: "SELECT ..."
    },
    timeoutService: '100'
};
var service = fluigAPI.getAuthorizeClientService();
var response = service.invoke(new org.json.JSONObject(options).toString());
var data = JSON.parse(response.getResult());
// data.Code == 200 → sucesso
// data.result → array de objetos com campos da query
```

---

## Extração de Constraints

### Estilo 1 — propriedade direta (padrão o projeto)

```javascript
var valor = "";
if (constraints != null) {
    for (var i = 0; i < constraints.length; i++) {
        if (constraints[i].fieldName == "nomeCampo") {
            valor = constraints[i].initialValue;
        }
    }
}
```

### Estilo 2 — getter Java (datasets legados)

```javascript
if (constraints) {
    for (var index in constraints) {
        if (constraints[index].getFieldName() == 'nomecampo') {
            valor = constraints[index].getInitialValue();
        }
    }
}
```

Ambos funcionam no Rhino. Usar Estilo 1 em código novo.

---

## Helpers Padrão

### exibeErro (createDataset — validações obrigatórias)

```javascript
function exibeErro(msg, detalhes) {
    if (detalhes == null || detalhes == '') msg = "Erro desconhecido, verifique o log do servidor.";
    log.error('uf-log | msg: ' + msg);
    log.error('uf-log | detalhes: ' + detalhes);
    var dataset = DatasetBuilder.newDataset();
    dataset.addColumn("ERRO");
    dataset.addColumn("MSG");
    dataset.addColumn("DETALHES");
    dataset.addRow(new Array('1', msg, detalhes));
    return dataset;
}
```

### valorNulo (Osync Lyceum — evitar null em addOrUpdateRow)

```javascript
function valorNulo(valor) {
    if (valor == null || valor === undefined) return "";
    return String(valor);
}
```

### getConstraintValue (helper opcional para createDataset)

```javascript
function getConstraintValue(constraints, fieldName) {
    if (!constraints || constraints.length === 0) return "";
    for (var i = 0; i < constraints.length; i++) {
        if (constraints[i].fieldName && constraints[i].fieldName.toLowerCase() == (fieldName || "").toLowerCase()) {
            var val = constraints[i].initialValue;
            return (val !== null && val !== undefined) ? String(val).trim() : "";
        }
    }
    return "";
}
```

---

## Referência de Datasets Internos

| Dataset | Descrição | Colunas Comuns |
|---------|-----------|----------------|
| `workflowProcess` | Instâncias de solicitação | `processInstanceId`, `status` (0=Aberta,1=Cancelada,2=Finalizada), `startDateProcess`, `requesterId`, `cardDocumentId` |
| `processHistory` | Logs de movimentação | `movementSequence`, `stateSequence`, `movementDate` |
| `processTask` | Detalhes das tarefas | `status`, `active`, `deadline`, `colleagueId` |
| `colleague` | Perfis de usuários | `colleagueId`, `colleagueName`, `mail` |
| `workflowColleagueRole` | Usuários por papel | `colleagueId`, `roleId` |

**Atenção:** Constraints de data para `workflowProcess` devem usar formato `dd/MM/yyyy HH:mm:ss`.
**Não usar:** `startDateProcessFromHistory`, `expired` (descontinuados).

---

## Capacidades e Protocolos

### `/dataset-new`

Ao gerar código:
1. **Estritamente ECMA 5**: Valide que nenhuma palavra-chave ES6 esteja presente.
2. **Escolher o tipo correto**:
   - Consulta filtrada → Tipo 1 (createDataset)
   - Cache Lyceum → Tipo 2 (Osync simples + valorNulo)
   - Cache Protheus → Tipo 3 (Osync init object)
   - Ação de workflow → Tipo 4 (ECMWorkflowEngineService)
3. **Helpers**: Incluir apenas os relevantes ao tipo (não injetar valorNulo em createDataset puro).
4. **JSDoc obrigatório** com identificador igual ao nome do arquivo.

### `/dataset-check`

Ao auditar:
1. Sinalizar uso de `let`, `const`, `=>`, template literals, `for...of`, destructuring.
2. Verificar se JSDoc corresponde ao nome do arquivo.
3. Garantir que `DatasetBuilder.newDataset()` seja usado para retornos.
4. Verificar datas para `workflowProcess` no formato `dd/MM/yyyy HH:mm:ss`.
5. **Sinalizar credenciais hardcoded** (senhas, tokens, chaves) diretamente no código — devem estar em configuração de serviço ou variável de ambiente.
6. Verificar `data.Code == 200` em chamadas Protheus (não `getHttpStatusResult()`).
7. Verificar uso de `valorNulo()` em todo `addOrUpdateRow` de Osync Lyceum.
