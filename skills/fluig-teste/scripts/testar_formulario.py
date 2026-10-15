#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Camada 2 do orquestrador de testes Fluig: abre o formulário em navegador headless
(Brave ou Chrome) com os assets reais do Fluig, simula cada atividade e confere a tela:
card e barra da ajuda, painéis visíveis/ocultos, campos somente leitura e o resultado do
beforeSendValidate para cada envio (origem → destino). Não cria nada no servidor.

Uso:
  python3 testar_formulario.py <suite.json> [--caso ID ...] [--saida DIR]

Lê suite["formulario"] (formato em formato-suite.md, ao lado da skill).
Os assets (jquery, fluig-style-guide) são baixados uma vez de FLUIG_HOST (do .env da suíte)
para ~/.cache/fluig-teste/assets/.
Saída: <saida>/formulario-<execucao>.json; código 0 (tudo passou), 1 (falhou algo), 2 (erro de uso).
"""
import html as htmlmod
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request

AQUI = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(os.path.expanduser('~'), '.cache', 'fluig-teste', 'assets')
MAPA = {
    '/style-guide/css/fluig-style-guide.min.css': 'fluig-style-guide.min.css',
    '/portal/resources/js/jquery/jquery.js': 'jquery.js',
    '/style-guide/js/fluig-style-guide.min.js': 'fluig-style-guide.min.js',
    # o style guide depende do Mustache; sem ele o FLUIGC não é criado
    '/portal/resources/js/mustache/mustache-min.js': 'mustache-min.js',
    '/resources/js/mustache/mustache-min.js': 'mustache-min.js',
    '/portal/resources/js/jquery/jquery-ui.min.js': 'jquery-ui.min.js',
}
NAVEGADORES = ['/Applications/Brave Browser.app/Contents/MacOS/Brave Browser',
               '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
               '/usr/bin/google-chrome', '/usr/bin/chromium']


def ler_env(caminho):
    env = {}
    if caminho and os.path.exists(caminho):
        for linha in open(caminho, encoding='utf-8'):
            linha = linha.strip()
            if '=' in linha and not linha.startswith('#'):
                k, v = linha.split('=', 1)
                env[k.strip()] = v.strip().strip('"').strip("'")
    return env


def garantir_assets(host):
    os.makedirs(ASSETS, exist_ok=True)
    for url, nome in MAPA.items():
        destino = os.path.join(ASSETS, nome)
        if not os.path.exists(destino):
            if not host:
                raise SystemExit('faltam os assets do Fluig e não há FLUIG_HOST no .env da suíte')
            urllib.request.urlretrieve(host.rstrip('/') + url, destino)


def baixar_cdn(url):
    """Script/estilo de CDN: baixa uma vez para .assets/cdn e serve local (fiel ao formulário)."""
    import hashlib
    pasta = os.path.join(ASSETS, 'cdn')
    os.makedirs(pasta, exist_ok=True)
    destino = os.path.join(pasta, hashlib.sha1(url.encode()).hexdigest()[:12] + '_' + os.path.basename(url.split('?')[0]))
    if not os.path.exists(destino):
        try:
            urllib.request.urlretrieve(url, destino)
        except Exception:
            return None
    return 'file://' + destino


def preparar_html(texto):
    for url, nome in MAPA.items():
        texto = texto.replace('"' + url + '"', '"file://' + os.path.join(ASSETS, nome) + '"')
    for url in set(re.findall(r'(?:src|href)="(https?://[^"]+\.(?:js|css)(?:\?[^"]*)?)"', texto)):
        local = baixar_cdn(url)
        if local:
            texto = texto.replace('"' + url + '"', '"' + local + '"')
    # o que sobrar do servidor (caminho /...) ou de CDN sem download não existe fora do Fluig
    texto = re.sub(r'<script[^>]*src="(?:/|https?:)[^"]*"[^>]*>\s*</script>', '', texto)
    texto = re.sub(r'<link[^>]*href="(?:/|https?:)[^"]*"[^>]*>', '', texto)
    return texto


STUB = '''<script>
window.__errosJs = [];
window.addEventListener('error', function (ev) { window.__errosJs.push((ev.message || 'erro') + ' @ ' + String(ev.filename || '').split('/').pop() + ':' + (ev.lineno || '')); });
var currentTask = %(task)s, modForm = %(modo)s, cardId = '1', currentProc = '1';
var formMode = modForm, currentUser = 'teste';  // nomes que o displayFields de alguns formulários injeta
%(globais)s
var __DS = %(datasets)s;
var DatasetFactory = { getDataset: function (n) { return { values: __DS[n] || [] }; },
  createConstraint: function () { return {}; } };
var ConstraintType = { MUST: 1, SHOULD: 2, MUST_NOT: 3 };
// funções globais que o Fluig fornece ao formulário (zoom): sem efeito fora dele
window.reloadZoomFilterValues = function () { };
window.WCMAPI = { userEmail: %(email)s, user: %(email)s, userCode: 'teste', isIe9: function () { return false; },
  getLocale: function () { return 'pt_BR'; } };  // FLUIGC.calendar lê o idioma daqui
// página pai do portal (o formulário roda num iframe no Fluig): parent.$, parent.document.body, parent.WCMAPI
window.parent = { WCMAPI: window.WCMAPI, document: { body: document.documentElement },
  $: function () { return window.jQuery.apply(window, arguments); },
  jQuery: function () { return window.jQuery.apply(window, arguments); } };
function getAtividade() { return String(currentTask); }
function getMode() { return modForm; }
function getMobile() { return false; }
</script>'''

COLETA = '''<script>
$(window).on('load', function () { setTimeout(function () {
  var C = %(caso)s, r = { erros: [] };
  function vis(s) { return $(s).length > 0 && $(s).is(':visible'); }
  try {
    r.card = $('.ajuda-card-titulo').first().text();
    r.etapas = {};
    $('.ajuda-etapa').each(function () {
      r.etapas[$(this).find('.ajuda-etapa-nome').text()] = this.className.replace(/.*ajuda-etapa-/, '');
    });
    r.paineisVisiveis = $('.panel[id]').filter(':visible').map(function () { return '#' + this.id; }).get();
    r.somenteLeitura = {};
    $.each((C.esperado || {}).somenteLeitura || {}, function (s) { r.somenteLeitura[s] = $(s).prop('readonly') === true; });
    r.visivel = {};
    $.each(((C.esperado || {}).visiveis || []).concat((C.esperado || {}).ocultos || []), function (_, s) { r.visivel[s] = vis(s); });
    r.envios = [];
    $.each(C.envios || [], function (_, e) {
      $.each(e.antes || {}, function (s, v) { $(s).val(v).trigger('change'); });
      var msg = null;
      try { window.arrError = []; window.campoObrig = []; beforeSendValidate(e.de, e.para); }
      catch (x) { msg = String(x); }
      r.envios.push({ de: e.de, para: e.para, erro: msg });
    });
  } catch (x) { r.erros.push(String(x)); }
  r.erros = r.erros.concat(window.__errosJs || []);
  var p = document.createElement('pre'); p.id = 'RESULTADO_TESTE';
  p.textContent = JSON.stringify(r); document.body.appendChild(p);
}, 600); });
</script>'''


def montar_pagina(base, formulario, caso):
    pre = ''.join("$(%s).val(%s).trigger('change');" % (json.dumps(s), json.dumps(v))
                  for s, v in caso.get('valores', {}).items())
    pre += ''.join("$(%s).prop('checked',true);" % json.dumps(s) for s in caso.get('marcar', []))
    stub = STUB % {'task': json.dumps(str(caso['atividade'])), 'modo': json.dumps(caso.get('modo', 'MOD')),
                   'datasets': json.dumps(formulario.get('datasets', {}), ensure_ascii=False),
                   'email': json.dumps(formulario.get('emailUsuario', 'teste@exemplo.com')),
                   'globais': ''.join('window[%s] = %s;' % (json.dumps(k), json.dumps(v, ensure_ascii=False))
                                      for k, v in formulario.get('globais', {}).items())}
    # stubs antes do primeiro script do formulário; valores antes do document.ready; coleta no load
    pagina = re.sub(r'(<script)', stub + r'\1', base, count=1)
    pagina = pagina.replace('</body>', '<script>' + pre + '</script>'
                            + COLETA % {'caso': json.dumps(caso, ensure_ascii=False)} + '</body>')
    return pagina


def avaliar(caso, r):
    checks = []
    esp = caso.get('esperado', {})

    def add(item, esperado, observado):
        checks.append({'item': item, 'esperado': esperado, 'observado': observado, 'ok': esperado == observado})
    if 'card' in esp:
        add('card', esp['card'], r.get('card'))
    for nome, estado in esp.get('etapas', {}).items():
        add('etapa "%s"' % nome, estado, r.get('etapas', {}).get(nome))
    for s in esp.get('paineisVisiveis', []):
        add('painel %s visível' % s, True, s in r.get('paineisVisiveis', []))
    for s in esp.get('paineisOcultos', []):
        add('painel %s oculto' % s, True, s not in r.get('paineisVisiveis', []))
    for s, v in esp.get('somenteLeitura', {}).items():
        add('%s somente leitura' % s, v, r.get('somenteLeitura', {}).get(s))
    for s in esp.get('visiveis', []):
        add('%s visível' % s, True, r.get('visivel', {}).get(s))
    for s in esp.get('ocultos', []):
        add('%s oculto' % s, False, r.get('visivel', {}).get(s))
    for e, obs in zip(caso.get('envios', []), r.get('envios', [])):
        nome = 'envio %s→%s' % (e['de'], e['para'])
        msg = obs.get('erro')
        texto = re.sub(r'<[^>]+>', '', msg or '')
        if e.get('espera') == 'ok':
            add(nome + ' passa', None, texto or None)
        else:
            add(nome + ' bloqueia', True, bool(msg))
        for t in e.get('contem', []):
            add('%s mensagem contém "%s"' % (nome, t), True, t in texto)
        for t in e.get('naoContem', []):
            add('%s mensagem não contém "%s"' % (nome, t), True, t not in texto)
    for e in r.get('erros', []):
        checks.append({'item': 'erro de JavaScript', 'esperado': None, 'observado': e, 'ok': False})
    return checks


def main():
    args = sys.argv[1:]
    if not args or args[0].startswith('-'):
        print(__doc__)
        return 2
    suite = json.load(open(args[0], encoding='utf-8'))
    filtro, saida = [], 'testes/resultados'
    i = 1
    while i < len(args):
        if args[i] == '--caso':
            filtro.append(args[i + 1]); i += 2
        elif args[i] == '--saida':
            saida = args[i + 1]; i += 2
        else:
            print('opção desconhecida: ' + args[i]); return 2
    form = suite.get('formulario')
    if not form:
        print('a suíte não tem a seção "formulario"')
        return 2
    navegador = next((n for n in NAVEGADORES if os.path.exists(n)), None)
    if not navegador:
        print('nenhum Brave/Chrome encontrado para o teste headless')
        return 2
    garantir_assets(ler_env(suite.get('servidor', {}).get('env')).get('FLUIG_HOST'))

    tmp = tempfile.mkdtemp(prefix='fluig-teste-')
    shutil.copytree(form['pasta'], os.path.join(tmp, 'form'))
    base = preparar_html(open(os.path.join(tmp, 'form', form['html']), encoding='utf-8').read())

    execucao = suite.get('execucao') or time.strftime('%Y%m%d-%H%M')
    resultados = []
    for caso in form.get('casos', []):
        if filtro and caso['id'] not in filtro:
            continue
        arq = os.path.join(tmp, 'form', 'teste_%s.html' % re.sub(r'\W', '_', caso['id']))
        open(arq, 'w', encoding='utf-8').write(montar_pagina(base, form, caso))
        p = subprocess.run([navegador, '--headless=new', '--disable-gpu', '--allow-file-access-from-files',
                            '--virtual-time-budget=5000', '--dump-dom', 'file://' + arq],
                           capture_output=True, text=True, timeout=90)
        m = re.search(r'<pre id="RESULTADO_TESTE">(\{.*?)</pre>', p.stdout, re.S)
        bruto = json.loads(htmlmod.unescape(m.group(1))) if m else {'erros': ['a página não terminou de carregar']}
        checks = avaliar(caso, bruto)
        ok = all(c['ok'] for c in checks)
        print('== %s (atividade %s) → %s' % (caso['id'], caso['atividade'], 'aprovado' if ok else 'reprovado'))
        for c in checks:
            if not c['ok']:
                print('  XX %s: esperado %s, observado %s' % (c['item'], json.dumps(c['esperado'], ensure_ascii=False),
                                                           json.dumps(c['observado'], ensure_ascii=False)))
        resultados.append({'id': caso['id'], 'atividade': caso['atividade'],
                           'resultado': 'aprovado' if ok else 'reprovado', 'checks': checks, 'bruto': bruto})
    shutil.rmtree(tmp, ignore_errors=True)

    os.makedirs(saida, exist_ok=True)
    destino = os.path.join(saida, 'formulario-%s-%s.json' % (os.path.basename(form['pasta'].rstrip('/')), execucao))
    json.dump({'execucao': execucao, 'formulario': form['pasta'], 'casos': resultados},
              open(destino, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
    aprov = sum(1 for r in resultados if r['resultado'] == 'aprovado')
    print('\n%d de %d caso(s) aprovados · resultado em %s' % (aprov, len(resultados), destino))
    return 0 if aprov == len(resultados) else 1


if __name__ == '__main__':
    sys.exit(main())
