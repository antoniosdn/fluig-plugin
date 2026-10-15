#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Confere (e, com --corrigir, conserta) um diagrama .process do Fluig (Graphiti/Eclipse).

Uso:
  python3 verificar_process.py <arquivo.process> [--corrigir]

Regras conferidas:
  POS-003  a âncora 0 da atividade de origem não lista a conexão em outgoingConnections
  POS-004  a âncora 0 da atividade de destino não lista a conexão em incomingConnections
  POS-005  a âncora 0 lista uma conexão que não sai/chega nela (referência sobrando)
  EXE-001  tarefa de serviço em segundo plano (executionType="1") sem evento de erro anexo
           (attachedEvents) que exista e tenha saída; o releaseProcess do Fluig recusa a versão

Como o Graphiti referencia as conexões: cada <connections> do diagrama é "/0/@connections.N",
onde N é a posição na ordem do arquivo (a partir de 0), não o id do flow. Inserir, remover ou
reordenar uma conexão muda o índice de todas as seguintes. Os <children> de primeiro nível podem
aparecer depois do bloco de conexões e dos <styles>.

--corrigir reescreve só os atributos outgoingConnections/incomingConnections da âncora 0 de cada
atividade, a partir das conexões (EXE-001 não é corrigido: depende do desenho do fluxo).
O resto do arquivo fica byte a byte igual.

