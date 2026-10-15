#!/usr/bin/env node
// Camada 3 do /fluig-teste: repassador na frente do `fluigcli dev` que reescreve o endereço do
// servidor Fluig nas respostas de texto, para o portal funcionar inteiro pela porta local.
//
// Por quê: o `fluigcli dev` reescreve as páginas, mas não o JSON. A tela "Movimentar
// Solicitação" monta o quadro do formulário com o campo `formHtml` do
// /ecm/api/rest/ecm/workflowView/getDefinitionProcess, que vem com o host do servidor
// (ex.: http://10.10.0.6:9090/webdesk/streamcontrol/...). Fora do proxy o quadro fica em branco
// (sem sessão, ou origem diferente) e o botão Enviar não habilita.
//
// Uso:
//   node proxy_tela.mjs --host http://10.10.0.6:9090 [--upstream 8786] [--port 8787]
//   (sem --host, usa FLUIG_HOST do ambiente)
//
// Escuta só em 127.0.0.1. Não guarda nem imprime credencial: a sessão é a do `fluigcli dev`.
import http from 'node:http';
import zlib from 'node:zlib';

function arg(nome, padrao) {
  const i = process.argv.indexOf('--' + nome);
  return i > 0 && process.argv[i + 1] ? process.argv[i + 1] : padrao;
}

const host = (arg('host', process.env.FLUIG_HOST || '')).replace(/\/+$/, '');
const upstream = Number(arg('upstream', '8786'));
const porta = Number(arg('port', '8787'));
if (!/^https?:\/\/[^/]+$/.test(host)) {
  console.error('Informe --host http://servidor:porta (ou FLUIG_HOST).');
  process.exit(2);
}
const local = 'http://localhost:' + porta;
const semEsquema = host.replace(/^https?:/, '');           // //10.10.0.6:9090
const variantes = [host, host.replace(/\//g, '\\/'), semEsquema];
const textual = /json|javascript|html|text|xml|css/i;

function reescreve(texto) {
  let t = texto;
  t = t.split(host).join(local);
  t = t.split(variantes[1]).join(local.replace(/\//g, '\\/'));  // JSON com "\/"
  t = t.split('"' + semEsquema).join('"' + local.replace(/^https?:/, ''));
  for (const u of ['http://127.0.0.1:' + upstream, 'http://localhost:' + upstream]) t = t.split(u).join(local);
  return t;
}

const servidor = http.createServer((req, res) => {
  // Host original (localhost:<porta>): o fluigcli dev monta os links com ele, apontando para cá
  const headers = { ...req.headers };
  delete headers['accept-encoding'];                       // resposta sem compressão: dá para reescrever
  const prox = http.request({ host: '127.0.0.1', port: upstream, path: req.url, method: req.method, headers }, (up) => {
    const h = { ...up.headers };
    if (h.location) h.location = reescreve(h.location);
    const tipo = h['content-type'] || '';
    if (!textual.test(tipo)) {
      res.writeHead(up.statusCode, h);
      up.pipe(res);
      return;
    }
    const partes = [];
    up.on('data', (c) => partes.push(c));
    up.on('end', () => {
      let corpo = Buffer.concat(partes);
      const enc = (h['content-encoding'] || '').toLowerCase();
      try {
        if (enc === 'gzip') corpo = zlib.gunzipSync(corpo);
        else if (enc === 'br') corpo = zlib.brotliDecompressSync(corpo);
        else if (enc === 'deflate') corpo = zlib.inflateSync(corpo);
      } catch (e) { /* corpo como veio */ }
      delete h['content-encoding'];
      const saida = Buffer.from(reescreve(corpo.toString('utf8')), 'utf8');
      h['content-length'] = String(saida.length);
      delete h['transfer-encoding'];
      res.writeHead(up.statusCode, h);
      res.end(saida);
    });
  });
  prox.on('error', (e) => {
    res.writeHead(502, { 'content-type': 'text/plain; charset=utf-8' });
    res.end('proxy_tela: fluigcli dev indisponível na porta ' + upstream + ' (' + e.message + ')');
  });
  req.pipe(prox);
});

servidor.listen(porta, '127.0.0.1', () => {
  console.log('proxy_tela: ' + local + ' → fluigcli dev em 127.0.0.1:' + upstream + ' (reescrevendo ' + host + ')');
});
