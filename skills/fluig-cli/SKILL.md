---
name: fluig-cli
description: Publica, audita e sincroniza artefatos Fluig com o fluigcli (alorenco/fluig-cli). Use ao importar/exportar form, dataset, evento global, mecanismo, widget ou script de processo; ao comparar local × servidor (diff), auditar código (audit, regras Rhino/Style Guide), montar release (deploy --plan), clonar servidor, ler log, ou quando mencionar fluigcli / fluigcliHelper.
---

# fluigcli

CLI não oficial ([alorenco/fluig-cli](https://github.com/alorenco/fluig-cli)),
feita para agentes: saída `--json` com envelope fixo e exit codes estáveis.

**Direção dos verbos (contrário do git):** `import` = servidor → local ·
`export` = local → servidor.

Pedir autorização explícita antes de qualquer escrita no servidor. O
`AGENTS.md` do projeto do cliente vence em servidores e regras de publicação.

Guia completo embutido no binário: `fluigcli skill show`. Flags exatas:
`fluigcli <grupo> <sub> --help` (preferir a assumir). Se `fluigcli` não estiver
no `PATH`, procurar em `~/.local/bin/fluigcli`.

## Regras ao executar

1. Comando que **você** roda: sempre `--json --non-interactive`. Em servidor
   `env=prod`, escrita exige `--yes` (sem ele: exit 2) — só com autorização.
2. Decidir pelo **exit code**, não pelo texto:

   | código | significado | ação |
   |---|---|---|
   | 0 | sucesso | seguir |
   | 1 | erro genérico; `AUDIT_FAILED` = audit barrou; `LOCAL_IO_ERROR` = disco | ler `error.code` |
   | 2 | uso incorreto | corrigir flags |
   | 3 | autenticação/sessão | conferir credencial |
   | 4 | não encontrado | conferir id/nome |
   | 5 | erro do servidor Fluig | ler `error.message`; pode ser transitório |
   | 6 | sucesso parcial em lote | inspecionar `data.results[]` item a item |
   | 7 | falta fluigcliHelper no servidor | `fluigcli server install-helper <nome>` (pedir autorização) |

3. Envelope `--json`: stdout tem **um** documento
   `{ok, command, server, data, error}`; log vai para o stderr.
4. Senha: nunca em argumento nem impressa. Ordem: `--password-stdin` →
   `FLUIGCLI_PASSWORD` → keyring → prompt. A sessão fica em cache entre
   execuções. Sem `.fluigcli/servers.local.json`, definir `FLUIGCLI_USERNAME`.
5. `server logout` sem senha reaproveitável trava o próximo comando
   não-interativo — evitar em agente.

## Comando para o usuário rodar à mão (ex.: produção)

Quando você **escreve** o comando para a pessoa executar:

- `--server <nome>` no próprio comando. Nunca `export FLUIGCLI_SERVER=...`
  (vale para os comandos seguintes do terminal e publica em prod sem querer).
- Sem `--json`, `--non-interactive` e `--yes`: a trava de produção precisa
  pedir confirmação.
- Sem senha na linha.
- Manter flags que mudam o efeito (`--new`, `--no-audit`, `--events`, `--build`).

```sh
fluigcli dataset export datasets/ds_nome.js --server prod
fluigcli form export "forms/<pasta>" --server prod
```

## Fluxo de desenvolvimento

1. `fluigcli server test <nome> --json` → exit 0.
2. Artefato novo: scaffold local, sem tocar o servidor —
   `dataset new`, `form new`, `event new`, `mechanism new`, `widget new`,
   `workflow new-script <processId> <evento>`.
3. Auditar: `fluigcli audit <caminho> --json` (exit 1 = reprovado; corrigir
   pelos `data.findings[]` ou `audit --fix` nas regras determinísticas).
   Form com seções `activity-N`: também `audit --process <processId> --json`.
4. Conferir o que muda: `fluigcli diff [<caminho>...] --json`.
5. Publicar: `fluigcli <grupo> export <arquivo|pasta> --json`.
6. Tratar exit 6 olhando `data.results[]`.

## audit — linter local (nada vai ao servidor)

Varre `forms/`, `wcm/widget/`, `datasets/`, `events/`, `mechanisms/`,
`workflow/scripts/`. Regras (lista completa: `fluigcli audit --help`):

- `RHINO002` (erro): sintaxe ES6+ em script server-side — SyntaxError no deploy.
- `RHINO003` (erro): `const` dentro de laço — Rhino congela o 1º valor, sem erro.
- `RHINO001`: `===` entre `java.lang.String` e literal — sempre false; usar `==`
  ou `String(...)`.
- `RHINO004`: `dataset.values[i].coluna` server-side — usar `getValue(i, "coluna")`.
- `FL001`–`FL006`: método inexistente em `hAPI`, `form`, `FLUIGC`,
  `DatasetFactory`, `docAPI`; variável `WK*` desconhecida (null em silêncio);
  método do `hAPI` chamado sem `hAPI.` (FL005, erro).
- `SG001`–`SG007`: Style Guide 2.0 — CDN externo, cor fixa, `!important`,
  `style=`, `alert/confirm` em vez de `FLUIGC`.
- `WF001`–`WF003` (com `--process`): seção `activity-N` sem etapa real, etapa
  humana sem seção, script comparando com número de etapa inexistente.

Todo `export`/`publish` **audita antes**: erro barra o envio (exit 1
`AUDIT_FAILED`). Em form só `RHINO*`/`FL*` barram (`SG*` não). Dívida antiga:
`audit --save-baseline` — preferir a `--no-audit`.

Assinaturas das APIs (`hAPI`, `WK*`, `DatasetBuilder`, `docAPI`, `form.*`,
`FLUIGC`, `wdkAddChild`): `skills/fluigcli/reference/fluig.d.ts` do upstream —
consultar com grep em vez de adivinhar.

## Mapa de comandos

Detalhes, flags e armadilhas por grupo: [reference/comandos.md](reference/comandos.md).

| Objetivo | Comando |
|---|---|
| Baixar tudo de um servidor em uso | `clone --only forms,datasets,...` ou `--all` |
| Publicar artefato | `dataset\|form\|event\|mechanism\|widget export` |
| Script de processo sem versão nova (helper) | `workflow export <arquivo>` |
| Versão nova do processo | `workflow publish <processId> --events a,b` |
| Script local × publicado | `workflow diff <arquivo\|processId>` |
| Release em ordem, auditável | `deploy --plan release.json [--dry-run] [--from N]` |
| Consultar dataset | `dataset query <id> [--fields a,b]` |
| Histórico / restaurar dataset | `dataset history <id>` · `dataset restore <id> <versão>` |
| SQL de leitura (helper) | `db query "<sql>"` · `db grants <tabela>` |
| Solicitações por status | `request list --process <id> --status open\|canceled\|finalized` |
| Fila de tarefas | `task list [--group\|--role]` · `task summary` |
| GED | `document list\|find\|show\|download\|upload` |
| Log do servidor (helper) | `log tail --follow --grep <texto>` · `log files` |
| Saúde do servidor | `server status` |
| Migrar solicitações de versão | `workflow convert <processId> --from v --to v` |
| Publicar ao salvar (só dev/hml) | `watch` |
| Dev server com live reload | `dev` |

## fluigcliHelper

WAR no Fluig (`fluigcli server install-helper`). **Nativo**, sem helper: form e
dataset import/export, `workflow import|diff|publish`, `dataset query`.
**Precisa do helper**: `workflow export`, `widget import`, `log`, `db`,
`dataset delete`. `widget list` tem fallback nativo. `server test` mostra a
versão do helper. A FluiggersWidget da extensão VS Code é outro componente.

## Armadilhas

- `request start|move` e `form records create|update` **não rodam** os eventos
  do formulário (`displayFields`, `validateForm`). Não servem para testar
  validação — testar no navegador ou no `fluigcli dev`.
- `workflow publish` sem `--events` sobe **todos** os scripts locais e pode
  desfazer alteração feita no Studio. Rodar `workflow diff` antes.
- `clone` e `import` sobrescrevem o local. Commitar antes. `clone` não traz
  diagrama, GED, páginas nem usuários.
- `dataset query` vazio volta como 1 linha em branco (`emptyRowSuspect:true`).
- Status em `PROCES_WORKFLOW`: 0 aberta, **1 cancelada, 2 concluída** — usar
  `request list --status` em vez de SQL.
- `widget import` grava em `wcm/widget/<code>/`. Não há `widget delete`.
