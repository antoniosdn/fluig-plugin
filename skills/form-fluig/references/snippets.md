# Snippets de componentes — form-fluig

Markup e handlers extraídos dos forms de referência. **Sempre conferir o original**
(usar `references/` deste plugin ou um form já padronizado do projeto)
antes de copiar — estes snippets podem ficar defasados.

---

## 1. Tabela pai-filho

### HTML (1ª linha = template, nunca removida)
```html
<table tablename="tableItens" class="table" nodeletebutton="true" noaddbutton="true">
  <thead><tr><td></td></tr></thead>
  <tbody>
    <tr>
      <td>
        <div class="row">
          <div class="form-group col-md-2">
            <label>&nbsp;</label>
            <button type="button" class="btn btn-danger form-control btnRemoverItem">Excluir</button>
          </div>
          <div class="form-group col-md-4">
            <label class="obrigatorio">Descrição</label>
            <input type="text" class="form-control" name="descricaoItem">
          </div>
          <!-- demais campos da linha... -->
        </div>
      </td>
    </tr>
  </tbody>
</table>
<div class="row">
  <div class="col-md-3">
    <button type="button" class="btn btn-primary btnAdicionarItem">Adicionar</button>
  </div>
</div>
```
> Atributos `nodeletebutton`/`noaddbutton` desligam os botões padrão do WDK; usamos
> botões próprios. `wdkAddChild` clona a 1ª linha (a linha-template), por isso ela
> **nunca** pode ser removida.

### Handlers (custom.js)
```js
// Adiciona linha clonando o template do WDK.
$(document).on("click", ".btnAdicionarItem", function () {
  wdkAddChild("tableItens");
});

// Remove só linhas adicionadas; na última, limpa em vez de remover.
$(document).on("click", ".btnRemoverItem", function () {
  var totalLinhas = $("table[tablename='tableItens'] tbody tr").length;
  if (totalLinhas > 1) {
    fnWdkRemoveChild(this);
  } else {
    $(this).closest("tr").find("input, select, textarea").val("");
  }
});
```
> Botão "Adicionar" também pode chamar uma global inline:
> `onclick="addItem('tableItens')"` → `function addItem(t){ wdkAddChild(t); }`.

### Índice das linhas dinâmicas
Campos da linha clonada recebem sufixo `___<indice>` no `id`/`name`
(ex.: `descricaoItem___3`). Para obter o índice: `id.split("___")[1]`.

### Validação por linha (custom_valida.js, dentro de beforeSendValidate)
```js
$("table[tablename='tableItens'] tbody tr:visible").each(function () {
  var linha = $(this);
  var desc = linha.find("[name^='descricaoItem']").first();
  if (desc.length && !desc.val()) {
    erros.push('O campo "Descrição" é obrigatório.');
    marcarCampoInvalido(desc);
  } else if (desc.length) {
    limparCampoInvalido(desc);
  }
});
```

---

## 2. Zoom (autocomplete / lookup)

### HTML
```html
<input type="zoom" class="form-control" name="codigoItem"
  data-zoom="{
    'displayKey':'CODIGO',
    'datasetId':'ds_exemplo',
    'placeholder':' ',
    'filterValues':'',
    'fields':[
      {'field':'CODIGO','label':'Código','visible':'true'},
      {'field':'NOME','label':'Nome','visible':'false'},
      {'field':'VALOR','label':'Valor','visible':'false'}
    ]
  }" />
```

### zoom.js — preencher e limpar campos dependentes
```js
function setSelectedZoomItem(selectedItem) {
  var inputId = selectedItem.inputId || "";

  // campo simples (fora de pai-filho)
  if (inputId === "codigoItem") {
    aplicarValorCampo("nomeItem", obterValorDataset(selectedItem, ["NOME", "nome"]));
    aplicarValorCampo("valorItem", obterValorDataset(selectedItem, ["VALOR", "valor"]));
    return;
  }

  // campo dentro de pai-filho: extrair índice e montar o sufixo
  if (inputId.indexOf("codigoItem___") === 0) {
    var indice = inputId.split("___")[1];
    aplicarValorCampo("nomeItem___" + indice, obterValorDataset(selectedItem, ["NOME"]));
    return;
  }
}

function removedZoomItem(removedItem) {
  var inputId = removedItem.inputId || "";
  if (inputId === "codigoItem") {
    aplicarValorCampo("nomeItem", "");
    aplicarValorCampo("valorItem", "");
    return;
  }
  if (inputId.indexOf("codigoItem___") === 0) {
    var indice = inputId.split("___")[1];
    aplicarValorCampo("nomeItem___" + indice, "");
  }
}
```

