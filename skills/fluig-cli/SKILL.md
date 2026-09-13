---
name: fluig-cli
description: Publica e sincroniza artefatos Fluig com o fluigcli (alorenco/fluig-cli). Use ao importar/exportar form, dataset, widget ou script de processo, clonar servidor, ver log, ou quando mencionar fluigcliHelper.
---

# fluigcli

CLI não oficial ([alorenco/fluig-cli](https://github.com/alorenco/fluig-cli)).
Convenção: **import** = servidor → local; **export** = local → servidor.

Pedir autorização explícita antes de qualquer escrita no servidor.

## O que é nativo vs helper

O `fluigcliHelper` é um WAR no Fluig (`fluigcli server install-helper`). Sem ele
ainda funcionam form/dataset import e export, `workflow import`/`diff`/`publish`
e query de dataset.

Com o helper: `workflow export` (script sem nova versão), `widget import`,
`widget list` completo, `log` e `db` via JNDI.

A extensão VS Code procura `GET /fluiggersWidget/api/ping` (outro componente).
O helper da CLI não substitui a FluiggersWidget.

## Comandos frequentes

```bash
fluigcli form export "forms/<pasta>" --document-id <id> --server <nome>
fluigcli form import <documentId> --server <nome>
fluigcli dataset export datasets/ds_nome.js --server <nome>
fluigcli widget import <code> --server <nome>   # precisa do helper
fluigcli widget export <code> --server <nome>   # nativo; lê wcm/widget/<code>/
fluigcli workflow export workflow/scripts/<proc>.<evento>.js --server <nome>
fluigcli workflow publish <processId> --server <nome>
fluigcli log tail --follow --grep <texto> --server <nome>
fluigcli clone --only forms,datasets --server <nome>
```

`clone` sobrescreve o local. Commit antes. Não clona GED, páginas nem usuários.

`widget import` grava em `wcm/widget/<code>/`. Não há `widget delete` na CLI.

Não imprimir senha. Credencial: keyring, `FLUIGCLI_PASSWORD` ou `--password-stdin`.
