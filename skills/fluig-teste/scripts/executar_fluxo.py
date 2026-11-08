#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Camada 1 do orquestrador de testes Fluig: executa os cenários de fluxo de uma suíte
pela API do fluigcli (request start / task assume / request move / request show) e confere
etapa, status, caminho, histórico e campos gravados.

Uso:
  python3 executar_fluxo.py <suite.json> [--cenario ID ...] [--saida DIR] [--simular] [--sem-ganchos]

  --simular      só mostra o que seria feito (não cria nem movimenta solicitação)
  --sem-ganchos  não roda os blocos "antesDaRodada" / "depoisDaRodada" da suíte

Ganchos da rodada (formato-suite.md): "antesDaRodada" roda antes do primeiro cenário (com "fundo":
true fica em paralelo e é ENCERRADO pelo próprio script no fim, mesmo com erro ou Ctrl-C);
"depoisDaRodada" roda depois do último. No fim o script lista as solicitações da rodada que
ficaram abertas e a etapa de cada uma.

Credenciais: o arquivo .env indicado em suite["servidor"]["env"] (relativo à raiz do projeto,
onde a suíte é rodada) é carregado no ambiente do fluigcli. A senha nunca é impressa.
Formato da suíte: formato-suite.md, ao lado da skill fluig-teste
Saída: <saida>/fluxo-<processo>-<AAAAMMDD-HHMMSS>[-<cenário>].json e código de saída 0 (tudo
passou), 1 (falhou algo), 2 (erro de uso). A saída padrão sai linha a linha (flush), mesmo com
pipe/tee: a linha "solicitação N criada" aparece na hora, para quem acompanha a rodada.
"""
import json
import os
import re
import base64
import subprocess
import urllib.request
from xml.sax.saxutils import escape
import sys
import shlex
import signal
import tempfile
import time

# Saída linha a linha também com pipe/tee (sem isso a linha "solicitação N criada" só chega no fim)
try:
    sys.stdout.reconfigure(line_buffering=True)
    sys.stderr.reconfigure(line_buffering=True)
except AttributeError:  # Python < 3.7
    pass

# Histórico: a coluna OBSERVATION é texto longo (LONGTEXT no MySQL, text/nvarchar(max) no SQL Server,
# CLOB no Oracle). Tenta sem CAST (funciona em MySQL e SQL Server) e cai para o CAST de cada banco.
SQL_HISTORICO = [
    'SELECT NUM_SEQ, OBSERVATION OBS FROM PROCESS_OBSERVATION WHERE NUM_PROCESS=%d ORDER BY OBSERVATION_ID',
    'SELECT NUM_SEQ, CAST(OBSERVATION AS CHAR(2000)) OBS FROM PROCESS_OBSERVATION WHERE NUM_PROCESS=%d ORDER BY OBSERVATION_ID',
    'SELECT NUM_SEQ, CAST(OBSERVATION AS VARCHAR(2000)) OBS FROM PROCESS_OBSERVATION WHERE NUM_PROCESS=%d ORDER BY OBSERVATION_ID',
    'SELECT NUM_SEQ, DBMS_LOB.SUBSTR(OBSERVATION, 2000, 1) OBS FROM PROCESS_OBSERVATION WHERE NUM_PROCESS=%d ORDER BY OBSERVATION_ID',
]


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
        # Gateway paralelo: mais de uma tarefa aberta; "etapa" vira a lista e o passo escolhe a sua
        etapa = (abertas[0] if len(abertas) == 1 else abertas) if abertas else (caminho[-1] if caminho else None)
        movimentos = dict((t['sequence'], t.get('movement')) for t in tarefas if t.get('status') == 'NOT_COMPLETED')
        return {'status': req.get('status'), 'etapa': etapa, 'abertas': abertas, 'movimentos': movimentos,
                'caminho': caminho, 'formRecordId': req.get('formRecordId')}, None

    def ramo(self, numero, etapa):
        """Ramo paralelo (threadSequence) da tarefa aberta na etapa: HISTOR_PROCES.NUM_SEQ_THREAD do
        movimento com tarefa em aberto (TAR_PROCES.IDI_STATUS = 0). 0 no fluxo único ou se a consulta falhar."""
        rc, d, txt = self.rodar(['db', 'query',
                                 'SELECT DISTINCT h.NUM_SEQ_THREAD FROM HISTOR_PROCES h JOIN TAR_PROCES t '
                                 'ON t.COD_EMPRESA = h.COD_EMPRESA AND t.NUM_PROCES = h.NUM_PROCES '
                                 'AND t.NUM_SEQ_MOVTO = h.NUM_SEQ_MOVTO '
                                 'WHERE h.NUM_PROCES = %d AND h.NUM_SEQ_ESTADO = %d AND t.IDI_STATUS = 0'
                                 % (numero, int(etapa))])
        linhas = ((d or {}).get('data') or {}).get('rows') or []
        valores = [list(l.values())[0] if isinstance(l, dict) else l[0] for l in linhas]
        return int(valores[0]) if len(valores) == 1 and valores[0] is not None else 0


def tem_etapa(atual, etapa):
    """A etapa está aberta (ou é a corrente/final) — vale para fluxo único e para ramos paralelos."""
    if atual is None:
        return False
    return etapa in (atual.get('abertas') or []) or atual.get('etapa') == etapa


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
            if chave == 'etapa':
                ok = tem_etapa(atual, esperado[chave])
            else:
                ok = atual is not None and atual.get(chave) == esperado[chave]
            checks.append({'onde': onde, 'item': chave, 'esperado': esperado[chave],
                           'observado': atual.get(chave) if atual else None, 'ok': ok})


def aguardar(fl, numero, esperado, atual):
    """Tarefa de serviço em segundo plano: consulta a solicitação a cada 3 s até bater com o
    esperado (etapa/status) ou passar esperado["aguardar"] segundos."""
    limite = time.time() + float(esperado.get('aguardar') or 0)
    def bate(a):
        return (a is not None and ('etapa' not in esperado or tem_etapa(a, esperado['etapa']))
                and ('status' not in esperado or a.get('status') == esperado['status']))
    while not bate(atual) and time.time() < limite:
        time.sleep(3)
        novo, erro = fl.estado(numero)
        if novo is not None:
            atual = novo
    return atual


# Servidor atrás de proxy/WAF (ex.: acesso só pelo DNS) responde 403 a chamada HTTP sem User-Agent de navegador
USER_AGENT = 'Mozilla/5.0'

SOAP_SAVE_AND_SEND = """<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:ws="http://ws.workflow.ecm.technology.totvs.com/">
<soapenv:Body><ws:saveAndSendTask>
<username>%(usuario)s</username><password>%(senha)s</password><companyId>%(empresa)s</companyId>
<processInstanceId>%(numero)d</processInstanceId><choosedState>%(destino)d</choosedState>
<colleagueIds/><comments>%(comentario)s</comments><userId>%(userid)s</userId><completeTask>true</completeTask>
<attachments>%(anexos)s</attachments><cardData>%(campos)s</cardData><appointment/>
<managerMode>false</managerMode><threadSequence>%(ramo)d</threadSequence>
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


