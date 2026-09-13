---
name: form-fluig
description: Cria, refatora ou injeta componentes em formulários Fluig no padrão deste plugin (custom.js, custom_valida.js, zoom.js, anexos.js, events/displayFields.js, style.css). Use ao criar um form/processo, padronizar um form existente ou adicionar pai-filho, zoom ou anexo.
---

# Formulários Fluig — scaffold, refatoração e componentes (projeto Fluig)

Padroniza o desenvolvimento de formulários Fluig do projeto Fluig. Todo form do
projeto segue o mesmo conjunto de arquivos e as mesmas convenções; esta skill cria
esse conjunto do zero, traz um form existente para o padrão, ou injeta componentes
recorrentes (pai-filho, zoom, anexo) em um form-alvo.

**Referência:** o conjunto de arquivos e os snippets em `skills/form-fluig/references/`.
Se o projeto tiver um form já no padrão, copiar dele; senão usar só as references do plugin.

## Uso

```
/form-fluig novo <Nome do Form>                  → scaffold completo de um form novo
/form-fluig refatorar <pasta do form>            → traz form existente ao padrão
/form-fluig componente pai-filho <pasta>         → injeta tabela pai-filho
/form-fluig componente zoom <pasta>              → injeta autocomplete/lookup (zoom)
/form-fluig componente anexo <pasta>             → injeta componente de anexo
```

Se o argumento de modo não vier claro, **perguntar** (AskUserQuestion): novo,
refatorar ou componente — e qual componente.

---

## Regra de motor (CRÍTICA)

| Arquivo | Onde roda | Sintaxe permitida |
|---------|-----------|-------------------|
| `*.html`, `custom.js`, `custom_valida.js`, `zoom.js`, `anexos.js`, `widget_code_repository.js` | **browser** | ES6+ liberado (`let`/`const`, arrow, template literals) |
| `events/displayFields.js` | **servidor (Rhino)** | **apenas ECMA 5** — `var`, `function(){}`, nada de arrow/`const`/template literals |
| `workflow/scripts/*.js` (service tasks) | **servidor (Rhino)** | **apenas ECMA 5** |

Erro mais comum: usar ES6 em `events/displayFields.js` ou numa service task → quebra
em runtime. Ver [AGENTS.md](../../AGENTS.md) e a regra ECMA 5 / Rhino.

---

## Estrutura-padrão de um form

```
forms/<id ou nome>/
├── <nome>.html              # markup; inclui os scripts e o style.css
├── custom.js                # lógica de tela: $(document).ready, handlers, currentTask
├── custom_valida.js         # validação client (beforeSendValidate) e server (validateForm)
├── zoom.js                  # setSelectedZoomItem / removedZoomItem (preenche campos do lookup)
├── anexos.js                # componente de anexo (lib estável — copiar de references/anexos.js)
├── events/
│   └── displayFields.js     # ECMA5; setShowDisabledFields, currentTask via <script>, defaults
└── style.css
```

Arquivos opcionais conforme necessidade: `widget_code_repository.js` (lib genérica —
ver abaixo), `jquery.mask.js`, `events/getUser.js`.

**Libs estáveis** — copiar **verbatim** de `references/` (não regenerar):

```bash
cp "skills/form-fluig/references/anexos.js"                 "forms/<form>/anexos.js"
cp "skills/form-fluig/references/widget_code_repository.js" "forms/<form>/widget_code_repository.js"
```

No projeto do cliente o caminho da skill é o que o plugin instalar (não `.agents/skills/`).

- `anexos.js` — componente de anexo (contrato de classes fixo).
- `widget_code_repository.js` — helpers genéricos do client: validação por
  `.obrigatorio` (`verificaCampos`/`destacaCampObrigatorio`/`limpaDestacados`),
  `validaCPF`/`validaCNPJ`/`validaCnpjCpf`, `asteriscosObrigatorios`, `campoVazio`,
  `disablefield`/`enablefield`/`hidediv`/`showdiv`, `currencyToNumber`/`numberToCurrency`,
  e helpers de ECM (`criarPasta`/`criarDocumento`/`excluirDocumento`/`verDocumento`).
  Usa os globais `arrError`/`campoObrig` declarados no `custom_valida.js`.

Includes no `<head>` do HTML (ver form de referência):
```html
<script src="/portal/resources/js/jquery/jquery.js"></script>
<script src="/portal/resources/js/jquery/jquery-ui.min.js"></script>
<script src="/style-guide/js/fluig-style-guide.min.js"></script>
<script src="/portal/resources/js/mustache/mustache-min.js"></script>
<link rel="stylesheet" type="text/css" href="https://style.fluig.com/css/fluig-style-guide-flat.min.css">
<link rel="stylesheet" href="style.css">
```

---

## Convenções obrigatórias

1. **`currentTask`** — exposto pelo `events/displayFields.js` via `<script>` e lido no
   `custom.js` para decidir o que mostrar/esconder/bloquear por atividade. Padrão fixo:
   ```js
   customHTML.append("<script>");
   customHTML.append("var currentTask='" + getValue("WKNumState") + "';");
   customHTML.append("</script>");
   ```
