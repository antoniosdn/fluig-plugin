# Plugin Fluig — instruções permanentes

Pacote genérico de customização Fluig. O `AGENTS.md` do **repositório do cliente**
vence em integrações, nomes de processo e publicação.

## Linguagem

Responder e documentar em Português (BR). Preservar nomes técnicos do Fluig
(`createDataset`, `beforeSendValidate`, `Constraint`, `onSync`).

## JavaScript — dois motores

| Onde | Sintaxe |
|---|---|
| `datasets/`, `workflow/scripts/`, `forms/*/events/displayFields.js` | **ECMA 5 / Rhino** — `var`, `function(){}`, sem arrow/`const`/template literal |
| `forms/` (HTML/JS de tela), widgets no browser | ES6+ ok |

## Skills deste plugin

| Pedido | Skill |
|---|---|
| Dataset novo ou refatorar | `dataset-fluig` / `fluig-dataset` |
| Form, zoom, pai-filho, anexo | `form-fluig` |
| `beforeSendValidate` / obrigatório | `fluig-validacao` |
| Widget WCM nova | `fluig-scaffolding-widget` |
| Layout WCM novo | `fluig-scaffolding-layout` |
| Publicar / importar / diff / audit / deploy / log / helper | `fluig-cli` |
| Vários arquivos ou risco Rhino | `fluig-orquestracao` |
| Review de UI / segurança / a11y | `fluig-code-review` e irmãs |

Não usar scaffold oficial TOTVS de form ou dataset. Query Store, se o cliente
tiver, está no `AGENTS.md` do projeto — não inventar endpoint.

## Publicação

Pedir autorização explícita antes de escrever no servidor. MCP Fluig costuma ser
somente leitura. Quem publica é o `fluigcli`.
