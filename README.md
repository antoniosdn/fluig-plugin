# fluig-plugin

Plugin de skills para customização **TOTVS Fluig** (Claude Code).

Substitui a cópia de `.agents/skills/` em cada cliente — o mesmo motivo do
`advpl-protheus-plugin`. O repositório do cliente fica só com o que é dele
(integrações, processos, publicação).

## Conteúdo

| Pasta | O que tem |
|---|---|
| `skills/` | Dataset, form, validação, workflow/eventos de servidor (`fluig-workflow`), widget/layout, Style Guide, review e correção (segurança, performance, acessibilidade), migração jQuery → ES6+, fluigcli, teste funcional de processos (`fluig-tester`), orquestrador de testes automatizados (`fluig-teste`: fluxo pela API do fluigcli + formulário headless, com suíte versionada em `testes/<processo>.json`) |
| `agents/` | `fluig-executor` e `fluig-revisor` (implementação e revisão de plano), `fluig-test-runner` e `fluig-test-auditor` (execução e auditoria de testes) |
| `context/` | Arquitetura, convenções, tecnologias e Style Guide (origem: TOTVS fluig-agent-skills) |
| `examples/` | Widget e layout mínimos oficiais |
| `rules/` | ECMA 5 / Rhino em `datasets/` e `workflow/scripts/` |

**Não entra neste plugin:** Query Store de um tenant, documentação Word timbrada,
credenciais, IDs de processo de um cliente.

Não usar as skills TOTVS de scaffold de form/dataset — o padrão daqui é
`form-fluig` e `dataset-fluig`.

## Instalação (Claude Code)

```
/plugin marketplace add antoniosdn/fluig-plugin
/plugin install fluig@fluig
```

## No projeto do cliente

Depois de o plugin estar instalado e validado, remover as skills Fluig locais
(`.agents/skills/` / `.claude/skills/`). No `AGENTS.md` do cliente fica só o
específico: serviços (Lyceum, Protheus, Query Store), processos, servidor e
regras de publicação.

## Origem do material TOTVS

`context/`, `examples/widget`, `examples/layout` e as skills `fluig-scaffolding-*`,
`fluig-style-guide-helpers`, `fluig-*-review`, `fluig-dark-mode`,
`fluig-validate-security`, `fluig-optimize-performance`,
`fluig-improve-accessibility` e `fluig-migrate-jquery-es6` vêm do
[totvs/fluig-agent-skills](https://github.com/totvs/fluig-agent-skills) (MIT).
Testadas pela TOTVS em Fluig 2.0 (Voyager). Em 1.8.x revisar o resultado.

## Créditos

A skill `fluig-cli` é texto próprio e opera o
[alorenco/fluig-cli](https://github.com/alorenco/fluig-cli), CLI não oficial
que é a base da publicação, do audit e do diff deste plugin.

A skill `fluig-tester` é texto próprio, inspirado na metodologia de
[matheusnevoa/fluig-tester](https://github.com/matheusnevoa/fluig-tester).

A skill `fluig-workflow` é texto próprio, inspirado em
[Wisleey/Skill-FLUIG-TOTVS-Cursor](https://github.com/Wisleey/Skill-FLUIG-TOTVS-Cursor).

## Licença

MIT. Ver `LICENSE` e `NOTICE`.
