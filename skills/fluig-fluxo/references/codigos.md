# Códigos de erro, aviso e recusa das ferramentas `fluig_flow_*`

Como ler:

1. `fluig_flow_validate` e `fluig_flow_generate` devolvem `erros[]` e `avisos[]` com `codigo`, `mensagem`
   e `caminho` (ex.: `ligacoes[3].condicao.regras[0].campo`).
2. **Falhas lançadas** (erros de geração e travas do deploy) chegam como texto `ERRO: <mensagem>`
   **sem o código**. Identifique pela mensagem (coluna "trecho").
3. `fluig_flow_deploy` também devolve `{ publicado: false, motivo, ... }` sem lançar.

Nunca corrija em silêncio: mostre o código, a mensagem e a correção proposta ao usuário.

## 1. Validador: erros

| Código | O que fazer |
|---|---|
| `E_VERSAO_ALVO` | `versaoAlvo` só `1.8.2` ou `2.0`; perguntar a versão de produção |
| `E_SPEC_INVALIDA` | refazer a spec como objeto JSON |
| `E_CAMPO_DESCONHECIDO` | chave fora da v1: erro de digitação, corrigir; recurso (prazo, raia, grupo...), explicar o limite (SKILL, seção de limites) |
| `E_CAMPO_OBRIGATORIO` | preencher o campo do `caminho` |
| `E_TIPO_CAMPO` | corrigir o tipo (texto, inteiro > 0, boolean, objeto, lista, número) |
| `E_PROCESSID` | tirar o espaço do `processId` |
| `E_ID_DUPLICADO` | renomear um dos ids |
| `E_TIPO_FORA_V1` | `captura_erro`: usar `tratamentoErro`; demais (`espera`, `subprocesso`, `mensagem`, `sinal`): limite da v1 |
| `E_TIPO_ATIVIDADE` | usar um dos 9 tipos |
| `E_RESPONSAVEL_FORA_HUMANA` | tirar `responsavel` da atividade |
| `E_RESPONSAVEL_TIPO` | só `papel` ou `pool_papel`; perguntar se serve um papel ou se ajusta no VS Code depois |
| `E_EXECUCAO` | perguntar `automatizada` ou `imediata` |
| `E_EXECUCAO_FORA_SERVICO` | tirar `execucao` |
| `E_TRATAMENTO_AUSENTE` | perguntar quem trata o erro; criar a atividade humana e a saída dela |
| `E_TRATAMENTO_FORA_AUTOMATIZADO` | tirar `tratamentoErro` (serviço imediato não tem captura) |
| `E_TRATAMENTO_ID` | apontar para uma atividade existente |
| `E_TRATAMENTO_TIPO` | o tratamento precisa ser `humana` e não o próprio serviço |
| `E_LIGACAO_ID` | corrigir `de`/`para` |
| `E_LIGACAO_LACO` | remover a ligação para si mesma |
| `E_CONDICAO_FORMA` | exatamente `regras` (não vazia) ou `js` (não vazio) |
| `E_VERSAO_RECURSO` | tirar `condicao.nome` (não usar `nome` em nenhuma versão: `E_PROCESS_CONDICAO_NOME`) |
| `E_OPERADOR` | usar um dos 10 operadores |
| `E_VALOR_TIPO` | `fixo` ou `campo`; com `campo`, `valor` é texto (nome do campo) |
| `E_REGRA_VALOR_PROIBIDO` | tirar `valor` de `vazio`/`preenchido` |
| `E_REGRA_VALOR_AUSENTE` | perguntar o valor |
| `E_INICIO_QTD` | exatamente um `inicio` |
| `E_FIM_AUSENTE` | acrescentar um fim (perguntar qual final) |
| `E_INICIO_ENTRADA` | nada volta ao início; "devolver ao solicitante": ver SKILL, seção de perguntas |
| `E_FIM_SAIDA` | tirar a saída do fim |
| `E_SEM_SAIDA` | perguntar para onde a atividade segue (inclusive a de tratamento de erro) |
| `E_INALCANCAVEL` | ligar a atividade ao fluxo ou removê-la (perguntar) |
| `E_SEM_CAMINHO_FIM` | laço sem saída: perguntar a saída |
| `E_RETORNO_JUNCAO` | tirar `retorno` da ligação que entra na junção paralela |
| `E_LIGACAO_DUPLICADA` | remover a repetida |
| `E_CONDICAO_FORA_GATEWAY` | condição/ordem só em saída de gateway exclusivo; decisão do executor = humana com 2+ saídas sem condição |
| `E_PADRAO_FORA_GATEWAY` | tirar `padrao` |
| `E_GATEWAY_SAIDAS` | gateway exclusivo com 2+ saídas |
| `E_GATEWAY_SEM_CONDICAO` | dar `condicao` + `ordem` (ou marcar a padrão) |
| `E_GATEWAY_ORDEM_REPETIDA` | ordens distintas |
| `E_PADRAO_REPETIDO` | um só destino padrão |
| `E_SERVICO_AUTO_SAIDAS` | uma saída; decisão depois do serviço: gateway exclusivo |
| `E_PARALELO_ABERTURA` | abertura paralela com 2+ saídas |
| `E_PARALELO_JUNCAO` | junção com 2+ entradas e 1 saída |
| `E_PARALELO_SEM_JUNCAO` | todo ramo precisa convergir para a mesma junção (o motivo vem no texto) |
| `E_JUNCAO_SEM_ABERTURA` | ligar a junção a uma abertura ou trocar por atividade comum |
| `E_PAPEL_INEXISTENTE` | o papel não existe no servidor de teste: mostrar a lista e perguntar; não criar papel |
| `E_CAMPO_INEXISTENTE` | o campo não existe no formulário (a mensagem sugere maiúsculas/minúsculas): conferir com `fluig_form_fields` e perguntar |

