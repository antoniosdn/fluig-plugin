# fluigcli — comandos por grupo

Resumo do mapa upstream (`skills/fluigcli/reference/commands.md` em
[alorenco/fluig-cli](https://github.com/alorenco/fluig-cli)). Flags exatas:
`fluigcli <grupo> <sub> --help`.

## server

| Comando | Efeito |
|---|---|
| `server add --name n --host h --env dev\|hml\|prod` | cadastra (senha no keyring, nunca em arquivo) |
| `server list` · `server use <n>` | lista · define padrão |
| `server test [<n>]` | login + ping + versão do helper (`helperVersion` × `cliHelperWAR`) |
| `server status [<n>]` | versão, helper, uptime, memória, banco (admin) |
| `server install-helper [<n>]` | instala/atualiza o helper; recusa downgrade |

Alvo: `--server`/`FLUIGCLI_SERVER` > padrão do projeto > padrão global > único.
Config versionável em `.fluigcli/servers.json`; usuário e padrão pessoal em
`.fluigcli/servers.local.json` (git-ignorado).

## clone

`clone --all` ou `--only forms,datasets,workflows,events,mechanisms,widgets`.
Não-interativo exige um dos dois. Widgets exigem helper (pulados no `--all`,
exit 7 no `--only widgets`). `workflows` = só scripts de evento.

## dataset

| Comando | Efeito |
|---|---|
| `dataset new <nome>` | esqueleto local em `datasets/` |
| `dataset list [--custom-only] [--search t]` | lista do servidor |
| `dataset import <id>... \| --all` | servidor → local |
| `dataset export <arquivo>... [--new]` | local → servidor; audita antes |
| `dataset query <id> [--fields a,b] [--constraint ...]` | executa o dataset |
| `dataset enable\|disable <id>` | liga/desliga (reversível) |
| `dataset history <id> [--version N]` · `dataset restore <id> <v>` | histórico · restaura (cria versão nova) |
| `dataset delete <id>` | físico, só `CUSTOM`; helper ≥ 0.7.0 |

`dataset query` com HTTP 500 e aspa simples na constraint: o dataset monta SQL
por concatenação — defeito do script, não da consulta.

## form

| Comando | Efeito |
|---|---|
| `form new <nome> [--title t]` | esqueleto em `forms/<nome>/` |
| `form import <documentId\|nome>... \| --all` | servidor → local (com eventos e anexos) |
| `form export <pasta> [--document-id id] [--version keep\|new]` | padrão cria versão nova (`keep` mantém); audita `RHINO*`/`FL*`; criação: `--new --parent-id --dataset-name` |
| `form link <pasta> --document-id <id>` | vincula pasta ↔ form em `.fluigcli/forms.json` (sem prompt) |
| `form link --auto` | vincula por nome; falha com pastas de nome técnico |
| `form records list\|show\|create\|update\|delete` | dados do form; create/update não rodam eventos |

## event / mechanism

`new`, `list`, `import <id>... | --all`, `export <arquivo>...` (audita antes),
`delete <id>...`. Pastas `events/` e `mechanisms/`. Mecanismo devolve userCodes,
não logins.

## workflow

| Comando | Efeito |
|---|---|
| `workflow new-script <processId> <evento>` | cria `workflow/scripts/<processId>.<evento>.js` com assinatura correta |
| `workflow list [--active-only]` · `version` · `versions` | processos e versões |
| `workflow import <processId> [--version n] [--stdout]` | baixa scripts; `--stdout` não grava |
| `workflow export <arquivo\|processId>` | atualiza scripts na versão corrente (helper); atômico |
| `workflow diff <arquivo\|processId>` | local × publicado (read-only) |
| `workflow publish <processId> [--events a,b] [--no-release]` | versão nova; sem `--events` sobe todos os scripts locais |
| `workflow convert <processId> --from v --to v [--all\|--instance id] [--map A=B]` | migra solicitações abertas; sem `--all`/`--instance` só mostra o plano |

## widget

`widget new <code>`, `list`, `import <code>` (helper; grava `wcm/widget/<code>/`),
`export <code>` (nativo; `--build` para SPA).

## diff / deploy / audit / watch / dev

| Comando | Efeito |
|---|---|
| `diff [<caminho>...]` | local × servidor; `--json` traz `data.counts` |
| `deploy --plan release.json` | passos `dataset`, `event`, `mechanism`, `form`, `widget`, `workflow` (publish), `db` (SQL de leitura); para no 1º erro; `--from N` retoma; `--dry-run` valida sem escrever; trava de prod pedida uma vez; plano nunca contém senha |
| `audit [<caminho>...] [--process id] [--fix] [--save-baseline]` | linter local; exit 1 = reprovado |
| `watch` | publica ao salvar; só dev/hml; nunca cria artefato ou versão |
| `dev` | proxy local do portal com live reload e preview de form |

## Operação

| Comando | Efeito |
|---|---|
| `request list --process id --status open\|canceled\|finalized` | solicitações por status |
| `request show\|start\|move\|cancel\|assignees\|attachments` | consulta e movimentação |
| `request observe <n> --text "..."` | comentário sem movimentar |
| `request move <n> --manager [--target-state N] --yes` | destrava atividade automática |
| `task list [--group c\|--role c\|--automatic]` · `task summary` · `task assume <n>` | fila de tarefas |
| `document list <id> --recursive` · `find --name "x*"` · `show` · `move` · `download` · `upload` · `mkdir` | GED |
| `log files` · `log tail --follow --level --grep --since` · `log download` | log do servidor (helper) |
| `db datasources` · `db query "<sql>" [--param v] [--file x.sql]` · `db grants <tabela>` | SQL de leitura via JNDI (helper ≥ 0.6.0) |

## Administração (requer admin)

`user list|show|create|update|activate|deactivate|audit|roles|groups|add-role|...`,
`group ...`, `role ...`, `replacement ...`. `user audit <login>` lista o que o
usuário fez num período.

## Enums de processo (medidos no Voyager 2.0, não é contrato TOTVS)

`PROCES_WORKFLOW.STATUS`: 0 aberta · 1 cancelada · 2 concluída.

`TAR_PROCES.IDI_STATUS`: 0 aberta · 1 consenso pendente · 2 concluída ·
3 transferida · 4 cancelada. `CLOSURE_STATUS` = SLA no encerramento
(1 no prazo, 2 alerta, 3 atrasada), não resultado. `LOG_ATIV = 1` = tarefa corrente.
