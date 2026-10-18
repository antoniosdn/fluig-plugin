#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Confere a máquina e o projeto do cliente para o plugin fluig. Só lê; não instala nada.

Uso:
  python3 conferir_ambiente.py [--projeto <pasta>] [--mcp-dir <pasta do mcp-fluig>] [--json]

  --projeto   raiz do projeto do cliente (default: pasta atual)
  --mcp-dir   pasta do mcp-fluig (default: FLUIG_MCP_DIR; sem ela, procura em lugares comuns)
  --json      saída JSON (para o agente)

Itens conferidos:
  fluigcli ≥ 0.9.6 e servidor cadastrado (fluigcli server list --json, na pasta do projeto)
  Node 20+, Python 3.8+, Chrome/Chromium/Brave, Java 8+ (FLUIG_MCP_JAVA → JAVA_HOME → PATH)
  mcp-fluig: pasta, origin do fork antoniosdn/fluig-mcp, node_modules, fluig_flow_* em --list
  FLUIG_MCP_DIR (ambiente ou env de .claude/settings*.json do projeto)
  servidor MCP registrado (.mcp.json do projeto e ~/.claude.json), sem mostrar valores de env
  conversor do Studio no cache (~/.fluig-mcp ou FLUIG_MCP_CACHE), com a conferência do mcp-fluig
  .gitignore do projeto cobrindo .env e .fluigcli/*.env

Nenhum valor de variável de ambiente de servidor MCP é impresso (pode ser senha).

Saída: 0 sem item FALTA, 1 com algum FALTA, 2 erro de uso.
"""
import json
import os
import re
import shutil
import subprocess
import sys

FORK = 'antoniosdn/fluig-mcp'
ORIGINAL = 'alucardigo/fluig-mcp'
FLUIGCLI_MIN = (0, 9, 6)
STUDIOS = ['1.8.2.0', '2.0.0.2']
FERRAMENTAS_FLUXO = ['fluig_flow_validate', 'fluig_flow_generate', 'fluig_flow_regenerate',
                     'fluig_flow_read', 'fluig_flow_deploy']
NAVEGADORES = ['/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
               '/Applications/Chromium.app/Contents/MacOS/Chromium',
               '/Applications/Brave Browser.app/Contents/MacOS/Brave Browser',
               '/usr/bin/google-chrome', '/usr/bin/google-chrome-stable',
               '/usr/bin/chromium', '/usr/bin/chromium-browser']
CANDIDATOS_MCP = ['~/DESENV/mcp-fluig', '~/DESENV/fluig-mcp', '~/mcp-fluig', '~/fluig-mcp',
                  '~/dev/fluig-mcp', '~/projetos/fluig-mcp']

itens = []


def item(chave, status, titulo, detalhe='', acao='', escreve=False):
    """status: OK, FALTA, AVISO. escreve=True: a ação grava algo (pedir autorização)."""
    itens.append({'item': chave, 'status': status, 'titulo': titulo, 'detalhe': detalhe,
                  'acao': acao, 'escreve': escreve})


def rodar(cmd, cwd=None, timeout=60, env=None):
    try:
        p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout, env=env)
        return p.returncode, p.stdout, p.stderr
    except FileNotFoundError:
        return None, '', 'não encontrado'
    except subprocess.TimeoutExpired:
        return None, '', 'tempo esgotado (%ss)' % timeout


def versao(texto):
    m = re.search(r'(\d+)\.(\d+)(?:\.(\d+))?', texto or '')
    return tuple(int(x or 0) for x in m.groups()) if m else None


def texto_versao(v):
    return '.'.join(str(x) for x in v)


# ---------------------------------------------------------------- fluigcli

def conferir_fluigcli(projeto):
    instalar = 'curl -fsSL https://raw.githubusercontent.com/alorenco/fluig-cli/main/install.sh | sh'
    if os.name == 'nt':
        instalar = 'irm https://raw.githubusercontent.com/alorenco/fluig-cli/main/install.ps1 | iex'
    rc, out, err = rodar(['fluigcli', '--version'])
    if rc is None:
        item('fluigcli', 'FALTA', 'fluigcli não instalado',
             'github.com/alorenco/fluig-cli (≥ %s)' % texto_versao(FLUIGCLI_MIN), instalar, True)
        return
    v = versao(out + err)
    if not v or v < FLUIGCLI_MIN:
        item('fluigcli', 'FALTA', 'fluigcli %s (precisa ≥ %s)' % (texto_versao(v) if v else '?',
             texto_versao(FLUIGCLI_MIN)), '', 'fluigcli upgrade', True)
    else:
        item('fluigcli', 'OK', 'fluigcli %s' % texto_versao(v))
    rc, out, err = rodar(['fluigcli', 'server', 'list', '--json'], cwd=projeto)
    dados = None
    for linha in (out or '').splitlines():
        if linha.strip().startswith('{'):
            try:
                dados = json.loads(linha)
            except ValueError:
                pass
    servidores = ((dados or {}).get('data') or {}).get('servers') or []
    if not servidores:
        item('fluigcli-servidor', 'FALTA', 'nenhum servidor cadastrado no fluigcli',
             'o usuário digita a senha no prompt do fluigcli (vai para o keyring); nunca pela conversa',
             'fluigcli server add --name <nome> --host <host> --port <porta> --username <usuario> '
             '--env hml --default   (rodar no terminal do usuário)', True)
        return
    padrao = dados['data'].get('default') or ''
    desc = ', '.join('%s%s (%s, %s)' % ('●' if s.get('name') == padrao else '', s.get('name'),
                                       s.get('env') or 'sem env', s.get('host'))
                     for s in servidores)
    if all((s.get('env') or '') == 'prod' for s in servidores):
        item('fluigcli-servidor', 'AVISO', 'só servidor de produção cadastrado', desc,
             'cadastrar um servidor de teste (env hml ou dev) para teste e geração de fluxo', True)
    else:
        item('fluigcli-servidor', 'OK', 'servidores no fluigcli: %s' % desc)


# ---------------------------------------------------------------- runtimes

def conferir_node():
    rc, out, err = rodar(['node', '--version'])
    v = versao(out) if rc == 0 else None
    if not v:
        item('node', 'FALTA', 'Node.js não encontrado', 'precisa 20+ (mcp-fluig e proxy_tela.mjs)',
             'instalar o Node.js 20 LTS ou mais novo (nodejs.org, brew install node, nvm)')
    elif v < (20, 6):
        item('node', 'FALTA', 'Node.js %s (precisa 20.6+)' % texto_versao(v),
             'mcp-fluig exige 20+; --env-file no registro do MCP exige 20.6+', 'atualizar o Node.js')
    else:
        item('node', 'OK', 'Node.js %s' % texto_versao(v))


def conferir_python():
    v = sys.version_info[:3]
    if v < (3, 8):
        item('python', 'FALTA', 'Python %s (precisa 3.8+)' % texto_versao(v), '', 'atualizar o Python 3')
    else:
        item('python', 'OK', 'Python %s' % texto_versao(v))


def conferir_navegador():
    achado = next((n for n in NAVEGADORES if os.path.exists(n)), None)
    if not achado:
        for nome in ('google-chrome', 'google-chrome-stable', 'chromium', 'chromium-browser', 'chrome'):
            achado = shutil.which(nome)
            if achado:
                break
    if achado:
        item('navegador', 'OK', 'navegador: %s' % achado)
    else:
        item('navegador', 'FALTA', 'Chrome/Chromium não encontrado',
             'camada 2 do fluig-teste (formulário headless)', 'instalar o Google Chrome ou o Chromium')


def resolver_java():
    for fonte in (os.environ.get('FLUIG_MCP_JAVA'), os.environ.get('JAVA_HOME')):
        if fonte and fonte.strip():
            base = fonte.strip().strip('"\'')
            for c in (base, os.path.join(base, 'bin', 'java'), os.path.join(base, 'Contents', 'Home', 'bin', 'java')):
                if os.path.isfile(c) and os.path.basename(c).startswith('java'):
                    return c
    return 'java'


def conferir_java():
    exe = resolver_java()
    rc, out, err = rodar([exe, '-version'])
    m = re.search(r'version\s+"([^"]+)"', (out or '') + (err or ''))
    if rc != 0 or not m:
        item('java', 'FALTA', 'Java não encontrado', 'ECM30 oficial do fluig-fluxo (conversor do Studio)',
             'instalar um JDK 8+ (ex.: Temurin 21, adoptium.net ou brew install --cask temurin) '
             'ou apontar FLUIG_MCP_JAVA para o java')
        return
    partes = re.split(r'[._-]', m.group(1))
    major = int(partes[1]) if partes[0] == '1' and len(partes) > 1 else int(partes[0])
    if major < 8:
        item('java', 'FALTA', 'Java %s (precisa 8+)' % m.group(1), '', 'instalar um JDK 8+')
    else:
        item('java', 'OK', 'Java %s (%s)' % (m.group(1), exe))


# ---------------------------------------------------------------- mcp-fluig

def env_settings(projeto):
    """FLUIG_MCP_DIR no env de .claude/settings.local.json ou settings.json do projeto."""
    for nome in ('settings.local.json', 'settings.json'):
        caminho = os.path.join(projeto, '.claude', nome)
        try:
            with open(caminho, encoding='utf-8') as f:
                valor = (json.load(f).get('env') or {}).get('FLUIG_MCP_DIR')
            if valor:
                return valor, '.claude/' + nome
        except (OSError, ValueError, AttributeError):
            pass
    return None, None


def achar_mcp_dir(arg, projeto):
    if arg:
        return os.path.abspath(os.path.expanduser(arg)), '--mcp-dir'
    if os.environ.get('FLUIG_MCP_DIR'):
        return os.path.abspath(os.path.expanduser(os.environ['FLUIG_MCP_DIR'])), 'FLUIG_MCP_DIR'
    valor, origem = env_settings(projeto)
    if valor:
        return os.path.abspath(os.path.expanduser(valor)), origem
    for c in CANDIDATOS_MCP:
        c = os.path.expanduser(c)
        if os.path.isfile(os.path.join(c, 'server.js')):
            return c, 'procurado'
    return None, None


def conferir_mcp(arg, projeto):
    clonar = 'git clone https://github.com/%s.git <pasta>/fluig-mcp && cd <pasta>/fluig-mcp && npm install' % FORK
    mcp_dir, origem = achar_mcp_dir(arg, projeto)
    if not mcp_dir or not os.path.isfile(os.path.join(mcp_dir, 'server.js')):
        item('mcp-fluig', 'FALTA', 'mcp-fluig não encontrado' + (' em %s' % mcp_dir if mcp_dir else ''),
             'precisa ser o fork %s (o original %s não tem fluig_flow_*)' % (FORK, ORIGINAL), clonar, True)
        item('fluig-mcp-dir', 'FALTA', 'FLUIG_MCP_DIR não definida', '',
             'definir depois de clonar (ver a skill fluig-preparar, passo FLUIG_MCP_DIR)', True)
        return None
    # FLUIG_MCP_DIR
    if origem in ('FLUIG_MCP_DIR',) or (origem or '').startswith('.claude/'):
        item('fluig-mcp-dir', 'OK', 'FLUIG_MCP_DIR = %s (%s)' % (mcp_dir, origem))
    else:
        item('fluig-mcp-dir', 'FALTA', 'FLUIG_MCP_DIR não definida',
             'mcp-fluig encontrado em %s (%s)' % (mcp_dir, origem),
             'definir FLUIG_MCP_DIR=%s no env de .claude/settings.local.json do projeto '
             'ou no perfil do shell' % mcp_dir, True)
    # origin
    rc, out, err = rodar(['git', '-C', mcp_dir, 'remote', 'get-url', 'origin'])
    url = (out or '').strip()
    if rc != 0 or not url:
        item('mcp-fluig-fork', 'AVISO', 'mcp-fluig em %s sem remote origin' % mcp_dir,
             'não dá para saber se é o fork; a conferência do fluig_flow_* abaixo decide')
    elif FORK in url:
        item('mcp-fluig-fork', 'OK', 'mcp-fluig do fork (%s)' % url)
    elif ORIGINAL in url:
        item('mcp-fluig-fork', 'FALTA', 'mcp-fluig é o original (%s)' % url,
             'o original não tem o gerador de fluxo (fluig_flow_*)',
             'clonar o fork em outra pasta: ' + clonar + '   (ou trocar o origin para o fork e git pull)', True)
    else:
        item('mcp-fluig-fork', 'AVISO', 'origin desconhecido: %s' % url,
             'esperado github.com/%s; a conferência do fluig_flow_* abaixo decide' % FORK)
    # node_modules
    if not os.path.isdir(os.path.join(mcp_dir, 'node_modules', '@modelcontextprotocol', 'sdk')):
        item('mcp-fluig-deps', 'FALTA', 'dependências do mcp-fluig não instaladas',
             mcp_dir, 'cd "%s" && npm install' % mcp_dir, True)
        return mcp_dir
    item('mcp-fluig-deps', 'OK', 'node_modules do mcp-fluig instalado')
    # --list (não carrega credencial)
    env = dict(os.environ)
    env.pop('FLUIG_READONLY', None)
    rc, out, err = rodar(['node', os.path.join(mcp_dir, 'server.js'), '--list'], cwd=mcp_dir, env=env)
    achadas = [f for f in FERRAMENTAS_FLUXO if re.search(r'\b%s\b' % f, out or '')]
    if rc != 0:
        ultima = ((err or out or '').strip().splitlines() or [''])[-1]
        item('mcp-fluig-fluxo', 'FALTA', 'node server.js --list falhou', ultima,
             'cd "%s" && npm install' % mcp_dir, True)
    elif len(achadas) == len(FERRAMENTAS_FLUXO):
        item('mcp-fluig-fluxo', 'OK', 'gerador de fluxo presente (%d ferramentas fluig_flow_*)' % len(achadas))
    else:
        faltam = [f for f in FERRAMENTAS_FLUXO if f not in achadas]
        item('mcp-fluig-fluxo', 'FALTA', 'faltam ferramentas do gerador: %s' % ', '.join(faltam),
             'versão sem o gerador de fluxo ou desatualizada',
             'cd "%s" && git pull && npm install   (precisa ser o fork %s)' % (mcp_dir, FORK), True)
    return mcp_dir


def servidores_mcp(projeto):
    """(nome, escopo, servidor) de .mcp.json do projeto e ~/.claude.json (local e usuário)."""
    achados = []
    try:
        with open(os.path.join(projeto, '.mcp.json'), encoding='utf-8') as f:
            for nome, s in (json.load(f).get('mcpServers') or {}).items():
                achados.append((nome, 'project (.mcp.json)', s))
    except (OSError, ValueError, AttributeError):
        pass
    try:
        with open(os.path.expanduser('~/.claude.json'), encoding='utf-8') as f:
            cfg = json.load(f)
        proj = (cfg.get('projects') or {}).get(projeto) or {}
        for nome, s in (proj.get('mcpServers') or {}).items():
            achados.append((nome, 'local (~/.claude.json, este projeto)', s))
        for nome, s in (cfg.get('mcpServers') or {}).items():
            achados.append((nome, 'user (~/.claude.json)', s))
    except (OSError, ValueError, AttributeError):
        pass
    return achados


def eh_mcp_fluig(s, mcp_dir):
    partes = [str(s.get('command') or '')] + [str(a) for a in (s.get('args') or [])]
    junto = ' '.join(partes)
    if mcp_dir and mcp_dir in junto:
        return True
    return bool(re.search(r'fluig-mcp|mcp-fluig', junto, re.I))


def conferir_registro(projeto, mcp_dir):
    regs = [(n, e, s) for (n, e, s) in servidores_mcp(projeto) if isinstance(s, dict) and eh_mcp_fluig(s, mcp_dir)]
    if not regs:
        item('mcp-registro', 'FALTA', 'mcp-fluig não registrado como servidor MCP deste projeto',
             'procurado em .mcp.json e ~/.claude.json; a prova final é ver ferramentas *fluig_flow_* na sessão',
             'claude mcp add fluig --scope local -- node --env-file="%s/.fluigcli/<servidor-teste>.env" '
             '"%s/server.js"   (credencial só no .env, fora do Git; vale em sessão nova)'
             % (projeto, mcp_dir or '<FLUIG_MCP_DIR>'), True)
        return
    for nome, escopo, s in regs:
        env = s.get('env') or {}
        senha = [k for k in env if 'PASS' in k.upper()]
        ro = str(env.get('FLUIG_READONLY', '')).lower() in ('1', 'true', 'yes', 'on')
        detalhe = 'variáveis no registro: %s' % (', '.join(sorted(env)) or 'nenhuma')
        if senha:
            item('mcp-registro', 'AVISO', 'servidor MCP "%s" (%s) com senha gravada na configuração' % (nome, escopo),
                 detalhe + ' (valores não mostrados)',
                 'trocar por node --env-file="%s/.fluigcli/<servidor>.env" (o usuário move a senha; ' % projeto +
                 'nunca pela conversa)' + ('; .mcp.json é versionado: tirar a senha antes de qualquer commit'
                                           if escopo.startswith('project') else ''), True)
        else:
            item('mcp-registro', 'OK', 'servidor MCP "%s" (%s)' % (nome, escopo), detalhe)
        if ro:
            item('mcp-readonly', 'AVISO', 'servidor MCP "%s" com FLUIG_READONLY=1' % nome,
                 'fluig_flow_deploy some; validar e gerar funcionam')


# ---------------------------------------------------------------- conversor

def dir_cache():
    v = (os.environ.get('FLUIG_MCP_CACHE') or '').strip()
    return os.path.abspath(os.path.expanduser(v)) if v else os.path.expanduser('~/.fluig-mcp')


def conferir_conversor(mcp_dir):
    cache = dir_cache()
    instalados = [v for v in STUDIOS if os.path.isfile(os.path.join(cache, 'studio', v, 'manifesto.json'))]
    instalar = ('node "%s/server.js" instalar-conversor --de <pasta plugins do Studio | raiz do Eclipse | studio.zip>'
                % (mcp_dir or '<FLUIG_MCP_DIR>'))
    if not instalados:
        item('conversor', 'FALTA', 'conversor do Studio não instalado em %s' % cache,
             'sem ele o ECM30 sai do plano B (W_ECM30_NAO_OFICIAL)',
             instalar + '   ou, com autorização (~43 MB de update.fluig.com e download.eclipse.org): '
             'node "%s/server.js" instalar-conversor --baixar 1.8.2.0' % (mcp_dir or '<FLUIG_MCP_DIR>'), True)
        return
    # integridade pela mesma função que o mcp-fluig usa a cada geração
    erros = {}
    if mcp_dir and os.path.isfile(os.path.join(mcp_dir, 'src', 'flow', 'conversor.js')) \
            and os.path.isdir(os.path.join(mcp_dir, 'node_modules')):
        url = 'file://' + os.path.join(mcp_dir, 'src', 'flow', 'conversor.js').replace(os.sep, '/')
        codigo = ("import { conferirConversor } from %s; import { join } from 'node:path';"
                  "const r = {}; for (const v of %s) { try { await conferirConversor(join(%s, 'studio', v), v); r[v] = null; }"
                  " catch (e) { r[v] = String(e && e.message || e); } } console.log(JSON.stringify(r));"
                  % (json.dumps(url), json.dumps(instalados), json.dumps(cache)))
        rc, out, err = rodar(['node', '--input-type=module', '-e', codigo], timeout=120)
        try:
            erros = json.loads((out or '').strip().splitlines()[-1])
        except (ValueError, IndexError):
            erros = {}
    for v in instalados:
        if erros.get(v):
            item('conversor-' + v, 'FALTA', 'conversor %s com cache inválido' % v, erros[v],
                 instalar + ' --versao %s --forcar' % v, True)
        else:
            conferido = ' (integridade conferida)' if v in erros else ''
            item('conversor-' + v, 'OK', 'conversor do Studio %s em %s%s' % (v, cache, conferido))
    if '2.0.0.2' not in instalados:
        item('conversor-2.0.0.2', 'AVISO', 'conversor 2.0.0.2 não instalado',
             'necessário para versaoAlvo 2.0; só existe por --de (plugins do Studio 2.0.0.2 ou studio.zip)',
             instalar + ' --versao 2.0.0.2', True)


# ---------------------------------------------------------------- projeto

def conferir_gitignore(projeto):
    rc, _, _ = rodar(['git', '-C', projeto, 'rev-parse', '--is-inside-work-tree'])
    if rc != 0:
        item('gitignore', 'AVISO', 'projeto fora de um repositório Git', projeto)
        return
    faltam, existentes = [], []
    candidatos = ['.env', '.fluigcli/teste.env']
    pasta = os.path.join(projeto, '.fluigcli')
    if os.path.isdir(pasta):
        candidatos += ['.fluigcli/' + n for n in sorted(os.listdir(pasta)) if n.endswith('.env')]
    for caminho in sorted(set(candidatos)):
        rc, _, _ = rodar(['git', '-C', projeto, 'check-ignore', '-q', '--no-index', caminho])
        if rc != 0:
            faltam.append(caminho)
            if os.path.isfile(os.path.join(projeto, caminho)):
                existentes.append(caminho)
    acao = 'acrescentar ao .gitignore: .env e .fluigcli/*.env'
    if existentes:
        item('gitignore', 'FALTA', 'arquivo de credencial fora do .gitignore: %s' % ', '.join(existentes),
             'credencial nunca vai para o Git (conferir também git ls-files)', acao, True)
    elif faltam:
        item('gitignore', 'AVISO', '.gitignore não cobre: %s (arquivo ainda não existe)' % ', '.join(faltam),
             'credencial nunca vai para o Git', acao, True)
    else:
        item('gitignore', 'OK', '.gitignore cobre .env e .fluigcli/*.env')


# ---------------------------------------------------------------- saída

def imprimir():
    rotulo = {'OK': '[ OK  ]', 'FALTA': '[FALTA]', 'AVISO': '[AVISO]'}
    for i in itens:
        print('%s %s' % (rotulo[i['status']], i['titulo']))
        if i['detalhe']:
            print('        %s' % i['detalhe'])
        if i['acao']:
            print('        → %s%s' % (i['acao'], '   [escreve: pedir autorização]' if i['escreve'] else ''))
    n = {s: sum(1 for i in itens if i['status'] == s) for s in ('OK', 'FALTA', 'AVISO')}
    print('\n%d ok, %d falta(m), %d aviso(s)' % (n['OK'], n['FALTA'], n['AVISO']))


def main(argv):
    projeto, mcp_arg, como_json = os.getcwd(), None, False
    args = list(argv)
    while args:
        a = args.pop(0)
        if a == '--projeto' and args:
            projeto = args.pop(0)
        elif a == '--mcp-dir' and args:
            mcp_arg = args.pop(0)
        elif a == '--json':
            como_json = True
        elif a in ('-h', '--help'):
            print(__doc__)
            return 0
        else:
            sys.stderr.write('argumento desconhecido: %s\n%s' % (a, __doc__))
            return 2
    projeto = os.path.abspath(os.path.expanduser(projeto))
    if not os.path.isdir(projeto):
        sys.stderr.write('projeto não existe: %s\n' % projeto)
        return 2

    conferir_fluigcli(projeto)
    conferir_node()
    conferir_python()
    conferir_navegador()
    conferir_java()
    mcp_dir = conferir_mcp(mcp_arg, projeto)
    conferir_registro(projeto, mcp_dir)
    conferir_conversor(mcp_dir)
    conferir_gitignore(projeto)

    if como_json:
        print(json.dumps({'projeto': projeto, 'mcpDir': mcp_dir, 'itens': itens}, ensure_ascii=False, indent=2))
    else:
        print('Projeto: %s\n' % projeto)
        imprimir()
    return 1 if any(i['status'] == 'FALTA' for i in itens) else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
