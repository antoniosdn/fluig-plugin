---
name: fluig-workflow
description: >
  Altera processos TOTVS Fluig no lado do servidor: eventos de workflow
  (beforeStateEntry, afterTaskComplete, afterProcessCreate, servicetaskNNN),
  eventos de formulário (displayFields, enableFields, validateForm), hAPI,
  gateways e atribuição do diagrama .process. Use quando a tarefa tocar
  workflow/scripts, forms/*/events, arquivo .process, ID de atividade,
  WKNumState, hAPI.getCardValue/setCardValue, addCardChild, service task ou
  "campo não grava na próxima etapa". Para HTML/JS de tela use form-fluig; para
  validação no browser use fluig-validacao; para dataset use dataset-fluig.
---

# Fluig — Workflow e eventos de servidor

O motor do Fluig é igual em todo processo. O desenho — IDs de atividade, campos,
helpers, integrações — é de cada processo. Esta skill cobre o motor. O desenho
sai sempre dos arquivos do processo em que o usuário está trabalhando.

Todo arquivo desta skill roda em **Rhino / ECMA 5** (ver `rules/fluig-rhino-es5.mdc`).
Se o arquivo já usa outro estilo, seguir o arquivo.

## Regras de trabalho

1. **Fonte da verdade é o processo aberto.** Nunca trazer ID de atividade, nome
   de campo, constante ou helper de outro processo — o mesmo papel (aprovador,
   financeiro, fim) tem número diferente em cada diagrama.
2. **Não inventar.** API, dataset, ID ou campo que não aparece no código do
   processo e não pode ser confirmado: dizer que não sabe.
3. **Mínimo necessário.** Sem rename, sem refatoração, sem arquivo novo "porque
   outro processo tem".
4. **Explicar antes de editar:** situação atual, o que muda (arquivo/função/campo),
   impacto em outras atividades e o que fica intocado.
5. **Integração é área restrita.** SOAP/`ServiceManager`, REST, JDBC, GED, token,
   service task que chama sistema externo: só alterar com pedido explícito daquela
   integração. Pedido de tela ou validação não autoriza. As integrações do cliente
   estão no `AGENTS.md` do projeto.
6. **Credencial** encontrada no código: não imprimir, não mover, não commitar.

## Roteiro de leitura

Ler só o processo alvo, nesta ordem, e anotar o que cada arquivo revela:

| # | Arquivo | O que extrair |
|---|---|---|
| 1 | `workflow/diagrams/<CODIGO>.process` | IDs das atividades, `<expression>` dos gateways, mecanismo de atribuição, service tasks e trilhas de erro |
| 2 | `workflow/scripts/<CODIGO>.*.js` | Eventos implementados, helpers chamados pelo diagrama, integrações existentes |
| 3 | `forms/<form>/events/displayFields.js` | Constantes de atividade, visibilidade, dados injetados no browser |
| 4 | `forms/<form>/events/enableFields.js` | O que cada atividade deixa gravar |
| 5 | `forms/<form>/events/validateForm.js` | Regra de envio no servidor |
| 6 | HTML e JS do form | `name` dos campos, `tablename`, zoom, `beforeSendValidate` |

Arquivo ausente no processo não é convite para criar. Criar só quando o usuário
pedir e o motor exigir (ex.: service task cujo ID já existe no diagrama).

## Onde cada código roda

| Camada | Pasta | Lê/grava o card | Dataset |
|---|---|---|---|
| Eventos do form | `forms/<form>/events/` | `form.getValue` / `form.setValue` | `ds.rowsCount`, `ds.getValue(i, "COL")` |
| Workflow | `workflow/scripts/` | `hAPI.getCardValue` / `hAPI.setCardValue` | idem |
| Tela do form (browser) | HTML/JS do form | `$("#campo").val()` | `ds.values.length`, `ds.values[i]["COL"]` |

Não misturar: `hAPI` não existe no evento de form; `form` não existe no workflow;
jQuery não existe em nenhum dos dois.

## Contratos do motor — nome e assinatura fixos

O Fluig chama a função pelo nome. Rename ou troca de parâmetros quebra o processo
sem erro de compilação.

### Eventos de formulário (servidor)

| Função | Quando roda | Uso |
|---|---|---|
| `displayFields(form, customHTML)` | Ao montar o form | Visibilidade, valor inicial, `customHTML.append("<script>...")` para passar dados ao browser |
| `enableFields(form)` | Ao montar o form | `form.setEnabled(campo, bool)` — **campo desabilitado não é gravado no envio** |
| `validateForm(form)` | No envio | `throw "mensagem"` bloqueia |
| `inputFields(form)` | No envio, antes de gravar | Só mexer se já houver lógica |

Modo do form: `form.getFormMode()` retorna `ADD`, `MOD` ou `VIEW`.

### Eventos de workflow

Arquivo `<CODIGO>.<evento>.js`; a função dentro chama só `<evento>`.

| Evento | Assinatura | Quando |
|---|---|---|
| `afterProcessCreate` | `(processId)` | Solicitação criada |
| `beforeStateEntry` | `(sequenceId)` | Antes de entrar na atividade |
| `afterStateEntry` | `(sequenceId)` | Depois de entrar |
| `beforeTaskSave` | `(colleagueId, nextSequenceId, userList)` | Antes de salvar/enviar — `throw` bloqueia |
| `afterTaskSave` | `(colleagueId, nextSequenceId, userList)` | Depois de salvar |
| `afterTaskComplete` | `(colleagueId, nextSequenceId, userList)` | Tarefa concluída |
| `validateAvailableStates` | `(iCurrentState, stateList)` | Filtra destinos oferecidos ao usuário |
| `beforeCancelProcess` | `(colleagueId, processId)` | Antes de cancelar — `throw` impede |
| `afterProcessFinish` | `(processId)` | Processo encerrado |
| `servicetaskNNN` | `(attempt, message)` | Service task de ID `NNN` no diagrama |

Helpers (`utils`, `alcada`, funções de gateway) não são eventos: são chamados por
outro script ou pela expressão do `.process`. Não renomear função que o diagrama
referencia; buscar o nome no `.process` antes de tocar.

## Variáveis do motor — `getValue`

Disponíveis nos eventos de servidor:

| Chave | Conteúdo |
|---|---|
| `WKNumState` | Atividade atual |
| `WKNextState` | Próxima atividade (quando o evento tem) |
| `WKNumProces` | Número da solicitação |
| `WKUser` | Matrícula do usuário corrente |
| `WKCompany` | Código da empresa |
| `WKUserComment` | Observação digitada ao movimentar |
| `WKDef` | Código do processo |
| `WKCompletTask` | Se a tarefa está sendo concluída (`"true"`/`"false"`) |

Comparar atividade como número: `parseInt(getValue("WKNumState"), 10) == ATIVIDADE_X`.
Constantes de atividade: reutilizar as que o processo já declara.

## hAPI — principais métodos

| Método | Uso |
|---|---|
| `getCardValue(campo)` / `setCardValue(campo, valor)` | Ler/gravar campo do card |
| `getCardData(numProces)` | `HashMap` com todos os campos (inclui filhos `campo___N`) |
| `addCardChild(tablename, hashMap)` | Nova linha pai-filho — chave **sem** `___` |
| `setTaskComments(user, numProces, 0, texto)` | Comentário no histórico |
| `listAttachments()` / `attachDocument(docId)` / `publishWorkflowAttachment(dto)` | Anexos |
| `setAutomaticDecision(state, users, comment)` | Movimentar pela automação — só se o processo já usa |

Antes de usar método que o processo ainda não usa, confirmar a assinatura na
documentação da versão do cliente. Não trocar um pelo outro (ex.: `attachDocument`
× `publishWorkflowAttachment`) porque "parece equivalente".

## Padrões recorrentes

### Campo some na próxima etapa

Quase sempre `enableFields`: o campo está `setEnabled(false)` na atividade em que
é preenchido. Liberar **só** naquela atividade.

```javascript
function enableFields(form) {
    var atividade = parseInt(getValue("WKNumState"), 10);
    if (atividade == ATV_APROVACAO) {
        form.setEnabled("observacaoAprovador", true);
    }
}
```

Validação ou script de tela não resolvem se o campo está desabilitado no servidor.

### Campo desabilitado e `_campo`

Radio/select desabilitado pode chegar ao servidor como `_campo`. Validação de
servidor que depende dele lê os dois:

```javascript
var decisao = form.getValue("decisao") || form.getValue("_decisao");
```

### Pai-filho no servidor

```javascript
// eventos de form
var indices = form.getChildrenIndexes("tbItens");
for (var i = 0; i < indices.length; i++) {
    var qtd = form.getValue("quantidade___" + indices[i]);
}

// workflow — nova linha: chave SEM ___
var linha = new java.util.HashMap();
linha.put("quantidade", "1");
hAPI.addCardChild("tbItens", linha);
```

No workflow, percorrer linhas existentes = filtrar chaves com `___` em
`hAPI.getCardData(numProces)`. Se o processo já tem helper para isso, usar o dele.

### Duas validações

`beforeSendValidate` (browser, skill `fluig-validacao`) e `validateForm`
(servidor) coexistem. A regra de negócio, quando está nas duas, é a mesma. Não
remover uma porque a outra existe — o servidor é o que protege de envio forçado.

### Service task

```javascript
function servicetask12(attempt, message) {
    try {
        // chamada existente
    } catch (e) {
        log.error("servicetask12: " + e);
        throw e; // segue a trilha de erro do diagrama
    }
}
```

`NNN` = ID da tarefa no `.process`. Não criar service task sem o ID no diagrama.
Se o diagrama tem trilha de erro, **não engolir** a exceção. `attempt` indica a
tentativa atual quando o diagrama configura retentativas.

### Gateway

A decisão fica no `<expression>` do `.process`: pode ser
`hAPI.getCardValue("aprovado") == "S"` ou chamada a uma função de script. Se já
chama função, alterar **essa** função e manter a assinatura (é comum receber
string: `"1"`, `"2"`). Não duplicar a regra em service task ou evento.

### Atribuição (quem recebe a atividade)

Definida no `.process` (mecanismo de atribuição: campo do formulário, grupo,
papel, executor de outra atividade). JavaScript não substitui. Para "mudar quem
recebe": ler a atividade no `.process` e o campo de card que o mecanismo usa —
normalmente um hidden preenchido pelo zoom (`form-fluig`).

### Ponte servidor → browser

`displayFields` entrega atividade, modo e usuário ao JS da tela:

```javascript
customHTML.append("<script>var ATIVIDADE = " + getValue("WKNumState") + ";</script>");
```

O JS da tela consome a variável que **este** form injeta; não inventar outra.

## Diagnóstico rápido

| Sintoma | Primeiro lugar |
|---|---|
| Valor preenchido some na etapa seguinte | `enableFields` da atividade |
| Browser aceita e servidor bloqueia (ou o contrário) | `beforeSendValidate` × `validateForm` |
| Linha da tabela não grava | `tablename`, sufixo `___N`, `addCardChild` com chave sem `___` |
| Service task falha e não vai para atividade de erro | `throw` engolido no `catch` ou trilha ausente no `.process` |
| Atividade cai para a pessoa errada | Mecanismo de atribuição no `.process` + hidden do zoom |
| Gateway sempre vai pelo mesmo caminho | `<expression>` e tipo comparado (string × número) |
| Código funciona num processo e quebra em outro | ID de atividade ou campo copiado |
| Erro de sintaxe só no servidor | ES6 em arquivo Rhino |

## Checklist antes de entregar

- [ ] Li o `.process` e os scripts **deste** processo
- [ ] IDs de atividade vêm deste diagrama ou das constantes deste processo
- [ ] Nenhum rename de função do motor, helper do diagrama ou campo
- [ ] Assinatura dos eventos preservada
- [ ] Camada certa (evento de form × workflow × tela)
- [ ] `enableFields` libera o campo onde ele precisa gravar
- [ ] Pai-filho: `___N` em form/tela; chave sem `___` em `addCardChild`
- [ ] Service task relança erro quando existe trilha de erro
- [ ] Nenhuma integração alterada sem pedido explícito
- [ ] ECMA 5 (sem `let`/`const`/arrow/template literal)
- [ ] Publicação via `fluig-cli`, só com autorização
