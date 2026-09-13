# fluig-plugin

Plugin de skills para customização **TOTVS Fluig** (Cursor e Claude Code).

Substitui a cópia de `.agents/skills/` em cada cliente — o mesmo motivo do
`advpl-protheus-plugin`. O repositório do cliente fica só com o que é dele
(integrações, processos, publicação).

## Conteúdo

| Pasta | O que tem |
|---|---|
| `skills/` | Dataset, form, validação, orquestração, widget/layout, Style Guide, review, fluigcli |
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
/plugin install fluig@ascendra
```

## Instalação (Cursor)

Repositório local:

```
/Users/antoniosdn/DESENV/fluig-plugin
```

Symlink para descoberta imediata:

```
ln -sfn /Users/antoniosdn/DESENV/fluig-plugin ~/.cursor/plugins/local/fluig
```

Ou adicione o repo como plugin a partir do GitHub depois do clone.

## No projeto do cliente

Depois de o plugin estar instalado e validado, remover as skills Fluig locais
(`.agents/skills/` / `.claude/skills/`). No `AGENTS.md` do cliente fica só o
específico: serviços (Lyceum, Protheus, Query Store), processos, servidor e
regras de publicação.

## Origem do material TOTVS

`context/`, `examples/widget`, `examples/layout` e as skills `fluig-scaffolding-*`,
`fluig-style-guide-helpers`, `fluig-*-review` e `fluig-dark-mode` vêm do
[totvs/fluig-agent-skills](https://github.com/totvs/fluig-agent-skills) (MIT).
Testadas pela TOTVS em Fluig 2.0 (Voyager). Em 1.8.x revisar o resultado.

## Licença

MIT. Ver `LICENSE` e `NOTICE`.