def mover_com_anexo(env, numero, destino, campos, anexos, comentario, ramo=0):
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
                                  'anexos': ''.join(itens), 'campos': cartao, 'ramo': ramo}
    req = urllib.request.Request(host + '/webdesk/ECMWorkflowEngineService', data=corpo.encode('utf-8'),
                                 headers={'Content-Type': 'text/xml; charset=utf-8', 'SOAPAction': '',
                                          'User-Agent': USER_AGENT})
    try:
        resp = urllib.request.urlopen(req, timeout=120).read().decode('utf-8', 'replace')
    except Exception as e:  # noqa: BLE001 — a mensagem vai para o relatório (sem a senha)
        return False, 'saveAndSendTask falhou: %s' % str(e)[:300]
    erro = re.search(r'<item>ERROR</item>\s*<item>(.*?)</item>', resp, re.S) or re.search(r'<faultstring>(.*?)</faultstring>', resp, re.S)
    if erro:
        return False, 'saveAndSendTask: %s' % erro.group(1)[:300]
    return True, ''


def historico(fl, numero):
    """Linhas {NUM_SEQ, OBS} do histórico da solicitação. Devolve (linhas, None) ou (None, erro)."""
    ultimo = ''
    for sql in SQL_HISTORICO:
        rc, d, txt = fl.rodar(['db', 'query', sql % numero])
        if d and d.get('ok'):
            dados_q = d.get('data') or {}
            colunas = [c.get('name') if isinstance(c, dict) else c
                       for c in (dados_q.get('columns') or ['NUM_SEQ', 'OBS'])]
            return [l if isinstance(l, dict) else dict(zip(colunas, l)) for l in dados_q.get('rows', [])], None
        ultimo = ((d or {}).get('error') or {}).get('message') or txt[-300:]
    return None, ultimo[:300]


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
        if p.get('etapa') is not None and not tem_etapa(atual, p['etapa']):
            # junção/divisão paralela e atividades automáticas podem levar alguns segundos
            atual = aguardar(fl, n, {'etapa': p['etapa'], 'aguardar': 15}, atual)
        if p.get('etapa') is not None and not tem_etapa(atual, p['etapa']):
            r['checks'].append({'onde': onde, 'item': 'etapa antes do passo', 'esperado': p['etapa'],
                                'observado': atual and atual['etapa'], 'ok': False})
            r['erros'].append('%s: solicitação não está na etapa esperada; passos seguintes não executados' % onde)
            break
        etapa = p.get('etapa') if p.get('etapa') is not None else atual['etapa']
        paralelo = len(atual.get('abertas') or []) > 1
        ramo = fl.ramo(n, etapa)  # depois da junção o ramo continua diferente de 0
        # pool: assume; tarefa já sua: o erro é inofensivo
        fl.rodar(['task', 'assume', str(n), '--thread', str(ramo), '-y'])
        if p.get('anexos'):  # atividade que exige anexo nela mesma: SOAP saveAndSendTask
            destino = p.get('destino') or destino_unico(fl, n, etapa)
            if not destino:
                r['erros'].append('%s: etapa com mais de uma saída; informe "destino" no passo com anexos' % onde)
                break
            ok, msg = mover_com_anexo(fl.env, n, int(destino), p.get('campos'), p['anexos'],
                                      '%s · passo %d' % (marca, i), ramo)
            if not ok:
                r['erros'].append('%s: movimento com anexo falhou: %s' % (onde, msg))
                break
        else:
            args = ['request', 'move', str(n), '--comment', '%s · passo %d' % (marca, i), '-y']
            if paralelo and atual['movimentos'].get(etapa) is not None:
                args += ['--movement', str(atual['movimentos'][etapa])]
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
        linhas, erro_q = historico(fl, n)
        if erro_q:
            # consulta que falha não reprova em silêncio: vira erro do cenário (bloqueia os checks de histórico)
            r['erros'].append('histórico: consulta ao PROCESS_OBSERVATION falhou, checks de histórico não '
                              'conferidos: %s' % erro_q)
        for h in (v['historico'] if not erro_q else []):
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


