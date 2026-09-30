#!/usr/bin/env bash
# publicar-layout.sh — publica um layout WCM com o fluigcli.
#
# O fluigcli não tem comando `layout`. O deploy nativo do WCM identifica o
# destino só pelo nome do arquivo (<código>.war). Por isso `widget export
# --force` publica o layout, desde que a CLI encontre a pasta em
# wcm/widget/<código>/. O script cria esse atalho para wcm/layout/<código>,
# publica, remove o atalho e confere os JS servidos.
#
# Uso:
#   publicar-layout.sh <código> --server <nome> [--env-file <arquivo>] [--project <raiz>]
#
# Credencial: --env-file, ou .fluigcli/<servidor>.env se existir, ou o que já
# estiver no ambiente/keyring. A senha nunca é impressa.
#
# Produção (env=prod em .fluigcli/servers.json): só roda em terminal
# interativo, sem --yes; a confirmação fica com o próprio fluigcli.

set -euo pipefail

uso() {
  echo "uso: publicar-layout.sh <código> --server <nome> [--env-file <arquivo>] [--project <raiz>]" >&2
  exit 2
}

erro() { echo "erro: $1" >&2; exit "${2:-1}"; }

CODIGO=""
SERVIDOR=""
ENV_FILE=""
ROOT=""

while [ $# -gt 0 ]; do
  case "$1" in
    --server)   SERVIDOR="${2:-}"; shift 2 ;;
    --env-file) ENV_FILE="${2:-}"; shift 2 ;;
    --project)  ROOT="${2:-}"; shift 2 ;;
    -h|--help)  uso ;;
    -*)         erro "flag desconhecida: $1" 2 ;;
    *)          [ -z "$CODIGO" ] || erro "código informado duas vezes" 2; CODIGO="$1"; shift ;;
  esac
done

[ -n "$CODIGO" ] || uso
[ -n "$SERVIDOR" ] || erro "--server é obrigatório (nunca depender de FLUIGCLI_SERVER)" 2

# Raiz do projeto: sobe a partir do diretório atual até achar .fluigcli/servers.json
if [ -z "$ROOT" ]; then
  d="$PWD"
  while [ "$d" != "/" ]; do
    if [ -f "$d/.fluigcli/servers.json" ]; then ROOT="$d"; break; fi
    d="$(dirname "$d")"
  done
fi
[ -n "$ROOT" ] && [ -f "$ROOT/.fluigcli/servers.json" ] || erro "raiz do projeto não encontrada (.fluigcli/servers.json); use --project"

LAYOUT="$ROOT/wcm/layout/$CODIGO"
INFO="$LAYOUT/src/main/resources/application.info"
[ -f "$INFO" ] || erro "não encontrado: wcm/layout/$CODIGO/src/main/resources/application.info" 4
grep -q '^application\.type=layout' "$INFO" || erro "application.info não tem application.type=layout"

# Dados do servidor em .fluigcli/servers.json
read -r SRV_ENV SRV_URL < <(python3 - "$ROOT/.fluigcli/servers.json" "$SERVIDOR" <<'PY'
import json, sys
cfg = json.load(open(sys.argv[1]))
for s in cfg.get("servers", []):
    if s.get("name") == sys.argv[2]:
        ssl = s.get("ssl", True)
        port = int(s.get("port") or (443 if ssl else 80))
        esquema = "https" if ssl else "http"
        padrao = (ssl and port == 443) or (not ssl and port == 80)
        url = "%s://%s%s" % (esquema, s["host"], "" if padrao else ":%d" % port)
        print(s.get("env", "?"), url)
        break
PY
) || true
[ -n "${SRV_URL:-}" ] || erro "servidor '$SERVIDOR' não está em .fluigcli/servers.json" 4

PROD=0
if [ "$SRV_ENV" = "prod" ]; then
  PROD=1
  [ -t 0 ] && [ -t 1 ] || erro "servidor '$SERVIDOR' é produção: rode em terminal interativo (o fluigcli pede confirmação)" 2
fi

FLUIGCLI="$(command -v fluigcli || true)"
[ -n "$FLUIGCLI" ] || FLUIGCLI="$HOME/.local/bin/fluigcli"
[ -x "$FLUIGCLI" ] || erro "fluigcli não encontrado no PATH nem em ~/.local/bin"

