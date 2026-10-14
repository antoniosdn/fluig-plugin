---
name: fluig-teste
description: Orquestrador de testes de processos TOTVS Fluig em 3 camadas — fluxo pela API do fluigcli (cria e movimenta solicitações reais), formulário em navegador headless e, opcionalmente, interface real pelo proxy autenticado (fluigcli dev). Levanta o processo, monta a suíte testes/<processo>.json, pede aprovação, roda com o subagente fluig-test-runner, audita com o fluig-test-auditor e propõe correção dos defeitos. Use quando o usuário pedir para testar, homologar, rodar a regressão ou "ver se o processo roda certinho", ou digitar /fluig-teste.
---

# /fluig-teste — orquestrador de testes Fluig

Você (sessão principal) orquestra. Execução e auditoria vão para subagentes; você não roda os
cenários na mão nem lê o código do processo inteiro — levanta, planeja com o usuário, delega e
relata.

Peças: `scripts/executar_fluxo.py` (camada 1), `scripts/testar_formulario.py` (camada 2),
`formato-suite.md` (formato da suíte), agentes `fluig-test-runner` (Sonnet medium) e
`fluig-test-auditor` (Opus high).

## Regras invioláveis

- **Ambiente:** só servidor de homologação/demo. O nome do servidor fica na suíte e o script
  aborta se o fluigcli responder por outro. Produção: não roda, nem com pedido.
- **Credenciais:** as do fluigcli (keyring ou `.env` do projeto, no `.gitignore`). Ninguém
  digita senha. Nunca imprimir o conteúdo do `.env`.
- **Autorização:** a camada 1 CRIA e MOVIMENTA solicitações. Por decisão do usuário
  (2026-10-13), em servidor **não produtivo** (o `env` do servidor no fluigcli não é `prod`:
  `fluigcli server list`) o orquestrador cria as solicitações de teste **sem pedir aprovação** e
  lista no relatório as que criou. Em servidor `prod` a camada 1 **não roda** (o script aborta).
  Servidor sem `env` definido conta como produtivo até o usuário marcar. Camada 2 não toca o
  servidor e roda sempre.
- **Teste não corrige.** Nenhum agente deste fluxo publica, altera formulário, script ou dataset.
  Defeito vira item do relatório e proposta de correção.
- **Solicitações de teste ficam.** Não cancelar nem apagar sem o usuário pedir; listar no
  relatório as que ficaram abertas.

## Fluxo

### 0. Suíte existe?
`testes/<processo>.json` no projeto. Se existe e o processo não mudou desde a última rodada
(`git log` dos fontes do processo × data da suíte), pular para o passo 2 (regressão).

### 1. Levantar e montar a suíte (Opus, com o usuário)
- Versão e atividades: `fluigcli workflow version`, `dataset query processState`.
- Fluxo e decisões: `db query` em `LINK_PROCES` e `ESTADO_PROCES_COND`; scripts em
  `workflow/scripts/<processId>.*.js` (o que leem do card, o que gravam, histórico).
- Formulário: `custom.js` por atividade, `beforeSendValidate`, ajuda (`ajuda_config.js`).
- Para processo grande, delegar o levantamento a um agente `Explore` e receber só o resumo.
- Escrever `testes/<processo>.json` seguindo `formato-suite.md`: um cenário por final e por
  desvio; casos de tela por atividade e por regra de validação.
- Validar com `python3 <dir desta skill>/scripts/executar_fluxo.py testes/<processo>.json --simular`.
- Mostrar ao usuário a matriz (cenário → caminho esperado → final) e seguir para a execução
  (regra "autorização": em servidor não produtivo não se pede aprovação).

### 2. Executar (subagente `fluig-test-runner`)
Passar: caminho da suíte, camadas aprovadas (1, 2, 3), cenários aprovados, pasta de saída
(`testes/resultados/`). O runner devolve um relatório curto e os arquivos de resultado.

Camada 3 (interface real) só quando o usuário pedir aceite com prints: o runner sobe o proxy
(`.claude/launch.json` → `fluigcli dev`) e abre o formulário de cada solicitação por
`/webdesk/streamcontrol/...` pelo navegador do app. Limite conhecido: a tela "Movimentar
Solicitação" do portal fica em branco pelo proxy (o iframe usa o host do servidor fixo); por isso
a movimentação é sempre pela camada 1.

### 3. Auditar (subagente `fluig-test-auditor`)
Passar: suíte, arquivos de resultado, lista de solicitações criadas. Ele confere no servidor (só
leitura), separa **defeito do processo** de **defeito do teste** (suíte errada, dado de teste
incompleto) e, para cada defeito do processo, escreve um rascunho de plano de correção.

### 4. Relatar ao usuário
Na resposta, curto:
- placar por camada e tabela cenário → solicitação → resultado;
- defeitos do processo (com o rascunho de correção) e defeitos do teste (o que ajustar na suíte);
- solicitações que ficaram abertas;
- bloco "Evidência para GMUD" (ambiente, data, cenários com resultado, caminho dos resultados).

Defeito do teste: corrigir a suíte você mesmo e oferecer rodar de novo.
Defeito do processo: o usuário aprova o plano → `fluig-executor` + `fluig-revisor` (ver CLAUDE.md
global) → oferecer rodar a suíte de novo como regressão.

## Comandos de referência

```bash
python3 <dir desta skill>/scripts/executar_fluxo.py testes/<p>.json --simular
python3 <dir desta skill>/scripts/executar_fluxo.py testes/<p>.json --cenario <id> --saida testes/resultados
python3 <dir desta skill>/scripts/testar_formulario.py testes/<p>.json --saida testes/resultados
```

Armadilhas já conhecidas: tarefa de pool precisa de `fluigcli task assume` antes do
`request move` (o script já faz); aprovação sem gateway exige `destino`; campos de
zoom/autocomplete não existem no headless.
