#!/usr/bin/env bash
# Despliega el Atlas en el servidor, solo por digest. Lo ejecuta un usuario del grupo docker, sin sudo.
#
#   /srv/atlas/desplegar.sh ghcr.io/DUENO/atlas@sha256:<64 hex>
#
# Lo deja preparado deploy/preparar.sh (una vez, con sudo):
#   /srv/atlas/compose.yaml y atlas.env       root:root 644
#   /srv/atlas/secrets/                       root:atlas 711 (se puede comprobar, no listar)
#   /srv/atlas/secrets/github_token           root:atlas 640 (solo lo leen root y el contenedor)
#   /srv/atlas/despliegue/                    del usuario que despliega: imagen actual y anterior
# Si el contenedor no queda healthy en 90 s, vuelve a la imagen anterior (si la hay) y sale con 1.
# Volver atras a mano: /srv/atlas/desplegar.sh "$(cat /srv/atlas/despliegue/imagen.anterior)"
set -euo pipefail

DIR=/srv/atlas
ESTADO="$DIR/despliegue"
IMAGEN="${1:-}"
if [[ ! "$IMAGEN" =~ ^ghcr\.io/[a-z0-9-]+/atlas@sha256:[0-9a-f]{64}$ ]]; then
  echo "uso: $0 ghcr.io/DUENO/atlas@sha256:<digest>  (solo por digest, nunca por tag)" >&2
  exit 2
fi
for f in "$DIR/compose.yaml" "$DIR/atlas.env"; do
  [[ -f "$f" ]] || { echo "falta $f" >&2; exit 2; }
done
TOKEN="$DIR/secrets/github_token"
[[ -f "$TOKEN" ]] || { echo "falta $TOKEN" >&2; exit 2; }
[[ "$(stat -c '%U:%G %a' "$TOKEN")" == "root:atlas 640" ]] || { echo "$TOKEN tiene que ser root:atlas 640" >&2; exit 2; }
[[ "$(stat -c '%s' "$TOKEN")" -gt 20 ]] || { echo "$TOKEN parece vacio" >&2; exit 2; }
[[ -w "$ESTADO" ]] || { echo "$ESTADO no es escribible por $(id -un)" >&2; exit 2; }

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

anterior="$(cat "$ESTADO/imagen" 2>/dev/null || true)"
docker pull -q "$IMAGEN"
arrancar "$IMAGEN"
if esperar_sano; then
  if [[ -n "$anterior" && "$anterior" != "$IMAGEN" ]]; then
    echo "$anterior" > "$ESTADO/imagen.anterior"
  fi
  echo "$IMAGEN" > "$ESTADO/imagen"
  echo "desplegado $IMAGEN"
  echo "volver atras: $DIR/desplegar.sh \"\$(cat $ESTADO/imagen.anterior)\""
  exit 0
fi
docker logs --tail 30 atlas >&2 || true
if [[ -n "$anterior" && "$anterior" != "$IMAGEN" ]]; then
  echo "vuelvo a $anterior" >&2
  arrancar "$anterior"
  esperar_sano && echo "de vuelta en $anterior" >&2
fi
exit 1