### Helpers de apoio (topo do zoom.js)
```js
// Lê o primeiro campo não-vazio dentre vários nomes possíveis (DS varia maiúsc/minúsc).
function obterValorDataset(item, campos) {
  for (var i = 0; i < campos.length; i++) {
    var valor = item ? item[campos[i]] : "";
    if (valor !== undefined && valor !== null && String(valor).trim() !== "") {
      return String(valor).trim();
    }
  }
  return "";
}

// Seta valor e dispara change (reaplica após 50ms p/ vencer corrida de render).
function aplicarValorCampo(idCampo, valor) {
  var texto = valor || "";
  var campo = $("#" + idCampo);
  if (!campo.length) campo = $("[name='" + idCampo + "']");
  campo.val(texto).trigger("change");
  setTimeout(function () { campo.val(texto).trigger("change"); }, 50);
}
```

---

## 3. Anexo

Copiar `references/anexos.js` para a pasta do form (lib estável, não editar a menos
que mude o contrato de classes). Incluir o `<script src="anexos.js">` no HTML.

### HTML do componente
```html
<div class="componentAnexo">
  <input type="hidden" class="descAnexo" id="fnAnexoX" name="fnAnexoX" value="Descricao_Fixa_Do_Anexo">
  <div class="input-group">
    <input type="text" id="fdAnexoX" name="fdAnexoX" class="form-control inputAnexo" placeholder="Selecione um arquivo" readonly>
    <span class="input-group-btn">
      <button type="button" class="btnUpFile btn btn-success" data-acao="upload" onclick="anexo(event)"><i class="fluigicon fluigicon-file-upload"></i></button>
      <button type="button" class="btnViewerFile btn btn-info" data-acao="viewer" onclick="anexo(event)" style="display:none"><i class="fluigicon fluigicon-eye-open"></i></button>
      <button type="button" class="btnDownloadFile btn btn-primary" data-acao="download" onclick="anexo(event)" style="display:none"><i class="fluigicon fluigicon-download"></i></button>
    </span>
  </div>
</div>
```
> Contrato de classes (não renomear sem ajustar anexos.js e o css): `.componentAnexo`,
> `.descAnexo` (hidden, guarda a descrição que identifica o anexo na aba Anexos do
> Fluig), `.inputAnexo` (mostra o nome físico), `.btnUpFile`/`.btnViewerFile`/
> `.btnDownloadFile`, e o atributo `data-acao`.

### custom.js — inicialização e validação
```js
$(document).ready(function () {
  displayBtnFiles(); // ajusta botões por modo (ADD/MOD/VIEW)
});
```
```js
// em beforeSendValidate, se o anexo é obrigatório:
if (invalidFile("fdAnexoX")) {
  erros.push("O anexo é obrigatório / não foi encontrado.");
}
```

---

## 4. Helpers de tela (events/getUser.js ou topo do custom.js)

```js
// Desabilita campos/zoom/botões de uma div (modo aprovação/visualização).
const disablefield = (idDivs) => {
  $(idDivs).find(':input').prop('readonly', true);
  $(idDivs).find('select').css('touch-action','none').css('pointer-events','none').css('background','#eee');
  $(idDivs).on("click", function(){ return false; });
  $(idDivs).find('.btn').prop('disabled', 'disabled');
};
const hidediv = (idDivs) => { $(idDivs).css('display','none'); };
const showdiv = (idDivs) => { $(idDivs).css('display',''); };

// Espera os campos-chave carregarem antes de aplicar a lógica de tela (corrida no VIEW).
function waitForFields(callback) {
  var attempts = 0;
  var checkInterval = setInterval(function () {
    var pronto = $("#campoChave").val() && $("table[tablename='tableItens']").length > 0;
    if (pronto || ++attempts > 30) { clearInterval(checkInterval); callback(); }
  }, 100);
}

// Desabilita todos os zooms (chamar em tarefas de aprovação/visualização).
function disableAllZooms() {
  setTimeout(function () {
    $('input[type="zoom"]').each(function () {
      var input = $(this);
      input.prop("readonly", false);
      var zoomName = input.attr("name");
      if (window[zoomName]) window[zoomName].disable(true);
    });
  }, 500);
}
```

