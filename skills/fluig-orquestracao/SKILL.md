---
name: fluig-orquestracao
description: Coordena tarefas de desenvolvimento Fluig em datasets, formulários, workflows e widgets. Use quando a tarefa envolver alteração de código Fluig, múltiplos arquivos, risco de incompatibilidade Rhino/ECMA 5, ou quando for necessário decidir entre execução direta, delegação a subagente e revisão independente.
---

# Orquestração Fluig

## Objetivo

Classificar a tarefa, escolher a estratégia de execução, limitar o escopo de
cada participante e garantir validação antes da entrega. Esta skill substitui a
orientação operacional do antigo hook de delegação, mas não bloqueia ferramentas
nem força tecnicamente a escolha de um modelo.

## Modelo root

O modelo root é o que o usuário selecionou no seletor do chat. Essa escolha é do
usuário e está fora do escopo desta skill — a skill orienta apenas a delegação a
subagentes.

## Tiers de delegação

Fonte única dos modelos. Ao trocar de modelo, alterar somente esta tabela.

| Tier | Nome na UI | Slug para `Task` | Uso |
|---|---|---|---|
| rápido | Composer 2.5 Fast | `composer-2.5-fast` | inspeção, busca de arquivos, validação mecânica, alteração simples |
| padrão | GPT-5.6 Terra Medium | `gpt-5.6-terra-medium` | implementação Fluig padrão e refatoração localizada |
| padrão (alt.) | Cursor Grok 4.5 Medium Fast | `cursor-grok-4.5-medium-fast` | mesma faixa do padrão, quando houver ganho de tempo |
| pesado | Opus 5 Medium | `claude-opus-5-thinking-medium` | mudanças amplas, integrações, migrações, workflow complexo, revisão crítica, arquitetura e segurança |

Omitir override de modelo quando o agente herdado for suficiente. Nunca
selecionar um nome que a interface atual não exponha.

## Classificação

Classifique antes de editar:

| Classe | Critério | Estratégia |
|---|---|---|
| Mecânica | inspeção, ajuste textual pequeno, validação ou alteração de até um arquivo sem decisão arquitetural | executar diretamente ou delegar no tier rápido |
| Padrão | implementação ou refatoração localizada em um ou poucos arquivos | delegar no tier padrão quando reduzir risco ou tempo; revisar o resultado |
| Pesada | vários módulos, integração externa, migração, workflow complexo ou mudança com alto risco de regressão | delegar por etapas no tier pesado e solicitar revisão independente |
| Crítica | segurança, credenciais, arquitetura, dados de produção ou conflito entre padrões | manter a decisão com o agente principal; revisão independente no tier pesado |

Não delegar tarefas pequenas apenas por regra. Delegar quando o escopo puder ser
fechado e a revisão do retorno for mais eficiente que a execução direta.

Limitar fan-out: um subagente por vez nas classes Mecânica e Padrão. Paralelizar
apenas quando os escopos forem disjuntos e o ganho de tempo for real — vários
subagentes simultâneos pesam mais no custo que a escolha do tier.

## Regras por área

- `datasets/`: exigir ECMA 5/Rhino, JSDoc, constraints validadas, tratamento de
  erro e ausência de credenciais hardcoded.
- `workflow/scripts/` e eventos Fluig: confirmar compatibilidade ECMA 5 quando
  executarem no servidor ou no motor do workflow.
- `forms/`: validar JavaScript de navegador, `beforeSendValidate`, tabelas
  pai/filho e dependências incluídas no formulário.
- `workflow/diagrams/`: consultar o diagrama antes de assumir estados, tarefas,
  responsáveis ou transições.
- `wcm/` e widgets: preservar estrutura de empacotamento e validar arquivos
  estáticos relacionados.

Ativar também a skill específica da área quando aplicável, especialmente
`dataset-fluig`, `fluig-validacao`, `form-fluig` e, se o projeto tiver, a skill de Query Store.

## Contrato de delegação

Ao solicitar trabalho a um subagente, informar explicitamente:

1. objetivo concreto;
2. contexto mínimo e arquivos de referência;
3. arquivos permitidos para leitura e edição;
4. arquivos proibidos e limites de escopo;
5. critérios de aceite;
6. validações esperadas;
7. formato obrigatório do retorno.

Usar este formato de retorno:

```text
Resumo:
Arquivos alterados:
Validações executadas:
Limitações ou bloqueios:
```

O subagente não deve fazer commit, alterar arquivos fora do escopo, inventar
respostas de serviços externos ou remover alterações preexistentes.

## Fluxo operacional

1. Ler `AGENTS.md` e as instruções locais mais próximas.
2. Conferir `git status --short` e identificar alterações preexistentes.
3. Mapear arquivos afetados, dependências e validações possíveis.
4. Classificar a tarefa pela tabela acima.
5. Se houver delegação, enviar o contrato com escopo fechado.
6. Revisar o retorno e o diff como agente principal.
7. Executar validações adequadas ao risco:
   - `node --check` para JavaScript compatível com Node;
   - inspeção por padrões proibidos em backend Fluig;
   - testes, build ou empacotamento quando existirem;
   - revisão de XML/HTML/CSS e referências de arquivos quando aplicável.
8. Confirmar que alterações preexistentes continuam preservadas.
9. Entregar resumo, arquivos alterados, validações e limitações.

## Limites importantes

- Esta é uma orientação de orquestração, não um hook de bloqueio.
- Não alegar que um subagente foi usado quando a execução foi direta.
- Não escolher ou prometer um modelo específico se a interface não o expuser.
- Não opinar sobre o modelo root: é escolha do usuário no seletor do chat.
- Não delegar operações destrutivas, publicação, commit ou acesso a produção sem
  autorização explícita.
- Se não houver subagente disponível, executar diretamente com o mesmo contrato,
  escopo e validações.
