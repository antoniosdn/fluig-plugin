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
(`SecurityError ... cross-origin frame`). Nesse caso, passe **os dois hosts**, o do `.env` e o público,
separados por vírgula: `proxy_tela.mjs --host http://10.10.0.6:9090,https://fluig.empresa.com.br
--upstream 8786 --port 8787`. Só o público não basta: no carregamento o iframe ainda passa pelo host
interno, o portal perde o formulário e o Enviar manda `formData: []` (o servidor acusa todos os campos
vazios e o `beforeSendValidate` não roda). Para conferir, veja o
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
Tarefa de pool **em ramo paralelo** (depois de um gateway paralelo): `fluigcli task assume <n> --thread <ramo>`.
O ramo está em `HISTOR_PROCES.NUM_SEQ_THREAD` do movimento aberto:
`fluigcli db query "SELECT h.NUM_SEQ_ESTADO, h.NUM_SEQ_MOVTO, h.NUM_SEQ_THREAD FROM HISTOR_PROCES h JOIN TAR_PROCES t ON t.NUM_PROCES=h.NUM_PROCES AND t.NUM_SEQ_MOVTO=h.NUM_SEQ_MOVTO AND t.IDI_STATUS=0 WHERE h.NUM_PROCES=<n>"`.
Depois da junção o ramo continua diferente de 0 (na Admissão foi 6): consulte sempre, não presuma 0.
Tarefa de serviço em segundo plano: espere a etapa seguinte em `TAR_PROCES`/`HISTOR_PROCES`.

## 3. Como preencher

- **`javascript_tool` na página do portal: nunca declare `var $`** (nem `var jQuery`) no escopo da
  página. O código roda no escopo global e troca o jQuery do portal; o Enviar passa a mandar
  `formData` vazio (o servidor cobra todos os campos). Use uma IIFE e o `$` do iframe:
  `(function () { var w = document.getElementById('workflowView-cardViewer').contentWindow; w.$('#campo').val('x').trigger('change'); })()`.
- **Digitar e clicar como usuário** em campos de texto e zooms (clique no campo, digite parte do
  texto, escolha o item na lista). O formulário fica num iframe: `find`/`read_page` não entram nele;
  use screenshot e coordenadas, rolando a página.
- **Select nativo** (a lista do sistema não aparece no navegador do app):
  `document.getElementById('workflowView-cardViewer').contentWindow.$('#campo').val('x').trigger('change')`.
- **Anexo**: a janela de arquivo do sistema não abre. Na aba Anexos, entregue um arquivo ao campo
  de envio do portal. Use um **PDF válido**, de preferência o `testes/anexos/documento-teste.pdf` do
  projeto: um texto qualquer como `'%PDF-1.4 ...'` é gravado pelo Fluig, mas o anexo não abre. Gere o
  base64 no terminal (`base64 -i testes/anexos/documento-teste.pdf`) e cole no lugar de `<BASE64>`:
  ```js
  (function () {
    var b = atob('<BASE64>'), u = new Uint8Array(b.length);
    for (var i = 0; i < b.length; i++) u[i] = b.charCodeAt(i);
    var f = new File([u], 'documento-teste.pdf', {type: 'application/pdf'});
    var dt = new DataTransfer(); dt.items.add(f);
    var inp = document.getElementById('ecm-navigation-inputFile-clone');
    inp.files = dt.files; inp.dispatchEvent(new Event('change', {bubbles: true}));
  })();
  ```
  Antes de anexar, feche o aviso **"Status do Servidor"** se ele aparecer: aberto, ele impede o
  upload. O anexo entra na atividade corrente (confira com `fluigcli request attachments <n>`).
- **Enviar** pelo botão Enviar da página.
- **Sessão do `fluigcli dev` expirada** (o preview cai na tela de login do Fluig): reinicie o preview
  (`preview_stop` e `preview_start`, ou o `fluigcli dev` no terminal, se for ele que está rodando).
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
