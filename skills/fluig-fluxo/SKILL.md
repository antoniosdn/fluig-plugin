---
name: fluig-fluxo
description: >
  Monta o fluxo (diagrama BPM) de um processo TOTVS Fluig a partir de uma descrição em linguagem
  natural, com as ferramentas fluig_flow_* do servidor MCP mcp-fluig: conversa com o usuário,
  escreve a spec v1 (atividades, ligações, responsável por papel, gateways com regras, serviço com
  tratamento de erro), valida no servidor de teste, gera o .process (editável no VS Code), o ECM30
  do conversor oficial do Studio e o SVG, e publica a versão só em servidor de teste com autorização.
  Use quando o usuário pedir para criar, desenhar ou montar um processo/workflow/fluxo Fluig novo,
  ajustar as etapas de um fluxo a partir de uma descrição, gerar o .process sem abrir o VS Code ou
  o Studio, ou mencionar fluig_flow_validate, fluig_flow_generate, fluig_flow_deploy ou "spec do fluxo".
  Não use para scripts de evento ou edição pontual de um .process existente (fluig-workflow),
  formulário (form-fluig) nem para testar o processo (fluig-teste).
---

# Fluig — Montar o fluxo de um processo (spec → .process)

Esta skill transforma a descrição de um processo em um fluxo Fluig: spec v1, `.process`, ECM30 e SVG,
pelas ferramentas `fluig_flow_*` do mcp-fluig. Princípio: **o agente não inventa o que é decisão do
usuário** (papel, campo, valor, formulário, tratamento de erro, versão). O validador confere a estrutura
e o servidor de teste; o resto se pergunta. Depois de gerado, o `.process` é a fonte da verdade do desenho.

Referências: `references/formato-spec.md` (formato da spec), `references/codigos.md` (códigos de erro e
aviso e o que fazer), `references/exemplos/*.json` (specs que validam e geram).

## Quando usar

Usar:
- processo novo a partir de uma descrição;
- esboço de fluxo para o usuário ajustar no VS Code;
- ajuste das etapas de um fluxo que ainda não tem dependências (seção "Ajustar o fluxo de um processo que já existe");
- reconstruir o `.process` de um processo que só existe no servidor (seção "Baixar um processo existente");
- publicar em teste uma versão gerada.

Não usar:

| Pedido | Skill |
|---|---|
| Script de evento, `servicetaskNNN` | `fluig-workflow` |
| Ajuste pontual num `.process` que já existe e tem scripts | `fluig-workflow` (+ `verificar_process.py`), depois `fluig_flow_regenerate` |
| Formulário | `form-fluig` |
| Testar o processo | `fluig-teste` |
| Qualquer coisa em produção | não faz |

## Pré-requisitos (conferir antes de começar)

1. Servidor MCP **mcp-fluig** com `fluig_flow_validate`, `fluig_flow_generate`, `fluig_flow_regenerate`,
   `fluig_flow_read` e `fluig_flow_deploy`. O prefixo (`mcp__<nome>__`) depende de como o projeto registrou
   o servidor; procurar pelo sufixo. Sem elas, parar e carregar a skill **`fluig-preparar`**, que confere
   e (com autorização) instala: o mcp-fluig precisa ser o fork
   [antoniosdn/fluig-mcp](https://github.com/antoniosdn/fluig-mcp) (o original `alucardigo/fluig-mcp` não
   tem o gerador de fluxo), com `npm install`, `FLUIG_MCP_DIR` e o registro como servidor MCP do projeto
   (`node <mcp-fluig>/server.js --list | grep fluig_flow` lista as 5).
2. **Toda chamada leva `env: "teste"`.** O servidor exige `env` sem default e `fluig_flow_deploy` recusa
   `"prod"`. Esta skill não lê nem escreve produção. Na dúvida sobre qual é o servidor de teste do
   projeto, `fluig_version` (env teste) mostra o host.
