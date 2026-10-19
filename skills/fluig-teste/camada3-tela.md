# Camada 3 — caminho feliz pela tela (primeiro teste da suíte)

Roda **uma vez por processo novo ou ajustado**, antes das camadas 1 e 2, na **sessão principal**
(os subagentes não têm o navegador do app). É o único teste que exercita o Fluig de verdade:
`displayFields` no servidor, `beforeSendValidate` no envio, zooms com dataset real, botão Enviar,
anexos e a tela de cada etapa.

## 1. Proxy da tela

O `fluigcli dev` abre o portal já logado (sem senha), mas não reescreve JSON: o quadro do
formulário vem do `formHtml` do `getDefinitionProcess`, com o host do servidor, e fica em branco.
O `scripts/proxy_tela.mjs` fica na frente e reescreve o host em toda resposta de texto.

Configuração no `.claude/launch.json` do projeto (ajuste o `.env`):

```json
{
  "name": "fluig-tela-<servidor>",
  "runtimeExecutable": "bash",
  "runtimeArgs": ["-c", "set -a && . .fluigcli/<servidor>.env && set +a && S=$(ls -d ~/.claude/plugins/cache/*/fluig/*/skills/fluig-teste/scripts 2>/dev/null | sort -V | tail -1) && (fluigcli dev --port 8786 --non-interactive &) && sleep 3 && exec node \"$S\"/proxy_tela.mjs --upstream 8786 --port 8787"],
  "port": 8787
}
```

`preview_start` com esse nome. Se outro `fluigcli dev` estiver na 8787, pare antes (`preview_stop`).

**Host a reescrever = "URL do servidor" do WCM**, não o host do `.env`. O `formHtml` e o `src` do
iframe do formulário saem com a URL configurada no WCM (`WCM_CONFIGURATION.SERVER_URL`). Se ela
for uma URL pública (ex.: `https://fluig.empresa.com.br`) e o `.env` usar o IP interno, o iframe
aponta para o host público, fica com origem diferente do proxy e o teste não lê o formulário
(`SecurityError ... cross-origin frame`). Nesse caso, passe o host público: `proxy_tela.mjs --host
https://fluig.empresa.com.br --upstream 8786 --port 8787`. Para conferir, veja o
`document.getElementById('workflowView-cardViewer').src`: ele tem de começar por `http://localhost:8787`.

**`fluigcli dev` sem rota para o servidor** ("no route to host" no log do preview, mas o mesmo host
responde pelo terminal): o processo aberto pelo app não tem acesso à rede local do macOS. Suba o
`fluigcli dev --port 8786 --non-interactive` pelo terminal (Bash em segundo plano, com o `.env`
carregado) e deixe no `launch.json` só o `proxy_tela.mjs` (configuração sem o `fluigcli dev`).

## 2. URLs

| Para | URL (em `http://localhost:8787`) |
|---|---|
| Abrir solicitação nova | `/portal/p/01/pageworkflowview?processID=<processId>` |
| Movimentar tarefa | `/portal/p/01/pageworkflowview?app_ecm_workflowview_processInstanceId=<n>&app_ecm_workflowview_currentMovto=<mov>&app_ecm_workflowview_taskUserId=<login>&app_ecm_workflowview_managerMode=false` |
| Detalhes (fim) | `/portal/p/01/pageworkflowview?app_ecm_workflowview_detailsProcessInstanceID=<n>` |

Número da solicitação recém-aberta e movimentação atual:
`fluigcli db query "SELECT TOP 1 p.NUM_PROCES, t.NUM_SEQ_MOVTO FROM PROCES_WORKFLOW p JOIN TAR_PROCES t ON t.NUM_PROCES=p.NUM_PROCES AND t.IDI_STATUS=0 WHERE p.COD_DEF_PROCES='<processId>' ORDER BY p.NUM_PROCES DESC"`.
Tarefa de pool: `fluigcli task assume <n>` antes de abrir (a movimentação muda: consulte de novo).
Tarefa de serviço em segundo plano: espere a etapa seguinte em `TAR_PROCES`/`HISTOR_PROCES`.

## 3. Como preencher

- **Digitar e clicar como usuário** em campos de texto e zooms (clique no campo, digite parte do
  texto, escolha o item na lista). O formulário fica num iframe: `find`/`read_page` não entram nele;
  use screenshot e coordenadas, rolando a página.
- **Select nativo** (a lista do sistema não aparece no navegador do app):
  `document.getElementById('workflowView-cardViewer').contentWindow.$('#campo').val('x').trigger('change')`.
- **Anexo**: a janela de arquivo do sistema não abre. Na aba Anexos, entregue um arquivo ao campo
  de envio do portal:
  ```js
  const f = new File(['%PDF-1.4 ...'], 'recibo-teste.pdf', {type: 'application/pdf'});
  const dt = new DataTransfer(); dt.items.add(f);
  const inp = document.getElementById('ecm-navigation-inputFile-clone');
  inp.files = dt.files; inp.dispatchEvent(new Event('change', {bubbles: true}));
  ```
  O anexo entra na atividade corrente (confira com `fluigcli request attachments <n>`).
- **Enviar** pelo botão Enviar da página.
- Máscaras (jQuery Mask) podem não formatar o que a ferramenta digita: não é defeito do formulário
  se `$('#campo').data('mask')` existe.

## 4. O que conferir em cada etapa

- card "Você está aqui" e barra de etapas (atual, feitas, puladas);
- painéis visíveis e ocultos, cabeçalho preenchido, campos sugeridos (datas, aprovador);
- **um envio sem preencher** o que é obrigatório na etapa: a mensagem cobra só o esperado;
- depois do envio: "Solicitação movimentada com sucesso" e a etapa seguinte no servidor.

No fim: `fluigcli request show <n>` (FINALIZED, caminho) e a tela de detalhes com o card de
conclusão.

## 5. Resultado e limpeza

**Sem evidência:** nenhum print vai para o projeto (decisão do usuário, 15/10/2026). Screenshot é só
para navegar. No relatório: solicitação criada, etapas percorridas, o que foi conferido em cada uma
e o que divergiu (defeito do processo × limitação da ferramenta).

No fim, pare o proxy (`preview_stop`) e apague os prints da sessão:
`rm -f ~/.claude/projects/<projeto>/<sessão>/tool-results/mcp-Claude_Browser-blob-*`
(a pasta `tool-results` da sessão aparece no caminho de cada screenshot).