## 2. Validador: avisos

| Código | O que fazer |
|---|---|
| `W_PROCESSID_CARACTERES` | preferir `[A-Za-z0-9_]` |
| `W_CONDICAO_JS` | mostrar o JS ao usuário; preferir regras |
| `W_OPERADOR_COMPARACAO` | avisar que a comparação texto x número não está confirmada; campo com máscara de moeda não compara como número; testar o caminho (`fluig-teste`) |
| `W_SERVICO_AUTOMATIZADO` | informativo: captura criada e script vazio; o script é com `fluig-workflow` |
| `W_HUMANA_SEM_RESPONSAVEL` | confirmar com o usuário ou definir papel |
| `W_SEM_LOOKUP` | papéis/campos não conferidos (CLI sem servidor); publicar exige conferir |
| `W_LOOKUP_FALHOU` | o servidor não respondeu à conferência: `fluig_version` e repetir; o deploy recusa enquanto houver |
| `W_SEM_FORMULARIO` | há regras sem `formId`: perguntar o formulário; o deploy recusa |

## 3. Ferramentas (`ferramentas.js`)

| Código / recusa | Onde | O que fazer |
|---|---|---|
| `E_VERSAO_SERVIDOR` | validate (erro) | `versaoAlvo` maior que o servidor: usar a versão menor |
| `W_VERSAO_SERVIDOR` | validate, generate | versão do servidor não lida, ou (generate) alvo maior: resolver antes de publicar; o deploy recusa |
| `W_MODELO_IGNORADO` / `W_ORIGEM_IGNORADA` | generate | não passar `modeloProcessId`/`origem` |
| `W_DEFINICAO_HERDADA` | deploy (só com `spec` e `novo: false`) | informativo: categoria, volume, expediente, instrução (em 2.0, também categoria 2.0 e ícone) vieram do servidor. Com `processo` não sai: a definição vem do `.process` (do servidor só categoria 2.0 e ícone) e instrução vazia no `.process` apaga a do servidor; ler antes com `fluig_process_export_xml` |
| `E_CATEGORIA_TROCADA` | deploy (`publicado: false`) | seguir a dica da mensagem. Com `spec`: conversor oficial, ou ajustar `category` no `.process`. Com `processo`: ajustar a categoria no `.process` (VS Code) para a do servidor e regenerar |
| `W_VERSAO_EM_EDICAO` | deploy (`publicado: false`, `versaoEmEdicao: true`) | ler `errosServidor`/`errosPorTipo`, corrigir, publicar de novo com `novo: false` |
| `motivo` "processo não encontrado no servidor para herdar a definição..." | deploy | o processo não existe: `novo: true` (confirmar com o usuário) |
| `motivo` "spec com erro" | deploy | voltar ao validate |
| `motivo` "papel ou campo não conferido no servidor" | deploy | resolver `W_LOOKUP_FALHOU`, `W_SEM_LOOKUP`, `W_SEM_FORMULARIO`, `E_PAPEL_INEXISTENTE`, `E_CAMPO_INEXISTENTE` |
| `motivo` "categoria do processo no servidor não conferida" | deploy (processo) | o export do processo falhou: conferir `processId` e a conexão |
| `motivo` "a publicação trocaria a categoria do processo" | deploy | ver `E_CATEGORIA_TROCADA` |
| `motivo` "liberação recusada pelo servidor" | deploy | ver `W_VERSAO_EM_EDICAO`. Recusas já vistas: "A atividade de serviço N - X não possui script" (resolvida pelo script vazio) e "Atividade Join N - X não pode possuir fluxos de entrada que permitam retorno" (`E_RETORNO_JUNCAO`) |
| ERRO "não publica em produção" | deploy | usar `env: "teste"` |
| ERRO "exige confirm=true" | deploy | só depois da autorização do usuário |
| ERRO "Informe novo=true ... ou novo=false" | deploy | conferir se o processo já existe (`fluig_process_versions`) |
| ERRO "Informe exatamente uma entrada: spec ... ou processo" | deploy | passar um dos dois |
| ERRO "Versão do servidor não conferida; publicação recusada" | deploy | conexão/servidor (`fluig_version`) |
| ERRO "versaoAlvo X é maior que a versão do servidor" | deploy | `versaoAlvo` menor |
| ERRO "a ferramenta ... exige o parâmetro env" | todas | passar `env: "teste"` |
| "Ferramenta desconhecida ... FLUIG_READONLY" | deploy | o servidor MCP está em somente leitura: pedir ao usuário |