2. **Campos obrigatórios** — marcar o `<label class="obrigatorio">`; a validação client
   varre `$(".obrigatorio:visible")` em `beforeSendValidate`.
3. **Bloqueio por atividade** — usar os helpers `disablefield(seletor)`, `hidediv`,
   `showdiv` (definidos em `events/getUser.js` ou no topo do `custom.js`); para zooms,
   usar `disableAllZooms()`.
4. **Condição de corrida em VIEW** — em tarefas de visualização os dados demoram a
   carregar; usar o padrão `waitForFields(callback)` antes de aplicar a lógica de tela.
5. **Comentários em português**, densidade igual à dos forms de referência (uma linha
   explicando a intenção de cada bloco/handler).
6. **Handlers via delegação** — `$(document).on("change", ".classe", ...)`, nunca
   `onclick` inline novo (exceto os do componente de anexo, que já são inline por
   contrato: `onclick="anexo(event)"`).

---

## Modo `novo`

1. Perguntar (se não informado): nome do form, se tem **pai-filho**, **zoom**,
   **anexo**, e se carrega **dados do solicitante logado** (RM/Fluig).
2. Criar a pasta `forms/<Nome>/` e gerar:
   - `<nome>.html` — esqueleto com `<head>` padrão, painéis em `.panel`, e os
     componentes pedidos (snippets em `references/snippets.md`).
   - `custom.js` — `$(document).ready` com bloco de inicialização, `waitForFields`,
     e o `if/else if (currentTask == ...)` (deixar tarefas como TODO comentado).
   - `custom_valida.js` — `beforeSendValidate` (client) com a varredura genérica de
     `.obrigatorio` via `verificaCampos` (template em `references/snippets.md` §5) +
     `validateForm` (server) quando houver aprovação. Copiar
     `references/widget_code_repository.js` junto (a validação depende dele).
   - `events/displayFields.js` — **ECMA5**, com o bloco `currentTask` e defaults (ex.:
     data atual na abertura).
   - `style.css` — base (pode iniciar a partir do form de referência).
   - Se anexo: copiar `references/anexos.js` **verbatim**.
   - Se zoom: criar `zoom.js` com `setSelectedZoomItem`/`removedZoomItem`.
3. Não inventar datasets/zooms inexistentes — perguntar o `datasetId` e os campos, ou
   deixar `datasetId` como placeholder comentado.

## Modo `refatorar`

1. Ler **todos** os arquivos do form-alvo e mapear o que existe.
2. Reorganizar para a estrutura-padrão **sem alterar comportamento**:
   - Mover lógica de tela solta para `custom.js`; validação para `custom_valida.js`;
     preenchimento de zoom para `zoom.js`.
   - Garantir `events/displayFields.js` em ECMA5 com o bloco `currentTask`.
   - Converter `onclick` inline antigos para delegação quando seguro (preservar os do
     anexo).
   - Padronizar nomes de funções/handlers conforme os forms de referência.
3. **Apontar diferenças de comportamento antes de aplicar** se houver ambiguidade.
4. Não tocar em `id`/`name` de campos integrados (quebraria o vínculo com o cardData)
   sem confirmar com o usuário.

## Modo `componente`

Opera sobre um form-alvo já existente, injetando só o bloco pedido. Em todos:
ler o HTML e os JS do alvo, inserir o markup no ponto indicado pelo usuário e plugar
os handlers nos arquivos JS corretos. Detalhes e markup em `references/snippets.md`.

### pai-filho
- Tabela com `tablename`, `nodeletebutton="true" noaddbutton="true"`, 1ª linha-template
  (nunca removida — o `wdkAddChild` clona dela).
- Botão "Adicionar" → `wdkAddChild('tablename')`; "Excluir" → `fnWdkRemoveChild(this)`
  com guarda para não remover a linha-template.
- Handlers em `custom.js`; validação por linha em `custom_valida.js`.

### zoom
- `<input type="zoom" data-zoom="{...}">` com `displayKey`, `datasetId`, `fields`.
- Em `zoom.js`: tratar o `inputId` em `setSelectedZoomItem` (preencher campos
  dependentes) e limpar em `removedZoomItem`. Para zoom dentro de pai-filho, extrair o
  índice com `inputId.split("___")[1]`.

### anexo
- Copiar `references/anexos.js` se ainda não existir; inserir o markup `.componentAnexo`
  (input `.descAnexo` hidden com a descrição fixa do anexo + input `.inputAnexo` +
  botão `.btnUpFile`). Chamar `displayBtnFiles()` no ready e validar com `invalidFile`.

---

## Checklist final (sempre)

- [ ] `events/displayFields.js` está em **ECMA5 puro**?
- [ ] `currentTask` exposto no displayFields e consumido no custom.js?
- [ ] Labels obrigatórios com `class="obrigatorio"` e cobertos pela validação?
- [ ] Pai-filho: linha-template preservada, add/remove com guarda?
- [ ] Zoom: preenche e limpa campos dependentes (incl. índice em pai-filho)?
- [ ] Sem `id`/`name` de campos integrados alterados sem aval do usuário?
- [ ] Comentários em português, no mesmo estilo dos forms de referência?
