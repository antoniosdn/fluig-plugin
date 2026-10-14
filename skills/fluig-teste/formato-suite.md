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
- Comentários e observações dos testes levam a marca `[TESTE <execucao>]` (o script põe sozinho).