## 4. Geração e regeneração (lançados como `ERRO: <mensagem>`)

Fontes: `artefatos.js`, `spec-process.js`, `regenerar.js`, `conversor.js`, `java.js`, `zip.js`, `cli-fluxo.js`.

| Código | Trecho da mensagem | O que fazer |
|---|---|---|
| `E_VERSAO` | "versaoAlvo ... inválida" / "Conversor ... inválido" | versão `1.8.2` ou `2.0`; conversor `auto`, `oficial` ou `proprio` |
| `E_PROCESS_ID` | "não serve como nome de arquivo" | `processId` com letras, dígitos, `_`, `-` e `.` |
| `E_PROJETO` | "projeto precisa ser um caminho absoluto" / "A pasta do projeto não existe" | caminho absoluto de pasta existente |
| `E_PROCESS_EXISTE` | "já existe e é diferente do gerado. Nada foi gravado" | perguntar: `sobrescrever: true` (com backup) ou editar o `.process` e usar `fluig_flow_regenerate` |
| `E_PROCESS_CONDICAO_NOME` | "o .process não guarda o nome da condição" | tirar `condicao.nome` |
| `E_PROCESS_VENDOR`, `E_PROCESS_ASCII`, `E_PROCESS_POS`, `E_PROCESS_CONFIG`, `E_PROCESS_DIVERGENTE` | "validação do vendor" / "pendência no editor" / "difere da spec" | defeito do gerador com spec válida: parar, mostrar a mensagem ao usuário e relatar (não contornar) |
| `E_CAMINHO` | "precisa estar em <projeto>/workflow/diagrams/" / "Arquivo não encontrado" | corrigir o caminho do `.process` |
| `E_PROCESS_INVALIDO` | "não é um .process suportado" | precisa ser arquivo do Studio/Fluiggers 3.0.1 |
| `E_PRECONDICAO` | "exatamente um fluxo de saida em cada atividade manual" | atividade manual (tipo 85, criada no VS Code) com uma única saída |
| `E_CONVERSOR_AUSENTE` | "Conversor do Studio ... não instalado" | instalar (pré-requisito 4 da SKILL) ou `conversor: "auto"` com aviso ao usuário |
| `E_CONVERSOR_CACHE` | "Rode de novo: fluig-mcp instalar-conversor" | cache corrompido: reinstalar |
| `E_CONVERSOR_FALHOU`, `E_ECM30_INVALIDO`, `E_PONTE` | "O conversor do Studio falhou" / "terminou sem gravar" / erro da ponte | conferir Java e `.process`; `conversor: "proprio"` só com o usuário ciente |
| `E_SVG_INVALIDO` | "não devolveu um SVG válido" | conferir o `.process` |
| `E_PLANO_B_RECUSADO` | "O gerador próprio recusa este processo" | instalar o conversor oficial |
| `E_JAVA_AUSENTE`, `E_JAVA_VERSAO` | "Java 8 ou superior" | instalar Java ou definir `JAVA_HOME`/`FLUIG_MCP_JAVA` |
| `E_FONTE`, `E_ZIP`, `E_HASH`, `E_BAIXAR` | falhas do `instalar-conversor` | seguir a mensagem; `E_HASH` = arquivo recusado, nada gravado |
| `E_SPEC` | CLI `gerar`: "Não foi possível ler a spec" | `spec.json` ilegível |