# Sintaxe dos JS do layout (browser; só checagem de parse)
NODE="$(command -v node || true)"
for n in /opt/homebrew/bin/node /usr/local/bin/node; do
  [ -n "$NODE" ] || { [ -x "$n" ] && NODE="$n"; }
done
JS_LISTA=()
while IFS= read -r -d '' f; do JS_LISTA+=("$f"); done \
  < <(find "$LAYOUT/src/main/webapp/resources" -name '*.js' -type f -print0 2>/dev/null)
if [ -n "$NODE" ]; then
  for f in ${JS_LISTA[@]+"${JS_LISTA[@]}"}; do
    "$NODE" --check "$f" || erro "sintaxe inválida: ${f#$ROOT/}"
  done
  echo "node --check: ${#JS_LISTA[@]} arquivo(s) ok"
else
  echo "aviso: node não encontrado; checagem de sintaxe pulada" >&2
fi

# Credencial
if [ -z "$ENV_FILE" ] && [ -f "$ROOT/.fluigcli/$SERVIDOR.env" ]; then
  ENV_FILE="$ROOT/.fluigcli/$SERVIDOR.env"
fi
if [ -n "$ENV_FILE" ]; then
  [ -f "$ENV_FILE" ] || erro "env-file não encontrado: $ENV_FILE"
  set -a; . "$ENV_FILE"; set +a
fi
unset FLUIG_READONLY FLUIGCLI_SERVER

# Atalho temporário wcm/widget/<código> -> ../layout/<código>
WIDGET_DIR="$ROOT/wcm/widget"
LINK="$WIDGET_DIR/$CODIGO"
CRIOU_DIR=0
if [ -L "$LINK" ]; then
  [ "$(readlink "$LINK")" = "../layout/$CODIGO" ] || erro "wcm/widget/$CODIGO já é um atalho para outro lugar"
elif [ -e "$LINK" ]; then
  erro "wcm/widget/$CODIGO já existe como pasta real (widget com o mesmo código?)"
fi
[ -d "$WIDGET_DIR" ] || { mkdir -p "$WIDGET_DIR"; CRIOU_DIR=1; }

limpar() {
  rm -f "$LINK"
  [ "$CRIOU_DIR" = 1 ] && rmdir "$WIDGET_DIR" 2>/dev/null || true
}
trap limpar EXIT
ln -sfn "../layout/$CODIGO" "$LINK"

echo "publicando layout '$CODIGO' em '$SERVIDOR' ($SRV_URL)"
set +e
if [ "$PROD" = 1 ]; then
  "$FLUIGCLI" widget export "$CODIGO" --force --server "$SERVIDOR" --project "$ROOT"
else
  FLUIGCLI_NON_INTERACTIVE=1 "$FLUIGCLI" widget export "$CODIGO" --force \
    --server "$SERVIDOR" --project "$ROOT" --json --non-interactive -y
fi
RC=$?
set -e
limpar
trap - EXIT
[ ! -e "$LINK" ] || erro "atalho wcm/widget/$CODIGO não foi removido"
[ "$RC" = 0 ] || erro "fluigcli widget export terminou com exit $RC" "$RC"

# Conferência: a instalação é assíncrona; tenta por até ~60s
[ ${#JS_LISTA[@]} -gt 0 ] || { echo "sem JS para conferir; publicação enviada"; exit 0; }
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
FALHAS=0
for f in "${JS_LISTA[@]}"; do
  rel="${f#$LAYOUT/src/main/webapp/}"
  ok=0
  for _ in $(seq 1 12); do
    code="$(curl -sk -o "$TMP/js" -w '%{http_code}' "$SRV_URL/$CODIGO/$rel?v=$(date +%s)" || true)"
    if [ "$code" = 200 ] && cmp -s "$TMP/js" "$f"; then ok=1; break; fi
    sleep 5
  done
  if [ "$ok" = 1 ]; then echo "conferido: $rel (HTTP 200, idêntico ao local)"
  else echo "divergente: $rel (último HTTP $code)" >&2; FALHAS=$((FALHAS + 1)); fi
done
[ "$FALHAS" = 0 ] || erro "$FALHAS arquivo(s) não conferem no servidor"
echo "layout '$CODIGO' publicado em '$SERVIDOR'"
