# Formato da spec v1 do fluxo

Referência da `spec` que `fluig_flow_validate`, `fluig_flow_generate` e `fluig_flow_deploy` recebem.
Fonte: `src/flow/spec.js` e `src/flow/validar.js` do mcp-fluig. Chave fora do formato dá
`E_CAMPO_DESCONHECIDO` em qualquer nível.

## 1. Raiz

| Campo | Obrigatório | Tipo | Regra |
|---|---|---|---|
| `processId` | sim | texto | sem espaço (`E_PROCESSID`); fora de `[A-Za-z0-9_]` dá `W_PROCESSID_CARACTERES`; a geração só aceita letras, dígitos, `_`, `-` e `.` (`E_PROCESS_ID`) |
| `descricao` | não | texto | vira a descrição do processo no servidor (vale para todas as versões) |
| `formId` | não* | inteiro > 0 | formulário vinculado. *Sem ele as condições não são conferidas e o deploy recusa (`W_SEM_FORMULARIO`) |
| `atividades` | sim | lista não vazia | ver §2 |
| `ligacoes` | sim | lista | ver §3 |

`versaoAlvo` **não** fica na spec: é parâmetro da ferramenta (`1.8.2` ou `2.0`).

## 2. Atividade

Chaves, nesta ordem: `id`, `tipo`, `nome` (obrigatórias, texto), `responsavel`, `execucao`, `tratamentoErro`, `posicao`.

| `tipo` | Número do Fluig (bpmnType) |
|---|---|
| `inicio` | 10 |
| `humana` | 80 |
| `servico` | 82 |
| `gateway_exclusivo` | 120 |
| `gateway_paralelo_abertura` | 126 |
| `gateway_paralelo_juncao` | 127 |
| `fim` | 60 |
| `cancelamento` | 65 |
| `fim_terminativo` | 68 |

Reconhecidos e recusados (`E_TIPO_FORA_V1`): `espera`, `subprocesso`, `captura_erro`, `mensagem`, `sinal`.

- `responsavel` (só em `humana`): `{ "tipo": "papel" | "pool_papel", "valor": "<roleId>" }`.
  `pool_papel` vai para a fila do papel e alguém assume; `papel` é o comportamento usual do Fluig
  (quem envia escolhe entre os usuários do papel). Sem `responsavel`: `W_HUMANA_SEM_RESPONSAVEL`.
- `execucao` (só em `servico`, e obrigatória nele): `automatizada` (executionType 1) ou `imediata` (2).
- `tratamentoErro` (só em `servico` automatizada, e obrigatório nela): id de uma atividade `humana`
  (não o próprio serviço). O gerador cria a captura de erro; a ligação captura → tratamento **não** entra em `ligacoes`.
- `posicao`: `{ "x": número, "y": número }`. Sem ela, layout automático (da esquerda para a direita).
  Posição em parte das atividades gera aviso.

Atividade `cancelamento` e `fim_terminativo` encerram a solicitação inteira (podem sair de dentro de um ramo paralelo).

## 3. Ligação

| Campo | Tipo | Regra |
|---|---|---|
| `de`, `para` | texto, obrigatórios | ids de atividades |
| `ordem` | inteiro >= 1 | só em saída de `gateway_exclusivo` |
| `condicao` | objeto | só em saída de `gateway_exclusivo` (§4) |
| `retorno` | boolean | "permitir retorno" do Fluig; nunca em ligação que entra numa junção paralela (`E_RETORNO_JUNCAO`) |
| `padrao` | boolean | saída padrão do gateway exclusivo; pode vir sem `condicao` e sem `ordem` |

Gateway exclusivo: pelo menos 2 saídas; cada uma com `condicao` + `ordem` (salvo a padrão); ordens
distintas; no máximo um destino padrão.

## 4. Condição

Exatamente uma forma:

- `{ "regras": [ ... ] }` (preferida; conferida contra o formulário), ou
- `{ "js": "..." }` (`W_CONDICAO_JS`; não conferida).

`condicao.nome` **não usar**: existe no validador só para 2.0, mas a geração do `.process` recusa
(`E_PROCESS_CONDICAO_NOME`).

Regra: `{ "campo": "...", "op": "...", "valor": "...", "valorTipo": "fixo" | "campo" }`.