---

## 5. custom_valida.js — validação genérica de `.obrigatorio`

Padrão genérico do projeto: a validação client (`beforeSendValidate`) varre todos os
labels `.obrigatorio:visible` e delega para `verificaCampos`, que mora na lib
`references/widget_code_repository.js`. Acrescente as regras específicas do form
empilhando em `arrError` antes do `throw` final.

**Pré-requisito:** o form precisa incluir `widget_code_repository.js` (lib genérica —
copiar de `references/widget_code_repository.js`). Ela fornece `verificaCampos`,
`destacaCampObrigatorio`, `limpaDestacados`, `validaCPF`, `validaCNPJ`,
`asteriscosObrigatorios`, `exibirMsgErroForm`, `campoVazio`, etc.

```js
// Arrays globais usados pela lib (verificaCampos/destacaCampObrigatorio).
var arrError = [];
var campoObrig = [];

var beforeSendValidate = function (_numState, _nextState) {
  arrError = [];   // zera a cada envio
  campoObrig = [];

  // 1) Validação genérica: todo label .obrigatorio:visible vira erro se vazio.
  //    Trata text/select/radio/zoom e destaca os campos faltantes.
  var obrigatorios = $('.obrigatorio:visible');
  verificaCampos(obrigatorios);

  // 2) Regras específicas do form (exemplos — empilhar em arrError):
  // if (campoVazio("meuCampo")) { arrError.push("Informe Meu Campo."); }
  // validaCnpjCpf($("#cnpjcpf"));   // valida CPF/CNPJ se preenchido
  // Validação por linha de pai-filho: ver seção 1 (usar arrError.push).

  // 3) Mostra os erros acumulados e interrompe o envio.
  if (arrError.length > 0) {
    var error = "Por favor, verifique os alertas abaixo:\r\n";
    arrError.forEach(function (err, index) {
      error += (index + 1) + " - " + err + "\r\n";
    });
    throw error;
  }
};
```

> `verificaCampos` já destaca os campos faltantes (radio/zoom/select/texto) e religa o
> destaque ao alterar o campo. Para exibir os erros num modal em vez do alert padrão,
> use `exibirMsgErroForm(mensagem)` no lugar do `throw`.

Opcional, no `custom.js` (`$(document).ready`): `asteriscosObrigatorios()` adiciona o
`*` vermelho aos labels `.obrigatorio` visíveis e editáveis.

### Variante de validação server-side (validateForm)
Quando precisar validar no servidor (atividades de aprovação), usar o padrão do form de
Exemplo de validateForm no servidor: `function validateForm(form){ var n = getValue("WKNumState"); ... form.getValue(campo) ... throw "mensagem"; }`.

---

## 6. events/displayFields.js (ECMA5 — servidor)

```js
function displayFields(form, customHTML) {
  var activity = getValue("WKNumState");

  form.setShowDisabledFields(true); // permite ver campos antes de assumir a tarefa
  form.setHidePrintLink(true);

  // expõe a atividade atual para o custom.js
  customHTML.append("<script>");
  customHTML.append("var currentTask='" + activity + "';");
  customHTML.append("</script>");

  // exemplo de default na abertura
  if (activity == 0 || activity == 4) {
    var hoje = new Date();
    var ano = hoje.getFullYear();
    var mes = (hoje.getMonth() + 1) < 10 ? "0" + (hoje.getMonth() + 1) : (hoje.getMonth() + 1);
    var dia = hoje.getDate() < 10 ? "0" + hoje.getDate() : hoje.getDate();
    form.setValue("dataSolicitacao", dia + "/" + mes + "/" + ano);
  }
}
```
> ⚠️ ECMA5 puro: nada de `const`/`let`/arrow/template literal aqui.
