#!/usr/bin/env bash
# Despliega el Atlas en el servidor, solo por digest.
#
#   sudo /srv/atlas/desplegar.sh ghcr.io/DUENO/atlas@sha256:<64 hex>
#
# Espera en /srv/atlas: compose.yaml, atlas.env (root:atlas 640) y secrets/github_token
# (root:atlas 640, en secrets/ root:atlas 750). El usuario de sistema `atlas` tiene que existir.
# Si el contenedor no queda healthy en 90 s, vuelve a la imagen anterior (si la hay) y sale con 1.
# Volver atras a mano: sudo /srv/atlas/desplegar.sh "$(cat /srv/atlas/imagen.anterior)"
set -euo pipefail

DIR=/srv/atlas
IMAGEN="${1:-}"
if [[ ! "$IMAGEN" =~ ^ghcr\.io/[a-z0-9-]+/atlas@sha256:[0-9a-f]{64}$ ]]; then
  echo "uso: $0 ghcr.io/DUENO/atlas@sha256:<digest>  (solo por digest, nunca por tag)" >&2
  exit 2
fi
for f in "$DIR/compose.yaml" "$DIR/atlas.env" "$DIR/secrets/github_token"; do
  [[ -f "$f" ]] || { echo "falta $f" >&2; exit 2; }
done
[[ "$(stat -c '%U:%G %a' "$DIR/secrets/github_token")" == "root:atlas 640" ]] || {
  echo "secrets/github_token tiene que ser root:atlas 640" >&2; exit 2; }

ATLAS_UID="$(id -u atlas)"
ATLAS_GID="$(getent group atlas | cut -d: -f3)"
export ATLAS_UID ATLAS_GID

arrancar() {
  ATLAS_IMAGEN="$1" docker compose --project-directory "$DIR" -f "$DIR/compose.yaml" up -d --remove-orphans
}

esperar_sano() {
  local estado=""
  for _ in $(seq 1 45); do
    estado="$(docker inspect -f '{{if .State.Health}}{{.State.Health.Status}}{{else}}sin-healthcheck{{end}}' atlas 2>/dev/null || echo no-existe)"
    [[ "$estado" == "healthy" ]] && return 0
    sleep 2
  done
  echo "el contenedor no queda healthy (estado: $estado)" >&2
  return 1
}

anterior="$(cat "$DIR/imagen" 2>/dev/null || true)"
docker pull -q "$IMAGEN"
arrancar "$IMAGEN"
if esperar_sano; then
  if [[ -n "$anterior" && "$anterior" != "$IMAGEN" ]]; then
    echo "$anterior" > "$DIR/imagen.anterior"
  fi
  echo "$IMAGEN" > "$DIR/imagen"
  echo "desplegado $IMAGEN"
  echo "volver atras: sudo $DIR/desplegar.sh \"\$(cat $DIR/imagen.anterior)\""
  exit 0
fi
docker logs --tail 30 atlas >&2 || true
if [[ -n "$anterior" && "$anterior" != "$IMAGEN" ]]; then
  echo "vuelvo a $anterior" >&2
  arrancar "$anterior"
  esperar_sano && echo "de vuelta en $anterior" >&2
fi
exit 1