Saída: 0 sem problemas, 1 com problemas (ou com EXE-001 depois de corrigir), 2 erro de uso.
"""
import re
import sys
import xml.etree.ElementTree as ET

BPMN = '{http://www.omg.org/spec/BPMN/20100524/MODEL-XMI}'


def ancora(ref):
    """'/0/@children.8/@anchors.0' -> (8, 0)"""
    m = re.match(r'^/0/@children\.(\d+)/@anchors\.(\d+)$', ref or '')
    if not m:
        raise ValueError('referência de âncora inesperada: %r' % ref)
    return int(m.group(1)), int(m.group(2))


def carregar(caminho):
    raiz = ET.parse(caminho).getroot()
    diag = [e for e in raiz if e.tag.endswith('Diagram')]
    if not diag:
        raise ValueError('pi:Diagram não encontrado')
    diag = diag[0]
    return raiz, diag, diag.findall('children'), diag.findall('connections')


def esperado(filhos, conexoes):
    """Por índice de atividade: (lista de saída, lista de chegada) que a âncora 0 deve ter."""
    saida = {i: [] for i in range(len(filhos))}
    chegada = {i: [] for i in range(len(filhos))}
    for i, c in enumerate(conexoes):
        a, ai = ancora(c.get('start'))
        b, bi = ancora(c.get('end'))
        if ai != 0 or bi != 0:
            raise ValueError('conexão %d usa âncora diferente de 0 (start=%s end=%s)'
                             % (i, c.get('start'), c.get('end')))
        saida[a].append('/0/@connections.%d' % i)
        chegada[b].append('/0/@connections.%d' % i)
    return saida, chegada


def nome(filho):
    link = filho.find('link')
    return link.get('businessObjects') if link is not None else '?'


def conferir_conexoes(filhos, conexoes):
    saida, chegada = esperado(filhos, conexoes)
    problemas = []
    for i, c in enumerate(conexoes):
        a, _ = ancora(c.get('start'))
        b, _ = ancora(c.get('end'))
        ref = '/0/@connections.%d' % i
        anc_a = filhos[a].findall('anchors')[0]
        anc_b = filhos[b].findall('anchors')[0]
        if ref not in (anc_a.get('outgoingConnections') or '').split():
            problemas.append('POS-003 conexão %d: origem %s não a lista em outgoingConnections' % (i, nome(filhos[a])))
        if ref not in (anc_b.get('incomingConnections') or '').split():
            problemas.append('POS-004 conexão %d: destino %s não a lista em incomingConnections' % (i, nome(filhos[b])))
    for k, f in enumerate(filhos):
        ancs = f.findall('anchors')
        if not ancs:
            continue
        for attr, certo in (('outgoingConnections', saida[k]), ('incomingConnections', chegada[k])):
            sobra = set((ancs[0].get(attr) or '').split()) - set(certo)
            if sobra:
                problemas.append('POS-005 %s: %s com referência sobrando %s' % (nome(f), attr, ' '.join(sorted(sobra))))
    return problemas


def conferir_servicos(raiz):
    elems = dict((e.get('id'), e) for e in raiz.iter() if e.tag.startswith(BPMN) and e.get('id'))
    problemas = []
    for i, e in elems.items():
        if e.get('type') != '82' or e.get('executionType') != '1':
            continue
        anexos = (e.get('attachedEvents') or '').split()
        ok = [a for a in anexos if a in elems and elems[a].tag.endswith('IntermediateEvent') and elems[a].get('outgoing')]
        if not ok:
            problemas.append('EXE-001 %s "%s": executionType=1 sem evento de erro anexo com saída '
                             '(attachedEvents -> BpmnIntermediateEvent tipo 43 -> tarefa de tratamento)'
                             % (i, e.get('name')))
    return problemas


def corrigir(caminho, filhos, conexoes):
    saida, chegada = esperado(filhos, conexoes)
    texto = open(caminho, 'rb').read().decode('utf-8')
    # Filhos de primeiro nível do pi:Diagram: linhas "    <children" (4 espaços), em qualquer posição
    inicios = [m.start() for m in re.finditer(r'(?m)^    <children\b', texto)]
    if len(inicios) != len(filhos):
        raise ValueError('esperava %d <children> de primeiro nível com 4 espaços, achei %d; corrija à mão'
                         % (len(filhos), len(inicios)))
    partes = []
    pos = 0
    for k, ini in enumerate(inicios):
        m = re.compile(r'<anchors\b[^>]*?/?>').search(texto, ini)
        fim_filho = inicios[k + 1] if k + 1 < len(inicios) else len(texto)
        if not m or m.start() > fim_filho:
            if saida[k] or chegada[k]:
                raise ValueError('atividade %d sem <anchors> mas com conexões' % k)
            continue
        tag = m.group(0)
        nova = re.sub(r'\s(outgoingConnections|incomingConnections)="[^"]*"', '', tag)
        extra = ''
        if saida[k]:
            extra += ' outgoingConnections="%s"' % ' '.join(saida[k])
        if chegada[k]:
            extra += ' incomingConnections="%s"' % ' '.join(chegada[k])
        fecho = '/>' if nova.endswith('/>') else '>'
        nova = nova[:-len(fecho)] + extra + fecho
        partes.append(texto[pos:m.start()])
        partes.append(nova)
        pos = m.end()
    partes.append(texto[pos:])
    open(caminho, 'wb').write(''.join(partes).encode('utf-8'))


def main(argv):
    args = [a for a in argv if not a.startswith('--')]
    if len(args) != 1 or any(a not in ('--corrigir',) for a in argv if a.startswith('--')):
        print(__doc__)
        return 2
    caminho = args[0]
    try:
        raiz, diag, filhos, conexoes = carregar(caminho)
        problemas = conferir_conexoes(filhos, conexoes)
        if problemas and '--corrigir' in argv:
            corrigir(caminho, filhos, conexoes)
            print('Corrigido: %d problema(s) de referência de conexão.' % len(problemas))
            raiz, diag, filhos, conexoes = carregar(caminho)
            problemas = conferir_conexoes(filhos, conexoes)
        problemas += conferir_servicos(raiz)
    except (ValueError, ET.ParseError) as e:
        print('ERRO: %s' % e)
        return 2
    print('%d atividade(s), %d conexão(ões), %d problema(s)' % (len(filhos), len(conexoes), len(problemas)))
    for p in problemas:
        print('  ' + p)
    return 1 if problemas else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