Avisos de geração:

| Código | O que fazer |
|---|---|
| `W_SCRIPT_SERVICO_VAZIO` | script vazio de serviço criado; a integração é escrita depois (`fluig-workflow`) |
| `W_ECM30_NAO_OFICIAL` | plano B usado; conferir antes de publicar e preferir instalar o conversor |
| `W_STUDIO_SUBSTITUTO` | o Studio 2.0.0.2 foi usado para 1.8.2 |
| `W_CONVERSOR` | aviso do conversor oficial: repassar ao usuário |
| `W_PROCESS_POS`, `W_PROCESS_POS_AVISO` | validação da extensão no `.process`: mostrar e corrigir no VS Code |
| `W_GERADOR_POSICAO_PARCIAL`, `W_GERADOR_POSICAO_ARREDONDADA` | posição incompleta ou arredondada |
| `W_PLANO_B_PERDA`, `W_PLANO_B_LITERAIS` | o que o plano B não leva |

Do plano B (`gerar.js`; aparecem só junto de `W_ECM30_NAO_OFICIAL`):

| Código | O que fazer |
|---|---|
| `W_GERADOR_SEM_MODELO` | categoria vazia; no deploy com `spec` e `novo: false` a herança do servidor corrige; com `processo` a categoria vem do `.process` |
| `W_GERADOR_SEM_FORMULARIO` | a spec não tem `formId`; o processo sai sem formulário vinculado |
| `W_GERADOR_SERVICO_SEM_SCRIPT` | o serviço sai sem o script `servicetaskN`; escrever no editor ou publicar à parte |
| `W_GERADOR_RETORNO_OU` | OU com retorno divergente: o link único fica com retorno |
| `W_GERADOR_ORIGEM_ID`, `W_GERADOR_ORIGEM_OU` | entradas de `origem` que não casam com a spec; ignoradas (não passar `origem`) |
| `W_GERADOR_SEM_DESENHO` | filtrado no generate/deploy porque o SVG vai junto; pode aparecer no `fluig_flow_regenerate` com plano B |
| `E_GERADOR_CARACTERE` | caractere de controle num texto: remover |
| `E_GERADOR_ORIGEM`, `E_EVENTO_ID`, `E_MODELO` | erros internos; vêm embutidos no `E_PLANO_B_RECUSADO` |

## 5. Leitura (`fluig_flow_read` e deploy com `processo`)

`ignorados` (`I_*`) é o que a spec v1 não carrega; **gerar de novo pela spec perde isso**.