def ultima_solicitacao(fl):
    """Maior número de solicitação no servidor antes da rodada (a rodada cria de ultima+1 em diante)."""
    rc, d, txt = fl.rodar(['db', 'query', 'SELECT MAX(NUM_PROCES) ULTIMA FROM PROCES_WORKFLOW'])
    linhas = ((d or {}).get('data') or {}).get('rows') or []
    if not linhas:
        return None
    v = list(linhas[0].values())[0] if isinstance(linhas[0], dict) else linhas[0][0]
    return int(v) if v is not None else None


def montar_comando(gancho, valores):
    """Comando do gancho com {ultima}, {execucao}, {solicitacoes} substituídos (só números/ids)."""
    cmd = gancho['comando']
    if isinstance(cmd, list):
        cmd = ' '.join(c if c.startswith('~') else shlex.quote(c) for c in cmd)
    for k, v in valores.items():
        cmd = cmd.replace('{%s}' % k, str(v))
    return cmd


def iniciar_fundo(gancho, cmd, env, saida, execucao, i):
    """Gancho em paralelo: grupo de processos próprio, saída em arquivo; o PID volta para encerrar no fim."""
    os.makedirs(saida, exist_ok=True)
    log = os.path.join(saida, 'gancho-%s-antes%d.log' % (execucao, i))
    f = open(log, 'w', encoding='utf-8')
    p = subprocess.Popen(['/bin/bash', '-c', cmd], env=env, stdout=f, stderr=subprocess.STDOUT,
                         start_new_session=True)
    print('  antesDaRodada %d em paralelo (PID %d, log %s): %s' % (i, p.pid, log, gancho.get('descricao', cmd)))
    return {'proc': p, 'arquivo': f, 'log': log, 'descricao': gancho.get('descricao', cmd)}


