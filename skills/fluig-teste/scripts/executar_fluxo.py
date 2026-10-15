#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Camada 1 do orquestrador de testes Fluig: executa os cenários de fluxo de uma suíte
pela API do fluigcli (request start / task assume / request move / request show) e confere
etapa, status, caminho, histórico e campos gravados.

Uso:
  python3 executar_fluxo.py <suite.json> [--cenario ID ...] [--saida DIR] [--simular]

  --simular   só mostra o que seria feito (não cria nem movimenta solicitação)

Credenciais: o arquivo .env indicado em suite["servidor"]["env"] (relativo à raiz do projeto,
onde a suíte é rodada) é carregado no ambiente do fluigcli. A senha nunca é impressa.
Formato da suíte: formato-suite.md, ao lado da skill fluig-teste
Saída: <saida>/fluxo.json e código de saída 0 (tudo passou), 1 (falhou algo), 2 (erro de uso).
"""
import json
import os
import re
import base64
import subprocess
import urllib.request
from xml.sax.saxutils import escape
import sys
import tempfile
import time


def carregar_env(caminho):
    env = dict(os.environ)
    if not caminho:
        return env
    with open(caminho, encoding='utf-8') as f:
        for linha in f:
            linha = linha.strip()
            if not linha or linha.startswith('#') or '=' not in linha:
                continue
            k, v = linha.split('=', 1)
            env[k.strip()] = v.strip().strip('"').strip("'")
    return env


class Fluig:
    def __init__(self, env, servidor_esperado):
        self.env = env
        self.servidor_esperado = servidor_esperado

    def rodar(self, args, json_out=True):
        cmd = ['fluigcli'] + args + ['--non-interactive']
        if json_out:
            cmd.append('--json')
        p = subprocess.run(cmd, capture_output=True, text=True, env=self.env, timeout=300)
        saida = (p.stdout or '') + (p.stderr or '')
        dados = None
        if json_out:
            m = re.search(r'\{.*\}', p.stdout or '', re.S)
            if m:
                try:
                    dados = json.loads(m.group(0))
                except ValueError:
                    dados = None
        if dados and self.servidor_esperado and dados.get('server') and dados['server'] != self.servidor_esperado:
            raise SystemExit('ABORTADO: o fluigcli respondeu pelo servidor "%s", a suíte exige "%s"'
                             % (dados['server'], self.servidor_esperado))
        return p.returncode, dados, saida.strip()

    def estado(self, numero):
        rc, d, txt = self.rodar(['request', 'show', str(numero)])
        if not d or not d.get('ok'):
            return None, 'request show falhou: ' + txt[-300:]
        req = d['data']['request']
        tarefas = d['data'].get('tasks', [])
        abertas = [t['sequence'] for t in tarefas if t.get('status') == 'NOT_COMPLETED']
        caminho = []
        for t in tarefas:
            if t.get('status') == 'TRANSFERRED':
                continue
            if not caminho or caminho[-1] != t['sequence']:
                caminho.append(t['sequence'])
        etapa = abertas[0] if abertas else (caminho[-1] if caminho else None)
        return {'status': req.get('status'), 'etapa': etapa, 'caminho': caminho,
                'formRecordId': req.get('formRecordId')}, None


def numero_de(dados, texto):
    def procura(o):
        if isinstance(o, dict):
            for k in ('processInstanceId', 'requestId', 'id', 'number'):
                if isinstance(o.get(k), int):
                    return o[k]
            for v in o.values():
                r = procura(v)
                if r:
                    return r
        return None
    if dados and dados.get('data'):
        n = procura(dados['data'])
        if n:
            return n
    m = re.search(r'solicita\w+ (\d+)', texto)
    return int(m.group(1)) if m else None


def arquivo_campos(campos):
    f = tempfile.NamedTemporaryFile('w', suffix='.json', delete=False, encoding='utf-8')
    json.dump(campos, f, ensure_ascii=False)
    f.close()
    return f.name


def conferir(esperado, atual, onde, checks):
    for chave in ('etapa', 'status'):
        if chave in esperado:
            ok = atual is not None and atual.get(chave) == esperado[chave]
            checks.append({'onde': onde, 'item': chave, 'esperado': esperado[chave],
                           'observado': atual.get(chave) if atual else None, 'ok': ok})


def aguardar(fl, numero, esperado, atual):
    """Tarefa de serviço em segundo plano: consulta a solicitação a cada 3 s até bater com o
    esperado (etapa/status) ou passar esperado["aguardar"] segundos."""
    limite = time.time() + float(esperado.get('aguardar') or 0)
    def bate(a):
        return a is not None and all(a.get(k) == esperado[k] for k in ('etapa', 'status') if k in esperado)
    while not bate(atual) and time.time() < limite:
        time.sleep(3)
        novo, erro = fl.estado(numero)
        if novo is not None:
            atual = novo
    return atual


SOAP_SAVE_AND_SEND = """<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:ws="http://ws.workflow.ecm.technology.totvs.com/">
<soapenv:Body><ws:saveAndSendTask>
<username>%(usuario)s</username><password>%(senha)s</password><companyId>%(empresa)s</companyId>
<processInstanceId>%(numero)d</processInstanceId><choosedState>%(destino)d</choosedState>
<colleagueIds/><comments>%(comentario)s</comments><userId>%(userid)s</userId><completeTask>true</completeTask>
<attachments>%(anexos)s</attachments><cardData>%(campos)s</cardData><appointment/>
<managerMode>false</managerMode><threadSequence>0</threadSequence>
</ws:saveAndSendTask></soapenv:Body></soapenv:Envelope>"""


def destino_unico(fl, numero, etapa):
    """Única saída da etapa na versão da solicitação (LINK_PROCES); None se houver mais de uma."""
    rc, d, txt = fl.rodar(['db', 'query',
                           'SELECT l.NUM_SEQ_ESTADO_FINAL FROM LINK_PROCES l JOIN PROCES_WORKFLOW p '
                           'ON p.COD_DEF_PROCES = l.COD_DEF_PROCES AND p.NUM_VERS = l.NUM_VERS '
                           'WHERE p.NUM_PROCES = %d AND l.NUM_SEQ_ESTADO_INICIAL = %d' % (numero, int(etapa))])
    linhas = ((d or {}).get('data') or {}).get('rows') or []
    valores = [list(l.values())[0] if isinstance(l, dict) else l[0] for l in linhas]
    return int(valores[0]) if len(valores) == 1 else None


def mover_com_anexo(env, numero, destino, campos, anexos, comentario):
    """Envia a tarefa corrente com anexos pelo SOAP saveAndSendTask (o `request move` não anexa).
    Credenciais do .env da suíte (FLUIG_HOST, FLUIG_USER, FLUIGCLI_PASSWORD/FLUIG_PASS). Devolve (ok, msg)."""
    host = (env.get('FLUIG_HOST') or '').rstrip('/')
    usuario = env.get('FLUIG_USER') or ''
    senha = env.get('FLUIGCLI_PASSWORD') or env.get('FLUIG_PASS') or ''
    if not (host and usuario and senha):
        return False, 'anexo por passo precisa de FLUIG_HOST, FLUIG_USER e FLUIGCLI_PASSWORD no .env da suíte'
    itens = []
    for i, caminho in enumerate(anexos, 1):
        nome = escape(os.path.basename(caminho))
        with open(caminho, 'rb') as f:
            conteudo = base64.b64encode(f.read()).decode('ascii')
        itens.append('<item><attachmentSequence>%d</attachmentSequence><attachments><attach>true</attach>'
                     '<fileName>%s</fileName><filecontent>%s</filecontent><principal>true</principal>'
                     '</attachments><deleted>false</deleted><description>%s</description><fileName>%s</fileName>'
                     '<newAttach>true</newAttach></item>' % (i, nome, conteudo, nome, nome))
    cartao = ''.join('<item><item>%s</item><item>%s</item></item>' % (escape(str(k)), escape(str(v)))
                     for k, v in (campos or {}).items())
    corpo = SOAP_SAVE_AND_SEND % {'usuario': escape(usuario), 'senha': escape(senha),
                                  'empresa': escape(env.get('FLUIG_COMPANY') or '1'), 'numero': numero,
                                  'destino': destino, 'comentario': escape(comentario),
                                  'userid': escape(env.get('FLUIG_USER_ID') or usuario),
                                  'anexos': ''.join(itens), 'campos': cartao}
    req = urllib.request.Request(host + '/webdesk/ECMWorkflowEngineService', data=corpo.encode('utf-8'),
                                 headers={'Content-Type': 'text/xml; charset=utf-8', 'SOAPAction': ''})
    try:
        resp = urllib.request.urlopen(req, timeout=120).read().decode('utf-8', 'replace')
    except Exception as e:  # noqa: BLE001 — a mensagem vai para o relatório (sem a senha)
        return False, 'saveAndSendTask falhou: %s' % str(e)[:300]
    erro = re.search(r'<item>ERROR</item>\s*<item>(.*?)</item>', resp, re.S) or re.search(r'<faultstring>(.*?)</faultstring>', resp, re.S)
    if erro:
        return False, 'saveAndSendTask: %s' % erro.group(1)[:300]
    return True, ''


def executar_cenario(fl, suite, cen, simular):
    proc = suite['processo']
    marca = '[TESTE %s] %s' % (suite.get('execucao', ''), cen['id'])
    campos = dict(suite.get('camposBase', {}))
    campos.update(cen.get('campos', {}))
    r = {'id': cen['id'], 'descricao': cen.get('descricao', ''), 'solicitacao': None,
         'checks': [], 'erros': [], 'resultado': None}

    if simular:
        print('  iniciar %s com %d campo(s)%s' % (proc, len(campos),
              ' → esperado ' + json.dumps(cen.get('inicio', {}).get('esperado', {})) if cen.get('inicio') else ''))
        for p in cen.get('passos', []):
            print('  na etapa %s: assumir e mover%s%s%s → esperado %s' % (
                p.get('etapa'), ' para ' + str(p['destino']) if p.get('destino') else '',
                ' anexando ' + ', '.join(os.path.basename(a) for a in p['anexos']) if p.get('anexos') else '',
                ' com ' + ', '.join(p.get('campos', {}).keys()) if p.get('campos') else '',
                json.dumps(p.get('esperado', {}), ensure_ascii=False)))
        r['resultado'] = 'simulado'
        return r

    args = ['request', 'start', proc, '--fields-file', arquivo_campos(campos), '--comment', marca, '-y']
    for anexo in cen.get('anexos', suite.get('anexos', [])):  # processo que exige anexo no início
        args += ['--attach', anexo]
    rc, d, txt = fl.rodar(args)
    n = numero_de(d, txt)
    if rc != 0 or not n:
        r['erros'].append('início falhou: ' + txt[-400:])
        r['resultado'] = 'bloqueado'
        return r
    r['solicitacao'] = n
    print('  solicitação %d criada' % n)
    atual, erro = fl.estado(n)
    if erro:
        r['erros'].append(erro)
    atual = aguardar(fl, n, cen.get('inicio', {}).get('esperado', {}), atual)
    conferir(cen.get('inicio', {}).get('esperado', {}), atual, 'início', r['checks'])

    for i, p in enumerate(cen.get('passos', []), 1):
        onde = 'passo %d (etapa %s)' % (i, p.get('etapa'))
        if p.get('etapa') is not None and (atual is None or atual['etapa'] != p['etapa']):
            r['checks'].append({'onde': onde, 'item': 'etapa antes do passo', 'esperado': p['etapa'],
                                'observado': atual and atual['etapa'], 'ok': False})
            r['erros'].append('%s: solicitação não está na etapa esperada; passos seguintes não executados' % onde)
            break
        fl.rodar(['task', 'assume', str(n), '-y'])  # pool: assume; tarefa já sua: o erro é inofensivo
        if p.get('anexos'):  # atividade que exige anexo nela mesma: SOAP saveAndSendTask
            destino = p.get('destino') or destino_unico(fl, n, atual['etapa'])
            if not destino:
                r['erros'].append('%s: etapa com mais de uma saída; informe "destino" no passo com anexos' % onde)
                break
            ok, msg = mover_com_anexo(fl.env, n, int(destino), p.get('campos'), p['anexos'],
                                      '%s · passo %d' % (marca, i))
            if not ok:
                r['erros'].append('%s: movimento com anexo falhou: %s' % (onde, msg))
                break
        else:
            args = ['request', 'move', str(n), '--comment', '%s · passo %d' % (marca, i), '-y']
            if p.get('destino'):
                args += ['--target-state', str(p['destino'])]
            if p.get('campos'):
                args += ['--fields-file', arquivo_campos(p['campos'])]
            rc, d, txt = fl.rodar(args)
            if rc != 0:
                r['erros'].append('%s: movimento falhou: %s' % (onde, txt[-400:]))
                break
        time.sleep(1)
        atual, erro = fl.estado(n)
        if erro:
            r['erros'].append(erro)
        atual = aguardar(fl, n, p.get('esperado', {}), atual)
        conferir(p.get('esperado', {}), atual, onde, r['checks'])

    v = cen.get('verificar', {})
    if 'caminho' in v and atual:
        it = iter(atual['caminho'])
        ok = all(any(s == x for x in it) for s in v['caminho'])  # subsequência em ordem
        r['checks'].append({'onde': 'final', 'item': 'passa pelas etapas-chave, em ordem (o caminho real pode ter outras entre elas)', 'esperado': v['caminho'],
                            'observado': atual['caminho'], 'ok': ok})
    if v.get('naoPassaPor') and atual:
        for s in v['naoPassaPor']:
            r['checks'].append({'onde': 'final', 'item': 'não passa por %s' % s, 'esperado': False,
                                'observado': s in atual['caminho'], 'ok': s not in atual['caminho']})
    if v.get('historico'):
        rc, d, txt = fl.rodar(['db', 'query',
                               'SELECT NUM_SEQ, CAST(OBSERVATION AS VARCHAR(2000)) OBS FROM PROCESS_OBSERVATION '
                               'WHERE NUM_PROCESS=%d ORDER BY OBSERVATION_ID' % n])
        dados_q = (d or {}).get('data') or {}
        colunas = [c.get('name') if isinstance(c, dict) else c for c in (dados_q.get('columns') or ['NUM_SEQ', 'OBS'])]
        linhas = [l if isinstance(l, dict) else dict(zip(colunas, l)) for l in dados_q.get('rows', [])]
        for h in v['historico']:
            achou = [l for l in linhas
                     if ('etapa' not in h or str(l.get('NUM_SEQ')) == str(h['etapa']))
                     and h['contem'] in re.sub(r'<[^>]+>', '', str(l.get('OBS', '')))]
            if 'vezes' in h:
                r['checks'].append({'onde': 'histórico', 'item': '"%s" aparece %d vez(es)' % (h['contem'], h['vezes']),
                                    'esperado': h['vezes'], 'observado': len(achou), 'ok': len(achou) == h['vezes']})
            else:
                r['checks'].append({'onde': 'histórico', 'item': 'etapa %s contém "%s"' % (h.get('etapa', '*'), h['contem']),
                                    'esperado': True, 'observado': bool(achou), 'ok': bool(achou)})
    if v.get('campos') and atual and atual.get('formRecordId') and suite.get('datasetFormulario'):
        nomes = ['documentid'] + list(v['campos'].keys())
        rc, d, txt = fl.rodar(['dataset', 'query', suite['datasetFormulario'], '--constraint',
                               'documentid=%s' % atual['formRecordId'], '--fields', ','.join(nomes)])
        linha = ((d or {}).get('data', {}).get('rows') or [{}])[0] if d else {}
        for k, esperado in v['campos'].items():
            r['checks'].append({'onde': 'campos gravados', 'item': k, 'esperado': esperado,
                                'observado': linha.get(k), 'ok': linha.get(k) == esperado})

    falhou = r['erros'] or any(not c['ok'] for c in r['checks'])
    r['resultado'] = 'reprovado' if falhou else 'aprovado'
    if r['erros'] and not r['checks']:
        r['resultado'] = 'bloqueado'
    return r


def main():
    args = sys.argv[1:]
    if not args or args[0].startswith('-'):
        print(__doc__)
        return 2
    caminho = args[0]
    filtro, saida, simular = [], 'testes/resultados', False
    i = 1
    while i < len(args):
        if args[i] == '--cenario':
            filtro.append(args[i + 1]); i += 2
        elif args[i] == '--saida':
            saida = args[i + 1]; i += 2
        elif args[i] == '--simular':
            simular = True; i += 1
        else:
            print('opção desconhecida: ' + args[i]); return 2
    suite = json.load(open(caminho, encoding='utf-8'))
    suite.setdefault('execucao', time.strftime('%Y%m%d-%H%M'))
    srv = suite.get('servidor', {})
    fl = Fluig(carregar_env(srv.get('env')), srv.get('nome'))

    if not simular:
        # Trava de ambiente: só roda em servidor marcado como não produtivo no fluigcli
        rc, d, txt = fl.rodar(['server', 'list'])
        servidores = (d or {}).get('data', {}).get('servers', []) if d else []
        alvo = next((s for s in servidores if s.get('name') == srv.get('nome')), None)
        amb = (alvo or {}).get('env') or ''
        if amb in ('', 'prod', 'producao', 'production'):
            print('ABORTADO: o servidor "%s" está marcado como "%s" no fluigcli. A camada 1 só roda em '
                  'servidor não produtivo (ex.: fluigcli server update %s --env hml).'
                  % (srv.get('nome'), amb or 'sem ambiente', srv.get('nome')))
            return 2
        print('servidor %s (%s) — ambiente não produtivo, execução autorizada' % (srv.get('nome'), amb))

    cenarios = [c for c in suite.get('cenarios', []) if not filtro or c['id'] in filtro]
    resultados = []
    for c in cenarios:
        print('== %s — %s' % (c['id'], c.get('descricao', '')))
        r = executar_cenario(fl, suite, c, simular)
        for ch in r['checks']:
            print('  %s %s · %s: esperado %s, observado %s' % ('OK ' if ch['ok'] else 'XX ', ch['onde'], ch['item'],
                                                              json.dumps(ch['esperado'], ensure_ascii=False),
                                                              json.dumps(ch['observado'], ensure_ascii=False)))
        for e in r['erros']:
            print('  ERRO ' + e)
        print('  → %s' % r['resultado'])
        resultados.append(r)

    if simular:
        return 0
    os.makedirs(saida, exist_ok=True)
    destino = os.path.join(saida, 'fluxo-%s-%s.json' % (re.sub(r'\W+', '_', suite['processo'])[:40], suite['execucao']))
    json.dump({'execucao': suite['execucao'], 'processo': suite['processo'], 'servidor': srv.get('nome'),
               'cenarios': resultados}, open(destino, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
    placar = {}
    for r in resultados:
        placar[r['resultado']] = placar.get(r['resultado'], 0) + 1
    print('\nplacar: %s · resultado em %s' % (json.dumps(placar, ensure_ascii=False), destino))
    return 0 if all(r['resultado'] == 'aprovado' for r in resultados) else 1


if __name__ == '__main__':
    sys.exit(main())