3. `fluig_flow_deploy` some quando o servidor MCP roda com `FLUIG_READONLY=1` ("Ferramenta desconhecida
   ... FLUIG_READONLY"). Validar e gerar continuam funcionando.
4. **ECM30 oficial:** Java 8+ e o conversor do Studio no cache local (`~/.fluig-mcp` ou `FLUIG_MCP_CACHE`),
   uma vez por máquina (a skill `fluig-preparar` confere presença e integridade e conduz a instalação):
   `fluig-mcp instalar-conversor --de <pasta plugins do Studio | studio.zip>`
   (aceita 1.8.2.0 e 2.0.0.2) ou `fluig-mcp instalar-conversor --baixar 1.8.2.0` (só existe download do
   1.8.2.0; o 2.0.0.2 só por `--de`). O `--baixar` baixa JARs da internet: **pedir autorização ao usuário
   antes** (nome, origem, tamanho ~43 MB; o comando mostra o total antes de baixar). Sem conversor, `conversor: "auto"` cai no **plano B** (gerador
   próprio) com o aviso `W_ECM30_NAO_OFICIAL`: avisar o usuário e preferir instalar antes de publicar.
   Para `versaoAlvo` 1.8.2 com só o 2.0.0.2 instalado, o gerador usa o 2.0.0.2 e avisa `W_STUDIO_SUBSTITUTO`.
5. Sem servidor MCP (só a máquina): `node <mcp-fluig>/server.js gerar <spec.json> --projeto <pasta> <1.8.2|2.0>`
   gera os três arquivos sem credencial, mas não confere papéis nem campos (`W_SEM_LOOKUP`). Serve para
   esboço, não para publicar.

## Regras invioláveis

- **Nunca produção:** `env: "teste"` em toda chamada; publicação só em servidor de teste, homologação ou demo.
- `fluig_flow_deploy` só com **autorização explícita do usuário naquela conversa**, depois de mostrar
  `processId`, `novo`, `versaoAlvo`, a entrada (`spec` ou `processo`) e o servidor. `confirm: true` só então.
- Não inventar papel, campo, valor de condição, formulário, atividade de tratamento de erro nem
  `versaoAlvo`. Placeholder (`"PERGUNTAR"`) nunca vai para validate/generate.
- Não corrigir em silêncio: todo erro ou aviso do validador é mostrado ao usuário com a correção proposta.
- **Processo de teste que recebeu solicitação nunca mais pode ser excluído** (o Fluig recusa retirar ou
  excluir com solicitação pendente, cancelada ou concluída). Reaproveitar o mesmo `processId` de teste
  (versão nova com `novo: false`) em vez de criar processos descartáveis; não iniciar solicitação nele
  sem o usuário pedir; avisar isso antes de passar para `fluig-teste`.
- Gravar em disco só com `projeto` (caminho absoluto) e só na pasta de projeto que o usuário indicou.
  `sobrescrever: true` só a pedido (o `.process` atual vai para `workflow/.resources/.backups/`).

## Roteiro

1. **Conversar e levantar.** Montar a lista de atividades, decisões e responsáveis e fazer as perguntas
   da próxima seção (agrupadas, uma rodada; não perguntar o que a descrição já responde). Ler as opções
   no servidor de teste (só leitura) para perguntar com alternativas reais:
   - `fluig_form_list` (filtro) para o `formId`;
   - `fluig_form_fields` (`documentId` = formId) para os campos;
   - `fluig_dataset_run` com `name: "workflowRole"` e `fields: ["workflowRolePK.roleId"]` para os papéis;
   - `fluig_process_versions` (`processId`) para saber se o processo já existe (`novo`).
2. **Mostrar o fluxo em texto** (atividade → responsável; gateway → condição → destino) e a spec
   resumida. Esperar o usuário confirmar o desenho.
3. **Montar a spec v1** (`references/formato-spec.md`; partir de um dos `references/exemplos/`).
4. **`fluig_flow_validate`** com `spec`, `versaoAlvo` e `env: "teste"`. Ler `ok`, `versaoServidor`,
   `erros[]` e `avisos[]` (`codigo`, `mensagem`, `caminho`). Cada código está em `references/codigos.md`.
   Erro de decisão do usuário (papel ou campo inexistente, tratamento ausente): perguntar. Erro de
   estrutura: corrigir a spec e mostrar o que mudou. Repetir até `ok: true` e levar os avisos ao usuário.
5. **`fluig_flow_generate`** com `projeto` = raiz absoluta do projeto Fluig do usuário (a que tem ou terá
   `workflow/`), a mesma `spec` e `versaoAlvo`, `conversor` omitido (`auto`) ou `"oficial"`. Sem `projeto`
   nada é gravado (só devolve o conteúdo): usar assim só para prévia. Mostrar `conversor` (oficial ou
   proprio), os três caminhos, `ids` (atividade → elemento; em `erp → servicetask3` o número do fim é o
   número da atividade no Fluig), `scripts` criados e os avisos. Opcional: rodar `verificar_process.py`
   (skill `fluig-workflow`) no `.process` gerado; deve dar 0 problema.
6. **O usuário confere o `.process` no VS Code** (extensão Fluiggers): layout, nomes, atribuições. Se ele
   editar e salvar, a extensão regenera ECM30 e SVG; sem VS Code aberto, `fluig_flow_regenerate`
   (`processo` = caminho absoluto de `<projeto>/workflow/diagrams/<processId>.process`, `versaoAlvo`).
   Daqui em diante o `.process` manda: mudança de desenho volta para ele, não para a spec.
7. **Publicar em teste** (só com autorização, ver regras): `fluig_flow_deploy` com
   - `processo` (preferido: leva os scripts reais de `<projeto>/workflow/scripts/<processId>.*.js`) **ou**
     `spec` (gera num temporário; a versão sai só com os scripts vazios de serviço, serve para processo de
     teste sem scripts);
   - `versaoAlvo`, `novo` (`true` = processo novo; `false` = versão nova de existente, conferido no
     passo 1), `confirm: true` e `env: "teste"`.

   Com `novo: false`, a definição geral (categoria, volume, expediente, instrução) vem de lugares
   diferentes conforme a entrada:
   - `spec`: vem do servidor (`W_DEFINICAO_HERDADA`); a descrição vem da spec (ou do servidor, se a spec
     não tiver). Em 2.0, categoria 2.0 e ícone também.
   - `processo`: vem do próprio `.process`; do servidor só a categoria 2.0 e o ícone. Não sai
     `W_DEFINICAO_HERDADA`. O `.process` gerado pela spec sai **sem categoria e sem instrução**: categoria
     definida no servidor dá `E_CATEGORIA_TROCADA`, e instrução vazia no `.process` **apaga** a do
     servidor, sem aviso.
   - Regra: antes de publicar `processo` + `novo: false`, ler a definição do servidor com
     `fluig_process_export_xml` (`env: "teste"`; `categoryId` e `instruction` do `ProcessDefinition`).
     Se houver categoria ou instrução, mostrar a diferença ao usuário e pedir que as acerte nas
     propriedades do processo no VS Code (ou regenerar depois) **antes** de publicar; ou publicar com
     `spec` quando o processo de teste não tem scripts.

   Ler `publicado`; se `false`, ver `motivo` e `errosServidor`/`errosPorTipo` (`references/codigos.md`).
   Depois: pedir ao usuário que abra a versão no editor web; oferecer `fluig-workflow` para escrever os
   scripts de serviço e `fluig-teste` para testar (com o aviso sobre solicitações).

## Quando perguntar em vez de inventar

| Decisão | Como perguntar / o que oferecer |
|---|---|
| Responsável de cada atividade humana | Papel existente (lista do `workflowRole`); `pool_papel` (vai para a fila do papel e alguém assume) ou `papel` (comportamento usual do Fluig: quem envia escolhe entre os usuários do papel). Atividade sem responsável gera `W_HUMANA_SEM_RESPONSAVEL` (o Fluig pede o executor ao movimentar): só com o usuário concordando. Papel novo não se cria: o usuário cria no Fluig ou escolhe outro. |
| "Gestor imediato" / "gerente da área do solicitante" | Não é papel: muda conforme quem abriu. Fora da v1 (Campo Formulário, mecanismo customizado). Oferecer: papel provisório (vai para a fila de todos do papel) ou sem responsável, e trocar a atribuição no VS Code depois (Campo Formulário com a matrícula do gestor preenchida no formulário, ou mecanismo customizado), publicando com `processo` + conversor oficial. Perguntar se o projeto já tem mecanismo de atribuição ou campo com o gestor. |
| Formulário vinculado (`formId`) | Lista do `fluig_form_list`. Sem `formId` as regras não são conferidas e o deploy recusa (`W_SEM_FORMULARIO`). |
| Campo e valor de cada condição | Campos de `fluig_form_fields`; o **valor gravado** (value do select/radio, ex.: `S`/`N`), não o rótulo da tela. Operador entre os 10 da v1. Para `maior`/`menor`... avisar `W_OPERADOR_COMPARACAO` (texto x número não confirmado) e perguntar como o valor fica gravado; campo de moeda com máscara (`5.000,00`) não compara como número — usar um campo oculto numérico ou condição `js` (não conferida). |
| Saída padrão do gateway | Para onde vai quando nenhuma condição bate (`padrao: true`). |
| Decisão do usuário ou automática | Quem decide ao movimentar = atividade humana com duas ou mais saídas (o executor escolhe). Decisão por campo = `gateway_exclusivo` com regras. |
| Serviço: `automatizada` ou `imediata` | Automatizada = assíncrona, com tentativas, **exige `tratamentoErro`** e uma única saída. Imediata = síncrona na movimentação, sem captura de erro. |
| Tratamento de erro do serviço automatizado | Qual atividade **humana** trata a falha, de que papel, e para onde ela segue (normalmente volta ao serviço: ligação `trata → servico`). |
| "Devolver ao solicitante" | Não há ligação para o `inicio` (`E_INICIO_ENTRADA`) nem atribuição "Executor Atividade" na v1. Opções: atividade humana de correção atribuída a um papel; sem responsável (quem movimenta escolhe); ou gerar assim e trocar a atribuição no VS Code para Executor Atividade, publicando depois com `processo` + conversor oficial. `retorno: true` na ligação (permitir retorno do Fluig) também é opção, a confirmar no teste. |
| `versaoAlvo` | Versão do Fluig **onde o processo vai rodar em produção**, não a do servidor de teste. Se diferem (ex.: teste 2.0, produção 1.8.2), gerar para a menor (1.8.2), que o 2.0 aceita; `versaoAlvo` maior que o servidor é recusada (`E_VERSAO_SERVIDOR`). `fluig_flow_validate` devolve `versaoServidor` do teste; a de produção, perguntar. |
| `processId` | Confirmar o id (sem espaço; letras, números e `_`). Se já existe no teste (`fluig_process_versions`): é o mesmo processo (versão nova, `novo: false`) ou outro id? |
| Retorno nas ligações | Quais etapas podem devolver para a anterior; nunca em ligação que entra numa junção paralela. |

## O que a publicação real ensinou

1. Serviço automatizado sem `tratamentoErro` não passa (o Studio exige a captura de erro e o editor exige
   saída nela): `E_TRATAMENTO_AUSENTE`. A captura é criada pelo gerador; a ligação captura → tratamento
   **não** entra em `ligacoes`.
2. Junção paralela não aceita ligação de entrada com retorno (o servidor recusou a liberação): `E_RETORNO_JUNCAO`.
3. O Fluig não libera serviço sem script: o gerador cria `workflow/scripts/<processId>.servicetaskN.js`
   **vazio** (`function servicetaskN() {}`) e avisa `W_SCRIPT_SERVICO_VAZIO`. O processo publica, mas o
   serviço não faz nada até alguém escrever a integração (`fluig-workflow`). Dizer isso ao usuário.
4. A definição geral do processo (categoria, ícone, volume, expediente, instrução) é **comum a todas as
   versões**. Em processo novo (`novo: true`) sai vazia/padrão: o usuário define categoria e ícone no
   editor web depois. Em versão nova (`novo: false`) depende da entrada: com `spec` o deploy **herda do
   servidor** (`W_DEFINICAO_HERDADA`); com `processo` vale o que está no `.process` (sem aviso), e o
   `.process` gerado pela spec não tem categoria nem instrução. Nos dois casos recusa trocar uma
   categoria já definida (`E_CATEGORIA_TROCADA`), e no caminho `processo` instrução vazia apaga a do
   servidor (regra de leitura prévia no roteiro, passo 7). A `descricao` da spec vira a descrição do
   processo (vale para todas as versões).
5. Ligação automática por prazo, timer, subprocesso, eventos de mensagem/sinal e o resto dos limites
   abaixo ficam fora da v1: não prometer.
6. Processo de teste com solicitação não se exclui mais. O mesmo `processId` de teste é reaproveitado.
7. Se a liberação falha, a versão fica **importada e em edição** (`W_VERSAO_EM_EDICAO`). Corrigir e publicar
   de novo com `novo: false` cria outra versão; a em edição continua lá (não apagar sem pedido).

## Limites da v1 (não prometer; dizer o caminho)

Fora da spec v1:
- subprocesso; eventos de mensagem e sinal; timer/espera e ligação automática por prazo;
- prazos, escalonamento e notificações; raias;
- nome da condição (`condicao.nome` é recusado na geração do `.process`, `E_PROCESS_CONDICAO_NOME`, mesmo em 2.0);
- atribuição por Grupo, Pool Grupo, Usuário, Campo Formulário, Executor Atividade, Grupos do Colaborador,
  Associado ou mecanismo customizado (só `papel` e `pool_papel`);
- scripts de evento (só o script vazio do serviço); permissões de quem inicia o processo; categoria e ícone em processo novo.

Caminho quando o usuário precisa disso: gerar a base pela spec, ajustar no VS Code (Fluiggers) e publicar
com `processo` e conversor **oficial** (o plano B recusa Executor Atividade, Campo Formulário, captura de
erro fora do formato e fluxo por prazo: `E_PLANO_B_RECUSADO`). Ajuste feito no editor web não volta para o
`.process` local: a próxima publicação a partir do `.process` sobrescreve o desenho do servidor. Avisar e
combinar com o usuário onde fica a fonte da verdade.

Etapa que só é alcançada por prazo (escalonar se não aprovar em N dias): na spec, uma ligação comum da atividade para a etapa de escalonamento (sem ela a etapa fica inalcançável, `E_INALCANCAVEL`); depois, no VS Code, trocar essa ligação por fluxo automático por prazo e configurar o expediente se for em dias úteis. Até lá, a ligação aparece como saída manual que o executor pode escolher. Publicar com `processo` + conversor oficial (o plano B recusa fluxo por prazo).

## Ajustar o fluxo de um processo que já existe

1. `fluig_flow_read` (`processId`, `env: "teste"`) devolve `spec`, `ignorados` (`I_*`: o que a spec v1 não
   guarda: prazos, raias, scripts, campos extras) e `avisos` (`W_LEITOR_*`). Mostrar `ignorados` ao usuário:
   **gerar de novo pela spec perde tudo o que está lá** (desenho, prazos, scripts na versão).
2. Os números das atividades saem da ordem da spec (início = 1, seguindo a ordem do array; a captura de
   erro de um serviço automatizado consome o número seguinte ao dele). `fluig_flow_generate` ignora
   `origem` (`W_ORIGEM_IGNORADA`). Conferir: na spec lida cada id vem como `s<número>`; depois de gerar,
   `ids["s<n>"]` precisa terminar no mesmo `<n>`. Se algum número mudar, scripts e eventos de formulário
   que usam `WKNumState`/`servicetaskNNN` quebram: **parar e mostrar ao usuário**.
3. Processo com `.process` no projeto, scripts ou qualquer `ignorados` relevante: não regerar pela spec.
   Editar o `.process` (`fluig-workflow`), `fluig_flow_regenerate` e `fluig_flow_deploy` com `processo`.

## Baixar um processo existente para o projeto (reconstruir o `.process`)

O servidor não guarda o `.process` do Studio; o que ele tem é o `.ecm30.xml` e o SVG publicado
(`fluig_process_export_xml`, `fluig_process_diagram_get`). Quando o projeto precisa de um `.process`
editável de um processo que já existe, o caminho é **reconstruir**, e é com perdas:

1. Scripts e formulário pelo fluigcli (skill `fluig-cli`): `workflow import <processId>` e
   `form import <nome>`. Rodar antes do passo 3: o ECM30 regenerado leva os scripts de `workflow/scripts`.
2. `fluig_flow_read` (`processId`, `env: "teste"`). Mostrar `ignorados` e `avisos` ao usuário **antes**
   de gerar: o `.process` reconstruído não terá desenho original (posições vêm do gerador), prazos,
   raias, campos extras de atividade/ligação nem `I_SERVICO_CONFIG`; isso é ajustado depois no VS Code
   ou fica de fora. `W_LEITOR_*` = a leitura já não reproduz fielmente; decidir com o usuário se vale.
3. `fluig_flow_generate` com a `spec` lida, `projeto` (raiz absoluta), `versaoAlvo` e `env`.
   Conferir a numeração como na seção anterior: cada `ids["s<n>"]` precisa terminar em `<n>`; número
   diferente quebra `WKNumState`/`servicetaskNNN` dos scripts importados → parar e mostrar.
4. Não publicar em seguida. O `.process` reconstruído é ponto de partida para edição local; a próxima
   `fluig_flow_deploy` com `processo` **sobrescreve o desenho do servidor** pelo gerado. Avisar.

## Como esta skill conversa com as outras

- `fluig-workflow`: scripts dos serviços (`servicetaskN`, nome igual ao de `ids`), eventos, edição pontual
  do `.process` e `verificar_process.py`.
- `form-fluig`: os campos que as condições usam precisam existir no formulário (e com o valor combinado).
- `fluig-teste`: depois de publicar em teste; avisar antes que solicitações tornam o processo permanente.
- `fluig-cli`: não publica diagrama gerado (o `fluigcli workflow publish` reaproveita o diagrama do
  servidor). A publicação do fluxo é sempre `fluig_flow_deploy`.
- Fluxo orquestrado (plano, `fluig-executor`, `fluig-revisor`): a spec aprovada vai no plano (ou num arquivo
  citado por ele). O executor **gera** pela CLI (`node "$FLUIG_MCP_DIR/server.js" gerar ...`) e não publica;
  o revisor confere a spec e o `.process`; a publicação fica com a sessão principal, que tem as
  ferramentas MCP, via `fluig_flow_deploy` e com autorização.