def encerrar_fundo(fundos):
    """Encerra os ganchos em paralelo pelo PID do grupo (nunca por pgrep/padrão): TERM, 10 s, KILL."""
    for g in fundos:
        p = g['proc']
        if p.poll() is None:
            try:
                os.killpg(p.pid, signal.SIGTERM)
                p.wait(timeout=10)
            except subprocess.TimeoutExpired:
                os.killpg(p.pid, signal.SIGKILL)
                p.wait(timeout=10)
            except ProcessLookupError:
                pass
        g['arquivo'].close()
        print('  antesDaRodada encerrado (PID %d, código %s): %s' % (p.pid, p.returncode, g['descricao']))


def main():
    args = sys.argv[1:]
    if not args or args[0].startswith('-'):
        print(__doc__)
        return 2
    caminho = args[0]
    filtro, saida, simular, ganchos = [], 'testes/resultados', False, True
    i = 1
    while i < len(args):
        if args[i] == '--cenario':
            filtro.append(args[i + 1]); i += 2
        elif args[i] == '--saida':
            saida = args[i + 1]; i += 2
        elif args[i] == '--simular':
            simular = True; i += 1
        elif args[i] == '--sem-ganchos':
            ganchos = False; i += 1
        else:
            print('opção desconhecida: ' + args[i]); return 2
    suite = json.load(open(caminho, encoding='utf-8'))
    # até o segundo: rodadas (ou cenários rodados um a um) no mesmo minuto não se sobrescrevem
    suite.setdefault('execucao', time.strftime('%Y%m%d-%H%M%S'))
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
    desconhecidos = [f for f in filtro if f not in [c['id'] for c in suite.get('cenarios', [])]]
    if desconhecidos:
        print('cenário inexistente na suíte: %s' % ', '.join(desconhecidos))
        return 2
    antes = suite.get('antesDaRodada', []) if ganchos else []
    depois = suite.get('depoisDaRodada', []) if ganchos else []
    valores = {'execucao': suite['execucao'], 'ultima': '<ultima>', 'solicitacoes': ''}
    if not simular and (antes or depois):
        ultima = ultima_solicitacao(fl)
        if ultima is None:
            print('ABORTADO: não consegui ler a última solicitação (PROCES_WORKFLOW) para os ganchos da rodada')
            return 2
        valores['ultima'] = ultima
        print('última solicitação antes da rodada: %d' % ultima)

    resultados, fundos, rodada = [], [], {'antes': [], 'depois': []}
    try:
        for i, g in enumerate(antes, 1):
            cmd = montar_comando(g, valores)
            if simular:
                print('  antesDaRodada %d%s: %s' % (i, ' (em paralelo)' if g.get('fundo') else '', cmd))
            elif g.get('fundo'):
                fundos.append(iniciar_fundo(g, cmd, fl.env, saida, suite['execucao'], i))
                rodada['antes'].append({'comando': cmd, 'fundo': True, 'pid': fundos[-1]['proc'].pid,
                                        'log': fundos[-1]['log']})
            else:
                p = subprocess.run(['/bin/bash', '-c', cmd], env=fl.env, capture_output=True, text=True,
                                   timeout=float(g.get('tempoLimite') or 300))
                print('  antesDaRodada %d (código %d): %s' % (i, p.returncode, g.get('descricao', cmd)))
                rodada['antes'].append({'comando': cmd, 'codigo': p.returncode,
                                        'saida': ((p.stdout or '') + (p.stderr or ''))[-2000:]})
                if p.returncode != 0:
                    print('ABORTADO: antesDaRodada %d terminou com código %d' % (i, p.returncode))
                    print(((p.stdout or '') + (p.stderr or ''))[-1000:])
                    return 2
        if fundos:
            time.sleep(float(antes[0].get('esperarInicio') or 2))  # o laço em paralelo sobe antes do 1º cenário

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
    finally:
        encerrar_fundo(fundos)  # nada da rodada fica vivo, nem com erro ou Ctrl-C

    valores['solicitacoes'] = ' '.join(str(r['solicitacao']) for r in resultados if r.get('solicitacao'))
    depois_falhou = False
    for i, g in enumerate(depois, 1):
        cmd = montar_comando(g, valores)
        if simular:
            print('  depoisDaRodada %d: %s' % (i, cmd))
            continue
        try:
            p = subprocess.run(['/bin/bash', '-c', cmd], env=fl.env, capture_output=True, text=True,
                               timeout=float(g.get('tempoLimite') or 300))
            codigo, texto = p.returncode, (p.stdout or '') + (p.stderr or '')
        except subprocess.TimeoutExpired:
            codigo, texto = 'tempo esgotado', ''
        print('  depoisDaRodada %d (código %s): %s' % (i, codigo, g.get('descricao', cmd)))
        if texto.strip():
            print('    ' + texto.strip()[-1500:].replace('\n', '\n    '))
        rodada['depois'].append({'comando': cmd, 'codigo': codigo, 'saida': texto[-2000:]})
        depois_falhou = depois_falhou or codigo != 0

    if simular:
        return 0

    # Solicitações da rodada ainda abertas: nada fica esquecido no meio do fluxo
    abertas = []
    for r in resultados:
        if r.get('solicitacao'):
            est, erro = fl.estado(r['solicitacao'])
            r['final'] = {'status': est and est.get('status'), 'etapa': est and est.get('etapa')}
            if est and est.get('status') == 'OPEN':
                abertas.append('%d (%s) na etapa %s' % (r['solicitacao'], r['id'], est.get('etapa')))
    print('\nabertas: %s' % ('; '.join(abertas) if abertas else 'nenhuma'))
    os.makedirs(saida, exist_ok=True)
    sufixo = ('-' + re.sub(r'\W+', '_', '_'.join(filtro))[:60]) if filtro else ''
    destino = os.path.join(saida, 'fluxo-%s-%s%s.json' % (re.sub(r'\W+', '_', suite['processo'])[:40],
                                                         suite['execucao'], sufixo))
    if os.path.exists(destino):  # mesma execucao fixada na suíte: não sobrescreve
        destino = destino[:-5] + time.strftime('-%H%M%S') + '.json'
    json.dump({'execucao': suite['execucao'], 'processo': suite['processo'], 'servidor': srv.get('nome'),
               'ultimaAntesDaRodada': valores['ultima'] if isinstance(valores['ultima'], int) else None, 'rodada': rodada, 'abertas': abertas,
               'cenarios': resultados}, open(destino, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
    placar = {}
    for r in resultados:
        placar[r['resultado']] = placar.get(r['resultado'], 0) + 1
    print('\nplacar: %s · resultado em %s' % (json.dumps(placar, ensure_ascii=False), destino))
    if depois_falhou:
        print('ATENÇÃO: algum depoisDaRodada terminou com código diferente de 0 (ver acima)')
    return 0 if all(r['resultado'] == 'aprovado' for r in resultados) and not depois_falhou else 1


if __name__ == '__main__':
    sys.exit(main())