| Operador (10) | Código | Valor |
|---|---|---|
| `vazio` | 0 | não leva |
| `igual` | 1 | exige |
| `diferente` | 2 | exige |
| `maior` | 3 | exige (`W_OPERADOR_COMPARACAO`) |
| `maior_igual` | 4 | exige (`W_OPERADOR_COMPARACAO`) |
| `menor` | 5 | exige (`W_OPERADOR_COMPARACAO`) |
| `menor_igual` | 6 | exige (`W_OPERADOR_COMPARACAO`) |
| `contem` | 7 | exige |
| `nao_contem` | 8 | exige |
| `preenchido` | 9 | não leva |

`valor` é texto ou número e é o **valor gravado** no campo (value do select/radio), não o rótulo da tela.
`valorTipo`: `fixo` (padrão) ou `campo` (o valor é o nome de outro campo do formulário).
Regras da mesma condição combinam por **E**. **OU** = várias ligações do mesmo gateway para o mesmo
destino, cada uma com a sua `ordem` (exemplo `ou.json`).

## 5. Regras de grafo (resumo do validador)

- Um `inicio`; pelo menos um fim (`fim`, `cancelamento`, `fim_terminativo`); nada chega ao início; fim não tem saída.
- Toda atividade tem saída (salvo fins), é alcançável e chega a um fim.
- Sem ligação repetida (fora de gateway exclusivo) nem laço para si mesma.
- Abertura paralela: 2+ saídas, convergindo para uma única junção. Junção: 2+ entradas e 1 saída.
- Serviço automatizado: uma única saída.

## 6. Exemplos (pasta `exemplos/`)

### 6.1 `aprovacao-simples.json`

Compra com aprovação: início, aprovar (pool_papel), gateway (regra `decisaoGestor igual aprovado`;
padrão para o fim "reprovada"), efetuar compra (papel), fim.

```json
{
  "processId": "exemploAprovacao",
  "descricao": "Solicitação de compra com aprovação do gestor",
  "formId": 1001,
  "atividades": [
    { "id": "ini", "tipo": "inicio", "nome": "Solicitar compra" },
    { "id": "apr", "tipo": "humana", "nome": "Aprovar compra", "responsavel": { "tipo": "pool_papel", "valor": "gestorCompras" } },
    { "id": "gw", "tipo": "gateway_exclusivo", "nome": "Aprovado?" },
    { "id": "comp", "tipo": "humana", "nome": "Efetuar compra", "responsavel": { "tipo": "papel", "valor": "compras" } },
    { "id": "fim", "tipo": "fim", "nome": "Compra concluída" },
    { "id": "rep", "tipo": "fim", "nome": "Compra reprovada" }
  ],
  "ligacoes": [
    { "de": "ini", "para": "apr" },
    { "de": "apr", "para": "gw" },
    { "de": "gw", "para": "comp", "ordem": 1, "condicao": { "regras": [ { "campo": "decisaoGestor", "op": "igual", "valor": "aprovado" } ] } },
    { "de": "gw", "para": "rep", "padrao": true },
    { "de": "comp", "para": "fim" }
  ]
}
```

### 6.2 `completo.json`

Todos os tipos da v1, exceto `fim_terminativo`, com `posicao`. Trechos que ensinam:

Serviço automatizado com tratamento de erro (a ligação `trata` para `erp` devolve ao serviço):

```json
{ "id": "erp", "tipo": "servico", "nome": "Integrar ERP", "execucao": "automatizada", "tratamentoErro": "trata" },
{ "id": "trata", "tipo": "humana", "nome": "Tratar erro da integração", "responsavel": { "tipo": "pool_papel", "valor": "admin" } }
...
{ "de": "erp", "para": "gw" },
{ "de": "trata", "para": "erp" }
```

Gateway exclusivo com duas regras (E) e saída padrão em `js`:

```json
{ "de": "gw", "para": "abre", "ordem": 1, "condicao": { "regras": [
  { "campo": "valor", "op": "maior", "valor": "100" },
  { "campo": "aprovado", "op": "igual", "valor": "sim" } ] } },
{ "de": "gw", "para": "canc", "ordem": 2, "condicao": { "js": "true" }, "padrao": true }
```

Paralelo: `abre` (abertura) com saídas para `ges` e `fin`, ambos para `junta` (junção), depois serviço
imediato `avisa` e `fim`.

### 6.3 `ou.json`

O mesmo fluxo com uma segunda ligação `gw` para `abre` (OU):

```json
{ "de": "gw", "para": "abre", "ordem": 3, "condicao": { "regras": [ { "campo": "urgente", "op": "igual", "valor": "sim" } ] } }
```
