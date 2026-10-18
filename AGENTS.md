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
| Evento de workflow, `displayFields`/`enableFields`/`validateForm`, service task, gateway, `.process` | `fluig-workflow` |
| Fluxo de processo novo a partir de descrição (spec → .process + ECM30 + SVG pelo mcp-fluig, publicação em teste) | `fluig-fluxo` |
| `beforeSendValidate` / obrigatório | `fluig-validacao` |
| Widget WCM nova | `fluig-scaffolding-widget` |
| Layout WCM novo | `fluig-scaffolding-layout` |
| Publicar / importar / diff / audit / deploy / log / helper | `fluig-cli` |
| Review de UI / segurança / a11y | `fluig-code-review` e irmãs |
| Corrigir XSS / sanitizar entrada no frontend | `fluig-validate-security` |
| Otimizar performance de widget/tela | `fluig-optimize-performance` |
| Corrigir acessibilidade de markup | `fluig-improve-accessibility` |
| Migrar jQuery → ES6+ (só código de browser) | `fluig-migrate-jquery-es6` |
| Teste funcional de processo pela interface | `fluig-tester` |
| Testar / regressão automatizada de processo (API do fluigcli + formulário headless) | `fluig-teste` (orquestrador) |

## Agentes deste plugin

| Agente | Modelo | Papel |
|---|---|---|
| `fluig-executor` | Sonnet medium | Implementa um `plano-*.md` aprovado; publica com fluigcli (ou versão de processo via `deployProcess` com imagem) só quando o plano manda |
| `fluig-revisor` | Opus high | Revisa o `git diff` contra o plano e o servidor (só leitura) |
| `fluig-test-runner` | Sonnet medium | Roda a suíte `testes/<processo>.json` aprovada (orquestrador `fluig-teste`) |
| `fluig-test-auditor` | Opus high | Classifica as falhas (processo × teste × ambiente) e rascunha o plano de correção |

Fluxo para mudança média ou grande (vários arquivos, risco Rhino, versão de processo): planejar na
sessão principal (`plano-<descricao>.md`, aprovado pelo usuário) → `fluig-executor` → `fluig-revisor`
→ no máximo uma rodada de correção → regressão com `fluig-teste`.

Não usar scaffold oficial TOTVS de form ou dataset. Query Store, se o cliente
tiver, está no `AGENTS.md` do projeto — não inventar endpoint.

## Publicação

Pedir autorização explícita antes de escrever no servidor. MCP Fluig costuma ser
somente leitura. Quem publica é o `fluigcli`.
