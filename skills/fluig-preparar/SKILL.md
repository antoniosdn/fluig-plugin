---
name: fluig-preparar
description: >
  Confere a máquina e o projeto do cliente para o plugin fluig e diz, item a item, o que está ok e o
  que falta, com o comando de instalação: fluigcli (≥ 0.9.6) com servidor cadastrado; Node 20+,
  Python 3, Chrome/Chromium e Java 8+; mcp-fluig do fork antoniosdn/fluig-mcp (o único com o gerador
  de fluxo fluig_flow_*), com dependências, FLUIG_MCP_DIR e registro como servidor MCP; conversor do
  Fluig Studio no cache do mcp-fluig; .gitignore cobrindo as credenciais. Só lê; clone, npm install,
  claude mcp add, FLUIG_MCP_DIR, conversor e .gitignore só com autorização do usuário. Use quando o
  usuário pedir para preparar, configurar ou conferir o ambiente, instalar o mcp-fluig ou o conversor,
  perguntar "o que falta para usar o plugin", começar em máquina ou projeto novo, ou quando outra
  skill (fluig-fluxo, fluig-teste, fluig-cli) ou agente (fluig-executor, fluig-revisor) parar por
  falta de ferramenta, de FLUIG_MCP_DIR ou das ferramentas fluig_flow_*.
---

# Fluig — Preparar a máquina e o projeto

Esta skill descobre o que falta para o plugin funcionar e, com autorização, instala o que é do
plugin. Princípio: **conferir tudo antes, mostrar a lista inteira, executar só o que o usuário
aprovar**. O plugin não traz o mcp-fluig dentro dele de propósito: a configuração é por cliente,
precisa de `npm install` e é fork de outro projeto. Esta skill faz a ponte.

Peça: `scripts/conferir_ambiente.py` (só leitura; Python 3.8+ sem dependências).

## Regras invioláveis

- **Senha nunca passa pela conversa.** Não pedir, não gravar, não imprimir, não pôr em linha de
  comando nem em `.mcp.json`/`~/.claude.json`. O usuário digita a senha no terminal dele (prompt do
  `fluigcli server add`, que grava no keyring) ou preenche ele mesmo o `.env` do projeto. Ao ler
  configuração, mostrar só **nomes** de variáveis, nunca valores.
- **Toda ação que escreve precisa de autorização explícita naquela conversa**, item a item:
  `git clone`, `npm install`, `claude mcp add`, gravar `FLUIG_MCP_DIR`, `instalar-conversor`,
  mudar `.gitignore`, criar `.env` sem senha. Aprovação de um item não vale para outro.
- **Download:** antes de `instalar-conversor --baixar`, informar nome, origem e tamanho
  (13 JARs, ~43 MB, de `update.fluig.com` — TOTVS — e `download.eclipse.org`) e esperar o sim.
- **Não instalar runtime nem ferramenta de sistema:** Node, Python, Java, Chrome e o próprio
  fluigcli só se conferem e se orientam; o usuário instala no terminal dele.
- **mcp-fluig é o fork** `https://github.com/antoniosdn/fluig-mcp`. O original
  (`alucardigo/fluig-mcp`) não tem `fluig_flow_*`: se a pasta for o original, avisar que falta o
  gerador de fluxo e propor clonar o fork. Nunca mexer no checkout que já existe (pode ter
  mudança local do usuário).
- Produção não entra aqui: servidor MCP de escrita só para teste/homologação; registro de
  produção, se o usuário quiser, com `FLUIG_READONLY=1`.

## Roteiro

1. **Conferir.** Localizar e rodar o script na raiz do projeto do cliente:

   ```bash
   P=$(ls -d ~/.claude/plugins/cache/*/fluig/*/skills/fluig-preparar/scripts 2>/dev/null | sort -V | tail -1)
   python3 "$P"/conferir_ambiente.py --projeto "$PWD" --json
   ```

   (`--mcp-dir <pasta>` se o mcp-fluig estiver num lugar que o script não acha.) Saída 0 = nada
   falta; 1 = algum `FALTA`. Cada item traz `status` (`OK`, `FALTA`, `AVISO`), `detalhe`, `acao`
   (o comando) e `escreve` (a ação grava algo → pedir autorização).
