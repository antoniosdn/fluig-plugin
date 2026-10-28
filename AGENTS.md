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

Tabela canônica de pedido → skill (o `README.md` repete esta tabela para leitura humana).

| Pedido | Skill |
|---|---|
| Preparar / conferir máquina e projeto (fluigcli, mcp-fluig do fork antoniosdn, `FLUIG_MCP_DIR`, registro MCP, conversor do Studio, runtimes) | `fluig-preparar` |
| Dataset novo, refatorar ou auditar (inclui dataset de ação `saveAndSendTask`/`startProcess`) | `dataset-fluig` |
| Form, zoom, pai-filho, anexo | `form-fluig` |
| Evento de workflow, `displayFields`/`enableFields`/`validateForm`, service task, gateway, `.process` | `fluig-workflow` |
| Fluxo de processo novo a partir de descrição (spec → .process + ECM30 + SVG pelo mcp-fluig, publicação em teste); reconstruir o `.process` de processo que só existe no servidor (`fluig_flow_read` → `fluig_flow_generate`, com perdas) | `fluig-fluxo` |
| `beforeSendValidate` / obrigatório | `fluig-validacao` |
| Widget WCM nova | `fluig-scaffolding-widget` |
| Layout WCM novo | `fluig-scaffolding-layout` |
| Trocar CSS próprio por Style Guide | `fluig-style-guide-helpers` |
| Dark mode (cores fixas → `var(--fs-color-*)`) | `fluig-dark-mode` |
| Publicar / importar / baixar processo existente (scripts, form; XML e SVG pelo mcp-fluig) / diff / audit / deploy / log / helper | `fluig-cli` |
| Revisar frontend sem alterar (geral, segurança, performance, acessibilidade) | `fluig-code-review`, `fluig-review-security`, `fluig-review-performance`, `fluig-review-accessibility` |
| Corrigir XSS / sanitizar entrada no frontend | `fluig-validate-security` |
| Otimizar performance de widget/tela | `fluig-optimize-performance` |
| Corrigir acessibilidade de markup | `fluig-improve-accessibility` |
| Migrar jQuery → ES6+ (só código de browser) | `fluig-migrate-jquery-es6` |
| Testar / regressão automatizada de processo (suíte `testes/<processo>.json`, API do fluigcli + formulário headless) | `fluig-teste` (orquestrador) |
| Teste manual pela interface com evidência para aceite ou GMUD, sem suíte | `fluig-tester` |

## Agentes deste plugin

| Agente | Modelo | Papel |
|---|---|---|
| `fluig-planejador` | Opus medium | Levanta (fontes e servidor, só leitura) e grava o `plano-*.md`; devolve resumo curto ao orquestrador. Modo `aplicar-sugestoes` ou `perguntar` para regra de cliente |
| `fluig-executor` | Sonnet medium | Implementa um `plano-*.md` aprovado; publica com fluigcli só quando o plano manda. Versão de processo: edita o `.process`, regenera ECM30 + SVG com `fluig-mcp regenerar` e deixa a publicação para `fluig_flow_deploy` na sessão principal |
| `fluig-revisor` | Opus high | Revisa o `git diff` contra o plano e o servidor (só leitura) |
| `fluig-test-runner` | Sonnet medium | Roda a suíte `testes/<processo>.json` aprovada (orquestrador `fluig-teste`) |
| `fluig-test-auditor` | Opus high | Classifica as falhas (processo × teste × ambiente) e rascunha o plano de correção |

Fluxo para mudança média ou grande (vários arquivos, risco Rhino, versão de processo): `fluig-planejador`
(`plano-<descricao>.md`; aprovação do usuário, salvo projeto que define `aplicar-sugestoes`) →
`fluig-executor` → `fluig-revisor`
→ no máximo uma rodada de correção → regressão com `fluig-teste`.

Não usar scaffold oficial TOTVS de form ou dataset. Query Store, se o cliente
tiver, está no `AGENTS.md` do projeto — não inventar endpoint.

## Publicação

Pedir autorização explícita antes de escrever no servidor. MCP Fluig costuma ser
somente leitura. Quem publica é o `fluigcli`.
