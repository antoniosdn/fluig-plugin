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
import subprocess
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
            print('  na etapa %s: assumir e mover%s%s → esperado %s' % (
                p.get('etapa'), ' para ' + str(p['destino']) if p.get('destino') else '',
                ' com ' + ', '.join(p.get('campos', {}).keys()) if p.get('campos') else '',
                json.dumps(p.get('esperado', {}), ensure_ascii=False)))
        r['resultado'] = 'simulado'
        return r

    args = ['request', 'start', proc, '--fields-file', arquivo_campos(campos), '--comment', marca, '-y']
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
    conferir(cen.get('inicio', {}).get('esperado', {}), atual, 'início', r['checks'])

    for i, p in enumerate(cen.get('passos', []), 1):
        onde = 'passo %d (etapa %s)' % (i, p.get('etapa'))
        if p.get('etapa') is not None and (atual is None or atual['etapa'] != p['etapa']):
            r['checks'].append({'onde': onde, 'item': 'etapa antes do passo', 'esperado': p['etapa'],
                                'observado': atual and atual['etapa'], 'ok': False})
            r['erros'].append('%s: solicitação não está na etapa esperada; passos seguintes não executados' % onde)
            break
        fl.rodar(['task', 'assume', str(n), '-y'])  # pool: assume; tarefa já sua: o erro é inofensivo
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