2. **Conferir a sessão.** O script vê a configuração; quem prova o registro é a lista de
   ferramentas desta sessão. Procurar ferramentas cujo nome **termina** em `fluig_flow_validate`,
   `fluig_flow_generate`, `fluig_flow_regenerate`, `fluig_flow_read` e `fluig_flow_deploy` (o prefixo
   `mcp__<nome>__` depende do nome do registro; incluir as ferramentas adiadas, que só aparecem
   pelo nome). `fluig_flow_deploy` ausente com as outras presentes = `FLUIG_READONLY=1` no registro.
   Registro presente no script e ferramentas ausentes na sessão: a sessão foi aberta antes do
   registro (abrir sessão nova) ou o servidor não subiu (`claude mcp list`; timeout → `MCP_TIMEOUT`).
3. **Relatar** numa tabela só, na ordem do script:

   | Item | Situação | O que fazer |
   |---|---|---|
   | fluigcli | OK 0.9.6 | — |
   | mcp-fluig | FALTA: é o original, sem gerador de fluxo | clonar o fork (escreve) |

   Terminar com a lista numerada **só das ações que escrevem** e perguntar, uma vez, quais executar.
   O que é do usuário (instalar Node/Java/Chrome/fluigcli, digitar senha) vai separado, com o comando.
4. **Executar** só as aprovadas, na ordem: clone → `npm install` → `FLUIG_MCP_DIR` → `.env` →
   registro → conversor → `.gitignore`. Erro numa ação: parar, mostrar a saída e não seguir para
   as que dependem dela.
5. **Reconferir** com o script e relatar o que mudou. Registro MCP ou `FLUIG_MCP_DIR` novos só
   valem em **sessão nova** do Claude Code: dizer isso no fim.

## Cada item

### fluigcli (alorenco/fluig-cli) ≥ 0.9.6

- Instalar (o usuário roda): macOS/Linux
  `curl -fsSL https://raw.githubusercontent.com/alorenco/fluig-cli/main/install.sh | sh`;
  Windows `irm https://raw.githubusercontent.com/alorenco/fluig-cli/main/install.ps1 | iex`.
  Versão antiga: `fluigcli upgrade`.
- Servidor: `fluigcli server list` (o script roda na pasta do projeto, que pode ter
  `.fluigcli/servers.json`). Sem servidor, o usuário roda no terminal dele
  `fluigcli server add --name <nome> --host <host> --port <porta> --username <usuario> --env hml --default`
  (`--ssl=false` se for HTTP); a senha é pedida pelo prompt e vai para o keyring.
  Só servidor `prod` cadastrado é `AVISO`: teste e geração de fluxo precisam de `hml` ou `dev`.
- fluigcliHelper (`fluigcli server install-helper`) só quando um comando sair com exit 7
  (skill `fluig-cli`); não faz parte desta conferência.

### Node 20+, Python 3, Chrome/Chromium, Java 8+

Só conferir e orientar. Node 20.6+ (o registro com `--env-file` exige). Navegador: Chrome,
Chromium ou Brave (camada 2 do `fluig-teste`). Java: o mcp-fluig procura `FLUIG_MCP_JAVA` →
`JAVA_HOME` → `java` do PATH, e o script faz o mesmo. Sugestões: Node LTS em nodejs.org (ou
`brew install node`/nvm), JDK Temurin em adoptium.net (ou `brew install --cask temurin`).

### mcp-fluig (fork antoniosdn/fluig-mcp)

O script procura a pasta em `--mcp-dir`, `FLUIG_MCP_DIR`, no `env` de `.claude/settings*.json`
do projeto e em lugares comuns (`~/DESENV/mcp-fluig`, `~/fluig-mcp` …) e confere:

| Conferência | Faltando |
|---|---|
| `server.js` na pasta | `git clone https://github.com/antoniosdn/fluig-mcp.git <pasta>` e `cd <pasta> && npm install` (perguntar a pasta; sugerir `~/DESENV/mcp-fluig`) |
| `git remote get-url origin` contém `antoniosdn/fluig-mcp` | original `alucardigo/fluig-mcp`: avisar que **não tem o gerador de fluxo** e propor clonar o fork em outra pasta; outro origin: `AVISO`, decide a linha de baixo |
| `node_modules/@modelcontextprotocol/sdk` | `cd <pasta> && npm install` |
| `node server.js --list` lista as 5 `fluig_flow_*` (não carrega credencial) | fork desatualizado: `git pull && npm install` na pasta (com autorização; antes, `git status` para não atropelar mudança local) |

### FLUIG_MCP_DIR

Os agentes `fluig-executor` e `fluig-revisor` usam `$FLUIG_MCP_DIR` no Bash. Duas formas
(perguntar qual):
- **no projeto** (recomendado, não versionado): `env` em `.claude/settings.local.json`, mesclando
  com o que já existir no arquivo, sem apagar chaves:
  `{ "env": { "FLUIG_MCP_DIR": "<pasta absoluta do mcp-fluig>" } }`. Conferir que
  `.claude/settings.local.json` não é versionado (`git check-ignore`).
