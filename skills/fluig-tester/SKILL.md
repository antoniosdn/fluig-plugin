---
name: fluig-tester
description: >
  Conduz teste funcional de processos TOTVS Fluig pela interface web, do início
  ao estado final, com cenários positivos e negativos, conferência do estado
  persistido no servidor e evidências (prints, relatório e JSON) por etapa.
  Use quando o usuário pedir para testar, homologar ou validar ponta a ponta um
  processo/workflow Fluig, gerar evidência de teste para GMUD ou aceite, ou
  mencionar "fluig-tester", "testar o processo", "caminho feliz", "roteiro de
  teste". Não use para corrigir, publicar ou alterar o processo.
---

# Fluig — Teste Funcional de Processos

Executa pela interface do Fluig uma suíte de cenários previamente autorizada e
entrega um resultado rastreável por solicitação, cenário, atividade e
ocorrência. O teste diz se o processo **se comportou como esperado**; a
evidência diz se isso **está comprovado**. As duas coisas são registradas
separadamente.

Inspirada na metodologia de
[matheusnevoa/fluig-tester](https://github.com/matheusnevoa/fluig-tester);
texto e adaptações próprios deste plugin.

## Contexto do cliente

Dados de cliente (URLs, processos, usuários de teste, integrações, destino das
evidências) **não ficam nesta skill**. Antes de começar, procurar no projeto:

1. uma skill complementar do cliente (ex.: `.agents/skills/fluig-tester-<cliente>/`);
2. o `AGENTS.md` / `CLAUDE.md` do projeto;
3. a configuração do `fluigcli` (`.fluigcli/servers.json`), só para identificar
   hosts e qual é homologação — nunca abrir arquivos `.env` com senha.

O que não estiver em nenhuma dessas fontes é perguntado ao usuário.

## Regras invioláveis

- **Homologação por padrão.** Produção só com o ambiente nomeado pelo usuário,
  os efeitos listados e autorização explícita para aquela suíte. Decidir o
  ambiente pelo **host**, não pelo nome do processo nem pelo banner. Se host,
  banner e contexto do cliente divergirem, parar e perguntar.
- **Nada de mudar o sistema para o teste passar.** Não publicar nem alterar
  formulário, script, dataset, diagrama, papel, grupo, permissão ou campo
  oculto. Achado de defeito vira registro no relatório, não correção.
- **Leitura no servidor pode; escrita não.** Consultar histórico, estados e
  valores do card por API/MCP somente leitura é permitido e recomendado para
  confirmar cada passagem. Movimentar, cancelar, assumir ou reatribuir tarefa só
  pela interface, como o usuário faria.
- **Um envio, uma confirmação.** Depois de timeout, erro ou tela travada, não
  reenviar nem recancelar antes de consultar o estado persistido da solicitação.
  Toast não prova transição. Integrações externas não têm rollback.
- **Credenciais são do usuário.** O login é feito pelo usuário no navegador.
  Não digitar senha, não ler arquivo de senha, não gravar cookie, token ou
  sessão nas evidências.
- **Autorização por suíte, não por clique.** Apresentar a matriz de cenários e
  os efeitos esperados, obter um "sim" explícito e, dentro desse escopo,
  executar sem pedir confirmação a cada ação. Qualquer ação fora do escopo
  (cenário novo, outro processo, outro ambiente) exige nova autorização.

## 1. Preparação

### 1.1 Insumos

Reunir, sem perguntar de novo o que já foi informado:

| Insumo | Fonte preferencial |
|---|---|
| Processo (ID e versão publicada) | contexto do cliente; `fluig_process_version` |
| Ambiente e host | contexto do cliente; `.fluigcli/servers.json` |
| Gabarito (regras esperadas) | documentação do processo, guia de teste, pedido do usuário |
| Fluxo (atividades, estados, transições) | diagrama `workflow/diagrams/<processo>.process`; `fluig_process_states_detail` |
| Validações do formulário | `forms/<form>/custom_valida.js` (`beforeSendValidate`) |
| Integrações e efeitos | `workflow/scripts/<processo>.*.js` (service tasks e eventos) |
| Usuários, papéis e substitutos | contexto do cliente; `fluig_process_available_users` |
| Anexos de teste | pasta informada pelo usuário |
| Destino das evidências | contexto do cliente; senão perguntar |

Código e diagrama são lidos **somente para consulta**. Gabarito é expectativa,
código é implementação, interface e histórico são comportamento. Uma fonte não
substitui a outra: divergência entre elas é achado e vai para o relatório.

Se o diagrama local diferir da versão publicada (`fluig_process_version`,
`fluig_process_states`), vale o publicado para executar e a diferença é
registrada.

### 1.2 Navegador

Ordem de preferência no Claude Code:

1. **Navegador embutido do app** (`mcp__Claude_Browser__*`) — isolado, padrão.
2. **Claude in Chrome** (`mcp__claude-in-chrome__*`) — quando o usuário quiser
   usar a sessão já logada no Chrome dele.
3. **Playwright MCP** — se estiver configurado e o usuário preferir.

Confirmar antes de começar: login feito pelo usuário, captura de tela
funcionando, leitura do PNG salvo e gravação no destino das evidências.

### 1.3 Matriz de cenários

Montar uma matriz finita a partir do diagrama e do `custom_valida.js`:

| Família | O que prova |
|---|---|
| Caminho feliz | aprovação ponta a ponta até o estado final esperado |
| Reprovação / cancelamento | cada saída de reprovação ou cancelamento relevante |
| Devolução / correção | retorno a etapa anterior e novo envio (nova ocorrência) |
| Validação negativa | cada regra do `beforeSendValidate` bloqueia o envio e a solicitação **não avança** |
| Anexos | regra de anexo obrigatório, tipo ou quantidade |
| Subramos | gateways com condição (ex.: flag do formulário que muda o caminho) |
| Integração com erro | caminho de tratamento de erro, quando o diagrama tiver |

Regras da matriz:

- finais incompatíveis usam **solicitações diferentes**;
- validações negativas podem ser feitas dentro da solicitação de outro cenário,
  antes do envio válido da mesma etapa;
- não inventar paralelismo, subprocesso ou etapa que o diagrama não tenha;
- cenário inalcançável (sem usuário, sem dado de teste, depende de sistema fora
  do ar) é marcado **bloqueado** já na matriz, com o motivo.

### 1.4 Modo de execução

| Modo | Capturas por etapa | Quando usar |
|---|---|---|
| **completo** | formulário na chegada, após preencher, histórico e diagrama real | aceite formal, GMUD, primeira homologação |
| **econômico** (padrão) | formulário após preencher e histórico | regressão depois de ajuste pequeno |

O usuário escolhe. Na dúvida, recomendar **completo** para processo novo ou
alterado no fluxo e **econômico** para ajuste de formulário.

### 1.5 Autorização

Antes da primeira ação que crie ou movimente solicitação, apresentar em um só
bloco: ambiente e host, processo e versão, cenários com o final esperado de
cada um, usuários/substitutos, anexos, modo, destino das evidências e **efeitos
externos previstos** (o que cada integração vai gravar e onde). Pedir um "sim"
explícito e registrar o escopo aprovado no `resultado.json`.

## 2. Execução por etapa

Para cada ocorrência de atividade humana:

1. **Localizar.** Abrir a tarefa pela Central de Tarefas ou pela solicitação.
   Conferir número da solicitação, atividade, ocorrência, responsável e se a
   tela está em modo de execução ou consulta. Em pool, assumir pela interface.
   Se o card da Central falhar, abrir pelos detalhes da solicitação antes de
   concluir que está inacessível.
2. **Capturar a chegada** (modo completo).
3. **Validação negativa**, se prevista para esta etapa: deixar o dado inválido,
   tentar enviar, capturar a mensagem, confirmar que a atividade não mudou.
4. **Preencher** só o que o cenário pede. Em campo de observação editável,
   escrever texto identificável:
   `[TESTE <execucao>] <cenario> · <atividade> · ocorrência <n> · <decisão>`.
   Campo somente leitura não é tocado. Anexos pelo botão do formulário, com
   arquivo da pasta de teste; esperar o formulário mostrar o anexo carregado.
5. **Capturar após preencher**, com decisão, observação e anexo visíveis.
6. **Conferir os arquivos** da ocorrência (seção 3) antes de enviar.
7. **Enviar uma vez.**
8. **Confirmar no servidor** com as ferramentas somente leitura:
   - `fluig_process_history` — a movimentação apareceu, com o destino certo;
   - `fluig_process_active_states` — a atividade atual é a esperada;
   - `fluig_process_card_value` — os campos gravados batem com o preenchido
     (quando o cenário depender do valor, ex.: flag que decide gateway).
   Sem MCP disponível, conferir pelo histórico da interface e capturá-lo.
9. **Capturar o histórico** da passagem.

Etapas automáticas (service task, gateway, timer) não têm tela: comprová-las
pelo histórico e pelo efeito da integração (seção 2.1).

Retorno à mesma atividade incrementa a ocorrência: nova observação, novas
capturas. Depois de sessão expirada, intervenção do usuário ou envio incerto,
reler o estado persistido antes da próxima ação.

Cancelamento pela plataforma: capturar o formulário, o diálogo com o motivo
preenchido e o estado final. O motivo do cancelamento é um campo próprio, com
texto próprio. Não afirmar que o processo passou por um nó "Cancelado" do
diagrama se o histórico só mostra a última atividade humana.

### 2.1 Efeito das integrações

Para cada service task ou evento com integração, o relatório diz o que era
esperado, o que o histórico mostra e **o que foi gravado no sistema externo**.

- Conferir o efeito externo somente com consulta de leitura indicada no
  contexto do cliente (ex.: SELECT no banco de teste do ERP, dataset de
  consulta, endpoint GET). Nunca criar, alterar ou estornar registro externo
  para limpar o teste.
- Sem meio de leitura disponível, registrar o efeito como **não verificado**,
  não como aprovado.
- Registros de teste criados no sistema externo são listados no relatório
  (tabela, chave) para o usuário decidir a limpeza.

## 3. Evidências

### 3.1 Captura

- **Formulário inteiro.** Voltar a rolagem ao topo antes de capturar, cobrir
  contêineres com rolagem interna e iframes, afastar botões flutuantes do
  conteúdo. Se uma imagem não couber, salvar partes numeradas e sobrepostas
  (`-p1`, `-p2`...) do cabeçalho à última seção.
- **Conferir o PNG salvo**, não só o DOM: número da solicitação legível,
  primeira e última seção presentes, decisão e observação visíveis, tela já
  carregada, nada cortado ou duplicado.
- **Diagrama real** (modo completo): Informações → Visualizar diagrama, esperar
  renderizar, enquadrar raias e destaque da atividade atual. Não desenhar
  diagrama substituto.
- Captura inválida é mantida e marcada como inválida; a recaptura ganha nome
  novo. Nunca renomear imagem de outra etapa para cobrir lacuna. Se a captura
  integral for impossível, registrar **evidência parcial** antes de avançar.

### 3.2 Dados sensíveis

Prints de processo costumam ter dados pessoais (nome, CPF, RA, valores). Por
isso:

- o destino padrão é **fora do repositório** (o contexto do cliente define o
  caminho); se for dentro, a pasta precisa estar no `.gitignore` — conferir
  antes de gravar;
- o `relatorio.md` e o `resultado.json` citam a solicitação pelo número e **não
  repetem** dados pessoais do formulário; quando um valor for necessário para
  provar a regra, mascarar (`***.456.789-**`);
- arquivos técnicos gerados pelo navegador fora da pasta da execução (traces,
  downloads, perfis) são informados ao usuário com o caminho, para ele decidir;
  não apagar em silêncio.

### 3.3 Estrutura

```text
<destino>/<ambiente>/<processo>/<AAAA-MM-DD_HHmm>/
├── resultado.json
├── relatorio.md
└── screenshots/
    └── <cenario>/
        └── <solicitacao>_<nn-atividade>_oc<n>_<momento>.png
```

`momento`: `chegada`, `preenchido`, `negativo-<regra>`, `historico`,
`diagrama`, `cancelamento-dialogo`, `final`. Cada execução tem pasta própria;
nunca sobrescrever execução anterior.

## 4. Resultado

### 4.1 Classificação

Cada caso recebe **resultado funcional** e **completude da evidência**:

| Resultado funcional | Significado |
|---|---|
| aprovado | comportamento igual ao gabarito, confirmado no estado persistido |
| reprovado | divergência do gabarito (descrever esperado × observado) |
| bloqueado | não foi possível executar (motivo e o que falta) |
| não executado | fora do escopo aprovado ou interrompido pelo usuário |
| não aplicável | cenário não existe nesta versão do processo |

| Evidência | Significado |
|---|---|
| completa | todas as capturas do modo escolhido, conferidas |
| parcial | alguma captura faltando ou cortada (dizer qual) |
| ausente | resultado baseado só em histórico/servidor |

### 4.2 `resultado.json`

Registro canônico. Estrutura mínima:

```json
{
  "execucao": "2026-09-25_1430",
  "ambiente": { "nome": "hml", "host": "", "versaoFluig": "" },
  "processo": { "id": "", "versao": 0 },
  "executor": { "agente": "Claude Code", "navegador": "", "modo": "completo" },
  "escopoAutorizado": { "texto": "", "em": "" },
  "cenarios": [
    {
      "id": "caminho-feliz",
      "solicitacao": 0,
      "esperado": { "final": "", "fonte": "" },
      "observado": { "final": "", "statusPersistido": "" },
      "resultado": "aprovado",
      "evidencia": "completa",
      "etapas": [
        {
          "atividade": "", "estado": 0, "ocorrencia": 1,
          "responsavel": "", "decisao": "", "observacao": "",
          "negativos": [{ "regra": "", "mensagem": "", "avancou": false }],
          "confirmacaoServidor": { "historico": true, "estadoAtivo": true },
          "capturas": ["screenshots/caminho-feliz/..."]
        }
      ],
      "integracoes": [
        { "etapa": "", "sistema": "", "esperado": "", "verificado": "sim|nao|nao-verificavel", "registro": "" }
      ]
    }
  ],
  "divergencias": [{ "entre": "gabarito x publicado", "descricao": "" }],
  "lacunas": [],
  "registrosExternosCriados": [],
  "limites": []
}
```

### 4.3 `relatorio.md`

Mesmo conteúdo do JSON, legível, com links relativos para os prints:

1. **Resumo** — processo, versão, ambiente, data, placar por resultado.
2. **Tabela de cenários** — cenário, solicitação, esperado, observado,
   resultado, evidência.
3. **Detalhe por cenário** — etapas, decisões, negativos, links dos prints.
4. **Integrações** — efeito esperado × verificado, registros criados.
5. **Divergências e achados** — gabarito × código × publicado × observado.
6. **Lacunas e limites** — o que não foi comprovado e por quê.
7. **Evidência para GMUD** — bloco curto, pronto para colar na seção de testes
   da GMUD: ambiente, data, cenários executados com resultado e caminho da
   pasta de evidências.

Antes de entregar: conferir que todo arquivo citado existe, que todas as
atividades humanas percorridas têm captura (ou lacuna declarada) e que não há
senha, token ou dado pessoal sem máscara.

### 4.4 Limites que sempre constam

- versão do Fluig e navegador em que o teste rodou (teste em 2.0 não comprova
  1.8.x);
- logs do servidor e recebimento/conteúdo de e-mail não são conferidos pela
  skill — se o gabarito exigir, marcar como dependência de conferência humana;
- integração verificada só no que foi observável.

## Integração com outras skills

- **`fluig-validacao`** — lista das regras de `beforeSendValidate` para montar
  os cenários negativos.
- **`fluig-orquestracao`** — se o teste revelar defeito e o usuário pedir a
  correção, a correção é outra tarefa, classificada por essa skill. Esta skill
  só testa.
- **Skill de GMUD do cliente**, se existir — usa o bloco "Evidência para GMUD".
