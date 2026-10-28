# fluig-plugin

Plugin do **Claude Code** para customização **TOTVS Fluig**: skills de formulário, dataset,
workflow, fluxo de processo, widget/layout e Style Guide; agentes que implementam e revisam
um plano; e um orquestrador de testes de processo.

O diferencial é a **geração do fluxo de processo**: a partir de uma descrição em português, o
agente monta o diagrama BPM, gera `.process`, ECM30 e imagem prontos para o Fluig e publica a
versão em servidor de teste, sem abrir o Fluig Studio
([como funciona](#geração-de-fluxo-de-processo)).

O plugin é genérico. O que é de cada cliente (integrações, IDs de processo, servidores,
regras de publicação) fica no `AGENTS.md` do repositório do cliente, que vence o plugin
quando os dois divergem.

- [Instalação](#instalação)
- [Pré-requisitos](#pré-requisitos)
- [Como usar](#como-usar)
- [Geração de fluxo de processo](#geração-de-fluxo-de-processo)
- [O que vem no plugin](#o-que-vem-no-plugin)
- [Regras que o plugin segue](#regras-que-o-plugin-segue)
- [Projetos de terceiros](#projetos-de-terceiros)
- [Licença](#licença)

## Instalação

No Claude Code:

```
/plugin marketplace add antoniosdn/fluig-plugin
/plugin install fluig@fluig
```

Para atualizar quando sair versão nova:

```bash
claude plugin marketplace update fluig && claude plugin update fluig@fluig
```

A versão instalada está em `.claude-plugin/plugin.json`; o histórico, no `git log`.

### No repositório do cliente

1. Remover as cópias locais de skills Fluig (`.agents/skills/`, `.claude/skills/`), se houver.
   Elas competem com as do plugin.
2. Deixar no `AGENTS.md` do cliente só o que é dele: servidores e ambientes, processos,
   serviços integrados (Protheus, RM, Query Store etc.) e regras de publicação.
3. Não versionar credencial: `.env` e `.fluigcli/*.env` vão no `.gitignore`.

## Pré-requisitos

Nem tudo é necessário para tudo. Instale conforme o que for usar.

A skill **`fluig-preparar`** confere a máquina e o projeto e diz, item a item, o que está ok e o
que falta, com o comando de instalação. Peça no projeto do cliente ("prepara o ambiente do
plugin fluig", ou `/fluig:fluig-preparar`). Ela só lê; clonar e instalar o mcp-fluig, registrar o
servidor MCP, definir `FLUIG_MCP_DIR` e instalar o conversor do Studio ela faz só com sua
autorização, item a item. Senha nunca passa pela conversa. O script de conferência também roda
sozinho, a partir do plugin instalado:

```bash
python3 "$(ls -d ~/.claude/plugins/cache/*/fluig/*/skills/fluig-preparar/scripts | sort -V | tail -1)/conferir_ambiente.py" --projeto "$PWD"
```

| Ferramenta | Para quê | Usada por |
|---|---|---|
| [fluigcli](https://github.com/alorenco/fluig-cli) ≥ 0.9.6, com o servidor cadastrado (`fluigcli server add`) | publicar, exportar, `diff`, `audit`, log, movimentar solicitações | `fluig-cli`, `fluig-executor`, `fluig-revisor`, `fluig-teste` |
| fluigcliHelper no servidor (`fluigcli server install-helper`) | comandos que a API nativa não cobre | `fluig-cli` (o fluigcli avisa com exit 7) |
| Python 3 | scripts de teste e de conferência do `.process` | `fluig-teste`, `fluig-workflow` |
| Google Chrome ou Chromium | formulário em navegador headless (camada 2) | `fluig-teste` |
| Node.js (20+ para o mcp-fluig) | `proxy_tela.mjs` (camada 3) e o mcp-fluig | `fluig-teste`, `fluig-fluxo` |
| [mcp-fluig](https://github.com/antoniosdn/fluig-mcp), **do fork antoniosdn** (o gerador de fluxo não existe no original), registrado como servidor MCP, e `FLUIG_MCP_DIR` apontando para a pasta dele | gerar/validar/publicar fluxo de processo; versão de processo com imagem | `fluig-fluxo`, `fluig-executor`, `fluig-revisor` |
| Java 8+ e o conversor do Fluig Studio no cache do mcp-fluig (`fluig-mcp instalar-conversor`) | ECM30 oficial do processo | `fluig-fluxo` |
| Extensão [Fluiggers](https://github.com/fluiggers/fluig-vscode-extension) no VS Code | conferir e ajustar o `.process` gerado | `fluig-fluxo` (recomendado) |

Detalhes de cada um estão em `fluig-preparar`, na própria skill (seção de pré-requisitos) e no
README do mcp-fluig.

## Como usar

As skills entram sozinhas pelo assunto do pedido ("cria um dataset que…", "adiciona um
pai-filho no formulário", "publica o form"). Também dá para chamar pelo nome:
`/fluig:fluig-teste`, `/fluig:fluig-fluxo` etc.

### Qual skill para qual pedido

A referência canônica desta tabela é o [`AGENTS.md`](AGENTS.md) do plugin, que é o que o modelo lê;
esta é uma cópia para consulta.

| Pedido | Skill |
|---|---|
| Preparar ou conferir a máquina e o projeto (fluigcli, mcp-fluig, conversor do Studio, runtimes) | `fluig-preparar` |
| Dataset novo, refatorar ou auditar (inclui dataset de ação `saveAndSendTask`/`startProcess`) | `dataset-fluig` |
| Formulário, zoom, pai-filho, anexo | `form-fluig` |
| Validação de envio (`beforeSendValidate`, obrigatórios) | `fluig-validacao` |
| Evento de workflow, `displayFields`/`enableFields`/`validateForm`, service task, gateway, `.process` | `fluig-workflow` |
| Fluxo de processo novo a partir de uma descrição; reconstruir o `.process` de um processo que só existe no servidor | `fluig-fluxo` |
| Widget ou layout WCM novo | `fluig-scaffolding-widget`, `fluig-scaffolding-layout` |
| Trocar CSS próprio por Style Guide; dark mode | `fluig-style-guide-helpers`, `fluig-dark-mode` |
| Revisar frontend sem alterar (geral, segurança, performance, acessibilidade) | `fluig-code-review`, `fluig-review-security`, `fluig-review-performance`, `fluig-review-accessibility` |
| Corrigir frontend (XSS, performance, acessibilidade) | `fluig-validate-security`, `fluig-optimize-performance`, `fluig-improve-accessibility` |
| Migrar jQuery para ES6+ (só código de browser) | `fluig-migrate-jquery-es6` |
| Publicar, importar, baixar processo existente (scripts e form pelo fluigcli; XML e SVG pelo mcp-fluig), `diff`, `audit`, release, log | `fluig-cli` |
| Testar / regressão automatizada de processo (suíte `testes/<processo>.json`) | `fluig-teste` |
| Teste manual pela interface com evidência para aceite ou GMUD, sem suíte | `fluig-tester` |

### Mudança média ou grande: plano → executor → revisor → teste

Para mudança em vários arquivos, versão nova de processo ou qualquer coisa com risco no Rhino:

1. **Planejar** com o agente `fluig-planejador` (Opus medium), que levanta nos fontes e no servidor
   e grava o `plano-<descricao>.md` na raiz, sem ocupar o contexto da sessão principal. Regra de
   cliente: devolve as dúvidas (`perguntar`) ou aplica a sugestão (`aplicar-sugestoes`, quando o
   projeto define).
2. **Executar** com dois agentes em paralelo, cada um com o caminho do plano. O planejador marca
   cada step: `[escritor]` vai para o `fluig-escritor` (Haiku) — formulário (HTML, `custom.js`,
   `custom_valida.js`, `zoom.js`, `ajuda_config.js`, eventos do form) e cópias idênticas, quando o
   plano traz tudo e não há decisão; `[executor]` vai para o `fluig-executor` (Sonnet). Step do
   executor que depende do formulário (publicar) leva `(depois do escritor)`: o executor devolve
   `AGUARDANDO_ESCRITOR` e é retomado com `SendMessage` quando o escritor termina, recebendo junto
   os steps que o escritor devolveu pendentes. O `fluig-executor` implementa e
   publica com fluigcli quando o plano manda. Versão de processo: o executor edita o `.process` e
   regenera ECM30 + SVG com `fluig-mcp regenerar` (informar `FLUIG_MCP_DIR`); quem publica é a
   sessão principal, com `fluig_flow_deploy` e autorização do usuário.
3. **Revisar** com o agente `fluig-revisor`: plano + `git diff`, conferindo no servidor
   (só leitura). Devolve APROVADO ou REPROVADO com cada item marcado como erro de execução
   ou de plano.
4. **Corrigir** no máximo uma rodada com o executor. Erro de plano volta para o usuário.
5. **Testar** com `fluig-teste` (regressão).

Commit é sempre a pedido do usuário; nenhum agente faz commit.

### Testes de processo (`fluig-teste`)

O orquestrador levanta o processo, monta a suíte `testes/<processo>.json` (versionada no
projeto do cliente), pede aprovação e roda em três camadas:

| Camada | O que faz | Quem roda |
|---|---|---|
| 3 — tela | caminho feliz pela interface real, pelo `fluigcli dev` + `proxy_tela.mjs`; é o primeiro teste | sessão principal |
| 1 — fluxo | cria e movimenta solicitações reais pela API do fluigcli (inclui anexos) | `fluig-test-runner` |
| 2 — formulário | regras de tela em navegador headless | `fluig-test-runner` |

As falhas vão para o `fluig-test-auditor`, que separa defeito do processo de defeito do teste
e rascunha o plano de correção. Defeito do processo segue o fluxo plano → executor → revisor.

Só roda em servidor não produtivo (o `env` do servidor no fluigcli não pode ser `prod`).
Nesse caso cria as solicitações de teste sem pedir confirmação a cada uma.

## Geração de fluxo de processo

Skill `fluig-fluxo`. Normalmente o diagrama de um processo Fluig é desenhado à mão no Fluig
Studio (Eclipse) ou na extensão Fluiggers do VS Code. Aqui o usuário descreve o processo
("solicitação de compra, o gestor aprova, se aprovado compras efetua, senão encerra") e sai
a versão publicada em teste, com os mesmos arquivos que o Studio geraria.

### Como funciona

```
descrição ──► conversa ──► spec v1 (JSON) ──► validate ──► generate ──► conferência ──► deploy
 (usuário)    (agente +     atividades,        estrutura +   .process     no VS Code     versão no
              servidor de   ligações,          servidor de   ECM30        (Fluiggers)    servidor de
              teste)        papéis, regras     teste         SVG                         teste
```

1. **Conversa.** O agente monta a lista de atividades, decisões e responsáveis e pergunta, numa
   rodada só, o que a descrição não responde. As opções vêm do servidor de teste (só leitura):
   formulários, campos do formulário, papéis (`workflowRole`) e se o processo já existe.
   **O agente não inventa** papel, campo, valor de condição, formulário, tratamento de erro nem
   versão do Fluig.
2. **Desenho em texto.** Antes de gerar, mostra o fluxo (atividade → responsável; gateway →
   condição → destino) e espera o usuário confirmar.
3. **Spec v1.** Um JSON com atividades e ligações (formato em
   [`skills/fluig-fluxo/references/formato-spec.md`](skills/fluig-fluxo/references/formato-spec.md),
   exemplos em [`references/exemplos/`](skills/fluig-fluxo/references/exemplos/)).
4. **Validação** (`fluig_flow_validate`). Confere a estrutura (fluxo alcançável, gateway com saída
   padrão, serviço com tratamento de erro…) e, no servidor de teste, se papéis e campos existem e
   qual a versão do Fluig. Cada erro ou aviso tem um código com a correção documentada em
   [`references/codigos.md`](skills/fluig-fluxo/references/codigos.md); nada é corrigido em silêncio.
5. **Geração** (`fluig_flow_generate`). Grava no projeto do usuário:
   - `workflow/diagrams/<processId>.process`: o diagrama editável, montado com as mesmas funções da
     extensão Fluiggers e relido contra a spec antes de gravar;
   - `workflow/.resources/<processId>.ecm30.xml`: o XML que o Fluig importa, gerado pelo
     **conversor oficial do Fluig Studio** (ou por um gerador próprio, com aviso, se o conversor
     não estiver instalado);
   - `workflow/.resources/<processId>.processimage.svg`: a imagem do diagrama;
   - `workflow/scripts/<processId>.servicetaskN.js` vazio para cada serviço (o Fluig não libera
     serviço sem script).
6. **Conferência no VS Code.** O usuário abre o `.process` na Fluiggers e ajusta layout, nomes e
   atribuições. A partir daqui o `.process` é a fonte da verdade; mudança de desenho volta para
   ele, não para a spec (`fluig_flow_regenerate` refaz ECM30 e SVG).
7. **Publicação** (`fluig_flow_deploy`). Só em servidor de teste e só com autorização na conversa,
   depois de mostrar processo, versão alvo, origem e servidor. Publica a versão com a imagem e os
   scripts reais do projeto. Produção é recusada pela própria ferramenta.

Depois disso: `fluig-workflow` escreve os scripts de serviço e eventos; `fluig-teste` testa o
processo.

### O que a spec v1 cobre

| Cobre | Fica fora (ajustar no VS Code depois) |
|---|---|
| Início, fim, cancelamento, fim terminativo, atividade humana, gateway exclusivo e paralelo (abertura e junção) | Subprocesso, eventos de mensagem e sinal, timer |
| Serviço automatizado (assíncrono, com captura de erro e atividade de tratamento) e imediato | Ligação automática por prazo, escalonamento, notificações, raias |
| Responsável por `papel` ou `pool_papel` | Grupo, usuário, Campo Formulário, Executor Atividade, mecanismo customizado |
| Condição por campo do formulário (10 operadores) ou JavaScript | Nome da condição |
| Retorno nas ligações; versão alvo 1.8.2 ou 2.0 | Categoria e ícone em processo novo; scripts de evento |

O que fica fora sai como base pela spec e é ajustado na Fluiggers; a publicação segue pelo
`.process` com o conversor oficial. Também dá para ler um processo existente como spec
(`fluig_flow_read`), com a lista do que a spec não guarda antes de regerar.

### Do que depende

| Peça | Papel |
|---|---|
| **mcp-fluig** ([antoniosdn/fluig-mcp](https://github.com/antoniosdn/fluig-mcp)) | Servidor MCP com as ferramentas `fluig_flow_validate`, `generate`, `regenerate`, `read` e `deploy`. É um fork do [alucardigo/fluig-mcp](https://github.com/alucardigo/fluig-mcp); **o gerador de fluxo só existe no fork**. Node.js 20+. |
| **Recorte da Fluiggers 3.0.1** (dentro do mcp-fluig) | Monta e valida o `.process` com o mesmo código que a extensão usa ao editar, sem precisar do VS Code. |
| **Conversor do Fluig Studio** + Java 8+ | Gera o ECM30 oficial. Instalado uma vez por máquina no cache do mcp-fluig (`fluig-mcp instalar-conversor --de <plugins do Studio ou studio.zip>`; aceita 1.8.2.0 e 2.0.0.2). Os JARs são da TOTVS/Eclipse e não são distribuídos. Sem ele, o ECM30 sai do gerador próprio, com aviso, e alguns casos são recusados. |
| **Servidor Fluig de teste** | Validação de papéis, campos e versão, e destino da publicação. Toda chamada leva `env: "teste"`. |
| **Extensão Fluiggers no VS Code** (recomendada) | Conferir e ajustar o diagrama gerado. |

Sem servidor MCP dá para gerar um esboço pela linha de comando
(`node <mcp-fluig>/server.js gerar <spec.json> --projeto <pasta> <1.8.2|2.0>`), sem conferência
de papéis e campos.

### Cuidados

- Processo de teste que recebeu solicitação **não pode mais ser excluído** no Fluig. Reaproveite
  o mesmo `processId` de teste (versão nova) em vez de criar processos descartáveis.
- Em versão nova de processo existente, a definição geral (categoria, instrução, expediente) é
  comum a todas as versões; a skill lê a do servidor antes de publicar para não apagá-la.
- No fluxo orquestrado, o `fluig-executor` só **gera** pela linha de comando; quem publica é a
  sessão principal, com autorização.

## O que vem no plugin

| Pasta | Conteúdo |
|---|---|
| `skills/` | 21 skills (tabela acima) e seus scripts: `fluig-teste/scripts/` (`executar_fluxo.py`, `testar_formulario.py`, `proxy_tela.mjs`), `fluig-workflow/scripts/verificar_process.py` e `fluig-preparar/scripts/conferir_ambiente.py` |
| `agents/` | `fluig-planejador` (Opus), `fluig-escritor` (Haiku), `fluig-executor` (Sonnet), `fluig-revisor` (Opus), `fluig-test-runner` (Sonnet), `fluig-test-auditor` (Opus) |
| `context/` | Arquitetura, convenções, tecnologias e Style Guide do Fluig, lidos pelas skills de frontend (widget, layout, formulário HTML); não servem a datasets nem a scripts de workflow |
| `examples/` | Widget e layout WCM mínimos |
| `rules/` | `fluig-rhino-es5.md`: referência das regras ECMA 5 / Rhino (datasets, scripts de workflow, `displayFields.js`) |

**Não entra no plugin:** Query Store ou endpoints de um cliente, documentação Word timbrada,
credenciais, IDs de processo, nem binários de terceiros (fluigcli, mcp-fluig, conversor do
Studio, Chrome).

## Regras que o plugin segue

- **Dois motores de JavaScript.** `datasets/`, `workflow/scripts/` e
  `forms/*/events/displayFields.js` rodam no Rhino: ECMA 5, só `var` e `function(){}`.
  HTML/JS de formulário e widgets rodam no browser: ES6+ liberado.
- **Escrita no servidor só com autorização explícita** na conversa. Quem publica é o fluigcli
  (ou o mcp-fluig, para versão de processo). Produção nunca entra em teste nem em geração de fluxo.
- **Padrão próprio de form e dataset.** Não usar o scaffold oficial da TOTVS para form ou
  dataset; o padrão é `form-fluig` e `dataset-fluig`.
- **Não inventar integração.** Endpoint, Query Store e dataset de cliente vêm do `AGENTS.md`
  do projeto.
- Respostas e documentação em português (BR), mantendo os nomes técnicos do Fluig.

## Projetos de terceiros

| Projeto | Licença | Relação com este plugin |
|---|---|---|
| [totvs/fluig-agent-skills](https://github.com/totvs/fluig-agent-skills) | MIT | **Material incluído.** `context/`, `examples/widget`, `examples/layout` e as skills `fluig-scaffolding-*`, `fluig-style-guide-helpers`, `fluig-code-review`, `fluig-review-*`, `fluig-dark-mode`, `fluig-validate-security`, `fluig-optimize-performance`, `fluig-improve-accessibility` e `fluig-migrate-jquery-es6`. Testado pela TOTVS no Fluig 2.0 (Voyager); no 1.8.x, revisar o resultado. |
| [alorenco/fluig-cli](https://github.com/alorenco/fluig-cli) | ver o repositório | **Ferramenta usada, não distribuída.** CLI não oficial, base da publicação, do `diff`, do `audit` e da camada de fluxo dos testes. A skill `fluig-cli` é texto próprio. |
| [antoniosdn/fluig-mcp](https://github.com/antoniosdn/fluig-mcp) (mcp-fluig), fork de [alucardigo/fluig-mcp](https://github.com/alucardigo/fluig-mcp) | MIT | **Ferramenta usada, não distribuída.** Servidor MCP do Fluig criado por Rodrigo de Souza Faria; o gerador de fluxo (`fluig_flow_*`) foi acrescentado no fork. |
| [fluiggers/fluig-vscode-extension](https://github.com/fluiggers/fluig-vscode-extension) | MIT | **Usada indiretamente.** O `.process` é gerado com funções da extensão (recorte que fica no mcp-fluig) e conferido nela no VS Code. |
| Fluig Studio (TOTVS) e Eclipse | proprietária / EPL | **Usado na máquina do usuário.** O conversor ECM30 é instalado pelo mcp-fluig a partir do Studio; os JARs não vêm com este plugin. |
| [matheusnevoa/fluig-tester](https://github.com/matheusnevoa/fluig-tester) | ver o repositório | **Inspiração.** Metodologia da skill `fluig-tester`; nenhum trecho copiado. |
| [Wisleey/Skill-FLUIG-TOTVS-Cursor](https://github.com/Wisleey/Skill-FLUIG-TOTVS-Cursor) | ver o repositório | **Inspiração.** Protocolo da skill `fluig-workflow`; nenhum trecho copiado. |

Os scripts de `fluig-teste` baixam do **servidor Fluig do próprio cliente** os arquivos do
portal (jQuery, jQuery UI, Mustache, Style Guide) para um cache local
(`~/.cache/fluig-teste/assets`). Eles não são distribuídos com o plugin.

TOTVS e Fluig são marcas da TOTVS S.A. Este projeto é independente e não é afiliado,
patrocinado nem endossado pela TOTVS. A TOTVS não se responsabiliza por código gerado por
ferramentas de IA.

## Licença

MIT. Ver [`LICENSE`](LICENSE) e [`NOTICE`](NOTICE).