- **na máquina:** `export FLUIG_MCP_DIR="<pasta>"` no perfil do shell (`~/.zshrc`, `~/.bashrc`).

Vale em sessão nova.

### Servidor MCP registrado no projeto

Registro recomendado: escopo `local` (fica em `~/.claude.json`, só nesta máquina e neste projeto),
credencial lida de um arquivo do projeto fora do Git, nada de senha na configuração:

```bash
claude mcp add fluig --scope local -- node --env-file=<projeto>/.fluigcli/<servidor-teste>.env "<FLUIG_MCP_DIR>/server.js"
```

- O arquivo `.fluigcli/<servidor-teste>.env` tem `FLUIG_HOST`, `FLUIG_USER`, `FLUIG_PASS` e,
  se precisar, `FLUIG_COMPANY` e `FLUIG_USERCODE` (lista completa no `.env.example` do mcp-fluig).
  Se não existir, criar **só com as chaves e `FLUIG_PASS=` vazio** (com autorização), `chmod 600`,
  e pedir que o usuário preencha a senha no editor dele. O mesmo arquivo pode ter
  `FLUIGCLI_PASSWORD` para o fluigcli.
- `--scope project` grava `.mcp.json`, que é versionado: só se o usuário pedir, e nunca com senha.
- Registro já existente com variável de senha no `env` (o script avisa pelo nome da chave):
  propor trocar pelo `--env-file`; o usuário move a senha.
- Com `FLUIG_READONLY=1` no `.env`, `fluig_flow_deploy` some (validar e gerar seguem).
- Registro novo vale em sessão nova.

### Conversor do Fluig Studio (ECM30 oficial)

Cache em `~/.fluig-mcp` (ou `FLUIG_MCP_CACHE`), uma vez por máquina. O script confere presença
(`studio/<versão>/manifesto.json`) e a integridade pela mesma função que o mcp-fluig usa ao gerar.

- **De um Studio instalado** (preferir): achar a pasta `plugins` que tem
  `com.totvs.tds.ecm.designer.export.bpmn20_*.jar` (ex.: `/Applications/Eclipse.app/Contents/Eclipse/plugins`;
  `find / -name 'com.totvs.tds.ecm.designer.export.bpmn20_*.jar' 2>/dev/null` com a permissão do
  usuário) e rodar `node "$FLUIG_MCP_DIR/server.js" instalar-conversor --de <pasta plugins | raiz do Eclipse | studio.zip>`
  (aceita 1.8.2.0 e 2.0.0.2; `--versao 1.8.2.0|2.0.0.2|todas` se houver as duas). É o mesmo que
  `fluig-mcp instalar-conversor` quando o binário está no PATH.
- **Download** (sem Studio): `node "$FLUIG_MCP_DIR/server.js" instalar-conversor --baixar 1.8.2.0`.
  Só existe para 1.8.2.0. Pedir autorização antes, com nome, origem e tamanho (regra acima); o
  comando confere tamanho e SHA-256 de cada JAR.
- O 2.0.0.2 só entra por `--de`. Sem ele, `versaoAlvo` 1.8.2 usa o 1.8.2.0 normalmente; para
  `versaoAlvo` 2.0 é preciso o 2.0.0.2.
- Cache inválido (`E_CONVERSOR_CACHE`): reinstalar com `--forcar`.
- Sem conversor, o `fluig-fluxo` gera pelo plano B (`W_ECM30_NAO_OFICIAL`) e alguns casos são
  recusados: dá para seguir, mas avisar.

### .gitignore do projeto

`.env` e `.fluigcli/*.env` precisam estar ignorados. Arquivo de credencial existente fora do
`.gitignore` é `FALTA`; conferir também `git ls-files .env .fluigcli` (se já foi versionado,
avisar o usuário: tirar do índice e trocar a senha é decisão dele).

## Como esta skill conversa com as outras

- `fluig-fluxo`: pré-requisitos 1 (ferramentas `fluig_flow_*`) e 4 (conversor) vêm daqui.
- `fluig-executor` / `fluig-revisor`: sem `FLUIG_MCP_DIR`, param e apontam para esta skill.
- `fluig-teste`: fluigcli com servidor `hml`/`dev`, Python 3, Chrome e Node (camada 3).
- `fluig-cli`: uso do fluigcli depois de instalado; helper no servidor.
