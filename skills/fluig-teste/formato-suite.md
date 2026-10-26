# Formato da suíte de testes Fluig (`testes/<processo>.json`)

Uma suíte por processo, versionada no projeto do cliente, em `testes/<processo>.json`.

```jsonc
{
  "processo": "reembolso - Solicitação de Reembolso",   // processId exato no servidor
  "versao": 3,                                           // versão levantada (informativo)
  "descricao": "...",
  "servidor": { "nome": "meu-servidor-hml", "env": ".fluigcli/hml.env" },
  //   nome: o "server" que o fluigcli responde; o script ABORTA se for outro
  //   env:  arquivo com FLUIG_HOST / FLUIGCLI_SERVER / credencial (relativo à raiz do projeto)
  "datasetFormulario": "Reembolso",   // datasetName do formulário (para conferir campos gravados)
  "camposBase": { "campo": "valor", "filho___1": "valor" },  // campos comuns a todos os cenários
  "anexos": ["testes/anexos/documento-teste.pdf"],           // opcional: anexados no início (também por cenário)

  "tela": {                           // CAMADA 3 — caminho feliz pela tela (roteiro: camada3-tela.md)
    "descricao": "prestador já cadastrado, aprovado, até a conclusão",
    "passos": [                        // o que preencher/conferir em cada etapa, para a sessão principal seguir
      { "etapa": 0, "preencher": "primeirasol=Não; Empresa=ASCENDRA (zoom); ...", "conferir": "cabeçalho preenchido; data do pagamento 10/25" },
      { "etapa": 4, "enviarVazio": "cobra só Deliberação", "preencher": "Aprovado", "conferir": "Cadastro do prestador riscada" },
      { "etapa": 21, "anexo": true }
    ],
    "fim": 18
  },

  "cenarios": [                        // CAMADA 1 — fluxo pela API (cria solicitações!)
    {
      "id": "caminho-feliz",
      "descricao": "...",
      "campos": { },                   // sobrepõe camposBase no início
      "inicio": { "esperado": { "etapa": 5 } },
      "passos": [
        {
          "etapa": 5,                  // onde a solicitação deve estar antes do passo
          "destino": 65,               // --target-state (saída escolhida pelo usuário); omitir = fluxo do diagrama
          "campos": { "ObsGestorSol": "..." },
          "esperado": { "etapa": 26 }  // e/ou "status": "OPEN" | "FINALIZED" | "CANCELED"
          // "anexos": ["testes/anexos/x.pdf"] → atividade que exige anexo nela mesma: o passo vai pelo
          //   SOAP saveAndSendTask (anexa e envia; destino = "destino" ou a única saída da etapa).
          //   Precisa de FLUIG_HOST, FLUIG_USER e FLUIGCLI_PASSWORD no .env da suíte.
          // "aguardar": 90 → consulta a cada 3 s até etapa/status baterem (tarefa de serviço em segundo plano)
        }
      ],
      "verificar": {
        "caminho": [4, 5, 26, 46, 37], // subsequência em ordem das etapas percorridas
        "naoPassaPor": [14, 52],
        "historico": [{ "etapa": 5, "contem": "APROVADO" }, { "contem": "classificada", "vezes": 1 }],  // texto sem HTML; "vezes" exige a contagem exata
        "campos": { "validado": "validadoSIM" }               // valor gravado no card
      }
    }
  ],

  "formulario": {                      // CAMADA 2 — tela em headless (não toca o servidor)
    "pasta": "forms/Reembolso",
    "html": "Reembolso.html",
    "emailUsuario": "...",             // WCMAPI.userEmail simulado
    "datasets": { "ds_x": [ { "COL": "v" } ] },   // respostas de DatasetFactory (padrão: vazio)
    "globais": { "currentUser": "joao", "tarefaatual": "$atividade" },  // opcional: variáveis que o displayFields injeta
    //   "$atividade" vira o número da atividade de cada caso; um caso pode ter "globais" próprias (sobrepõem)
    //   (o simulador já define currentTask, modForm, formMode = modForm e currentUser = 'teste')
    "casos": [
      {
        "id": "gestor-obs-reprovar",
        "atividade": 5,                // currentTask simulado
        "modo": "MOD",                 // modForm (ADD/MOD/VIEW)
        "valores": { "#campo": "valor" },   // preenchidos antes do document.ready
        "marcar": ["#radioOuCheckbox"],
        "esperado": {
          "card": "Aprovação do gestor",                    // título do card da ajuda
          "etapas": { "Aprovação do gestor": "atual" },     // feita|atual|pendente|pulada|reprovada
          "paineisVisiveis": ["#formGestorSol"],
          "paineisOcultos": ["#formValidarReembolso"],
          "somenteLeitura": { "#ObsGestorSol": false },
          "visiveis": ["#div_x"], "ocultos": ["#div_y"]
        },
        "envios": [                    // beforeSendValidate(de, para)
          { "de": 5, "para": 12, "espera": "erro", "contem": ["Observação"] },
          { "de": 5, "para": 65, "antes": { "#ObsGestorSol": "ok" }, "naoContem": ["Observação"] }
          // "espera": "ok" exige nenhuma mensagem; sem "espera", só contem/naoContem são conferidos
        ]
      }
    ]
  }
}
```

## Regras para escrever cenários

- Atividades, gateways e condições vêm do **servidor** (`processState`, `LINK_PROCES`,
  `ESTADO_PROCES_COND`), nunca de suposição. Aprovação sem gateway (o usuário escolhe a saída no
  envio) usa `destino`; gateway com condição decide sozinho pelos `campos`.
- Um cenário por final diferente: caminho feliz, cada reprovação, cada desvio por valor/flag,
  cada devolução.
- Na camada 1 os eventos do formulário não rodam (`displayFields`, `validateForm`,
  `beforeSendValidate`): os `campos` precisam trazer tudo o que os gateways e scripts leem.
  Validação de tela é a camada 2.
- Na camada 2, campos que vêm de zoom/autocomplete não existem no headless: use `contem` /
  `naoContem` para a regra testada, em vez de `"espera": "ok"`, quando houver outros obrigatórios.
- Tarefa de serviço roda em segundo plano (o `request move` volta antes dela terminar): no passo
  que entra nela, use `"aguardar": <segundos>` no `esperado` (também vale em `inicio.esperado`).
- **Gateway paralelo**: um passo por tarefa aberta, na ordem em que o teste quer concluí-las, cada um
  com a `etapa` da sua tarefa; até a junção o `esperado` é `{"status": "OPEN"}` (as outras tarefas
  continuam abertas), e o passo que fecha o último ramo espera a etapa seguinte à junção. O script
  escolhe a tarefa aberta pela `etapa`, lê o ramo em `HISTOR_PROCES.NUM_SEQ_THREAD` (`task assume
  --thread`, `threadSequence` do SOAP) e passa `--movement` ao `request move`. Exemplo:
  ```jsonc
  { "etapa": 95, "destino": 41, "esperado": { "status": "OPEN" } },   // abre 15 e 44
  { "etapa": 15, "esperado": { "status": "OPEN" } },
  { "etapa": 44, "esperado": { "etapa": 64 } }                         // junção → 64
  ```
  Com várias tarefas abertas, `etapa` no `esperado` confere se aquela etapa está entre as abertas.
- Comentários e observações dos testes levam a marca `[TESTE <execucao>]` (o script põe sozinho).
