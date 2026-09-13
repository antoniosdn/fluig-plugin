---
name: fluig-validacao
description: >
  Padrão de validação de formulários Fluig no arquivo custom_valida.js.
  Use esta skill SEMPRE que o usuário pedir para validar campos obrigatórios,
  bloquear envio de formulário, validar tabelas pai/filho, ou quando mencionar
  "beforeSendValidate", "arrError", "obrigatorio" ou "verificaCampos".
---
 
# Fluig — Padrão de Validação de Formulários
 
## Dependência Obrigatória
 
> **O script `widget_code_repository.js` deve estar incluído no projeto Fluig.**
> Ele define as funções globais `verificaCampos` e `destacaCampObrigatorio`
> usadas pelo padrão. Sem ele, `verificaCampos` não existirá em runtime.
 
---
 
## Conceito
 
Validação feita em `custom_valida.js` via `beforeSendValidate`, chamada pelo Fluig
antes de cada movimentação de workflow. Acumula erros em `arrError[]` e lança
`throw` ao final, bloqueando o envio e exibindo as mensagens ao usuário.
 
---
 
## Template Base — custom_valida.js
 
```javascript
var beforeSendValidate = function (_numState, _nextState) {
 
    arrError  = []; // Array global para armazenar erros
    campoObrig = []; // Array global para campos obrigatórios
 
    // Campos visíveis com classe .obrigatorio no <label>
    var obrigatorios = $('.obrigatorio:visible');
    verificaCampos(obrigatorios);
 
    // === Validações manuais adicionais aqui ===
 
    // Mostra os erros acumulados, se existirem
    if (arrError.length > 0) {
        var error = "Por favor, verifique os alertas abaixo:\r\n";
        arrError.forEach((err, index) => {
            error += `${index + 1} - ${err}\r\n`;
        });
        throw error; // Interrompe o envio com os erros
    }
};
```
 
---
 
## Classe CSS `.obrigatorio`
 
Aplicada ao `<label>`, **nunca ao `<input>`**. O `verificaCampos` localiza o input
dentro do mesmo elemento pai.
 
```html
<!-- CORRETO -->
<label class="obrigatorio" for="meuCampo">Nome do Campo</label>
<input type="text" name="meuCampo" id="meuCampo" class="form-control">
 
<!-- ERRADO -->
<input type="text" class="form-control obrigatorio" ...>
```
 
**Tornar obrigatório condicionalmente (custom.js):**
 
```javascript
if (condicao) {
    $("label[for='meuCampo']").addClass("obrigatorio");
} else {
    $("label[for='meuCampo']").removeClass("obrigatorio");
}
```
 
---
 
## Validação Manual (sem `.obrigatorio`)
 
Para regras de negócio — inserir entre `verificaCampos(...)` e o bloco de erros:
 
```javascript
// Basta empurrar a mensagem — o bloco final já consolida tudo
arrError.push("Mensagem de erro para o usuário.");
```
 
**Exemplo — pai/filho com mínimo de linhas:**
 
```javascript
var tipodeSolVal = $("#TipodeSol").val();
if (tipodeSolVal === "mudancaDia") {
    var qtdHorarios = $('input[name*="diaHorarioAtual___"]').length;
    if (qtdHorarios === 0) {
        arrError.push("Adicione ao menos um horário a ser alterado.");
    }
}
```
 
> Usar `[name*="campo___"]` — nunca `[name="campo"]`, pois isso seleciona o template.
 
---
 
## Validação por Estado
 
Os números de estado variam por processo — consulte o diagrama do workflow.
 
```javascript
// Validar ao sair de um estado específico
if (_numState === ESTADO_ATUAL) {
    arrError.push("...");
}
 
// Validar ao ir para um estado específico
if (_nextState === ESTADO_DESTINO) {
    arrError.push("...");
}
```
 
---
 
## Validação de Intervalo de Datas
 
```javascript
// Datas em formato ISO (yyyy-mm-dd) — comparação direta de string funciona
var inicio = $("#dataInicio").val();
var fim    = $("#dataFim").val();
if (inicio && fim && fim < inicio) {
    arrError.push("Data de Fim não pode ser anterior à data de Início.");
}
```
 
---
 
## Checklist de Implementação
 
- [ ] `widget_code_repository.js` incluído no projeto Fluig
- [ ] `arrError = []; campoObrig = [];` no início de `beforeSendValidate`
- [ ] `verificaCampos($('.obrigatorio:visible'))` chamado logo após
- [ ] Classe `.obrigatorio` no `<label>`, nunca no `<input>`
- [ ] Validações manuais com `arrError.push("mensagem")`
- [ ] Validações condicionais usando `_numState` / `_nextState` (números do diagrama)
- [ ] Pai/filho: `[name*="campo___"]` — nunca `[name="campo"]`
- [ ] `throw error` ao final se `arrError.length > 0`