| Código | Significado |
|---|---|
| `I_ATIVIDADE_CAMPOS` | campos da atividade que a spec não guarda |
| `I_PROCESSO_CAMPOS` | campos do processo que a spec não guarda |
| `I_LIGACAO_CAMPOS` | campos da ligação que a spec não guarda |
| `I_SERVICO_CONFIG` | configuração do serviço fora da v1 |
| `I_SCRIPTS` | scripts de evento do processo ignorados (não vão na spec) |
| `I_RAIAS` | raias (SwimLane) ignoradas |
| `I_DESENHO` | elementos de desenho ignorados |
| `I_DIAGRAMA` | `processDiagram` não guardado |
| `I_ELEMENTO` | elemento do diagrama sem equivalente na v1 |
| `I_CONDICAO_ATRIBUICAO` | a condição tem atribuição, que a v1 não guarda |
| `I_ATRIBUICAO_NAO_HUMANA` | atribuição em atividade que não é humana |
| `I_EXECUCAO_FORA_SERVICO` | `executionType` em atividade que não é serviço |
| `I_CAPTURA_ERRO_REGERADA` | captura de erro descartada; o gerador a recria a partir de `tratamentoErro` |

`avisos` `W_LEITOR_*`: a leitura não reproduz o processo fielmente. No deploy com `processo` viram aviso
(não bloqueiam). Mostrar ao usuário; recurso fora da v1: SKILL, seção de limites.

| Código | Mensagem resumida |
|---|---|
| `W_LEITOR_ATRIBUICAO_FORA_V1` | atribuição que não cabe na v1; a atividade ficou sem responsável |
| `W_LEITOR_ATRIBUICAO_INVALIDA` | atribuição sem papel legível; a atividade ficou sem responsável |
| `W_LEITOR_CAPTURA_ERRO_PAI` | captura de erro não ligada a serviço automatizado |
| `W_LEITOR_CAPTURA_SEM_TRATAMENTO` | serviço automatizado cuja captura não tem saída; indicar `tratamentoErro` |
| `W_LEITOR_CONDICAO_ILEGIVEL` | condições ou regras que não puderam ser lidas |
| `W_LEITOR_CONDICAO_SEM_LIGACAO` | condição sem ligação de gateway exclusivo correspondente; descartada |
| `W_LEITOR_CONDICAO_SEM_REGRAS` | condição por regras sem nenhuma regra |
| `W_LEITOR_CONDICAO_TIPO` | `conditionType` desconhecido; lida como JavaScript |
| `W_LEITOR_EXECUCAO` | `executionType` do serviço diferente de 1 ou 2 |
| `W_LEITOR_FLUXO_AUTOMATICO` | ligação por prazo vira ligação comum; muda o comportamento |
| `W_LEITOR_FLUXO_AUTOMATICO_DESCARTADO` | fluxo automático por prazo descartado ao lado da ligação manual |
| `W_LEITOR_FLUXO_ERRO` | captura de erro com ligações fora do formato da v1 |
| `W_LEITOR_FORMID_V2` | formulário do Form Builder (`formIdV2`); a v1 não confere os campos |
| `W_LEITOR_GATEWAY_SEM_CONDICAO` | saída de gateway sem condição |
| `W_LEITOR_LIGACAO_ORFA` | ligação para atividade que não existe |
| `W_LEITOR_LIGACAO_REPETIDA` | gateway com mais de uma ligação para o mesmo destino; condições na primeira |
| `W_LEITOR_NOME_VAZIO` | atividade sem nome |
| `W_LEITOR_OPERADOR` | operador desconhecido na condição |
| `W_LEITOR_PADRAO_FORA_GATEWAY` | marca de padrão fora de gateway exclusivo; ignorada |
| `W_LEITOR_REGRA_ORFA` | regra automática do estado sem condição por regras correspondente; descartada |
| `W_LEITOR_SEQUENCE_DUPLICADA` | número de atividade repetido; a segunda ocorrência foi descartada |
| `W_LEITOR_SEQUENCE_INVALIDA` | atividade sem número válido; descartada |
| `W_LEITOR_SERVICO_SEM_CAPTURA` | serviço automatizado sem captura de erro; o gerador cria uma |
| `W_LEITOR_TIPO_DESCONHECIDO` | tipo de atividade (bpmnType) desconhecido |
| `W_LEITOR_VALOR_TIPO` | `valueType` desconhecido; tratado como valor fixo |
