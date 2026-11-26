#!/usr/bin/env bash
# Prepara el servidor para el Atlas. Una vez, con sudo, desde la carpeta donde estan los archivos de deploy/:
#
#   sudo bash preparar.sh DUENO/REPO-DE-DATOS ruta/al/manifiesto.yaml
#
# Crea el usuario de sistema `atlas`, /srv/atlas con sus permisos, un archivo de token vacio
# root:atlas 640 (lo rellena una persona, nunca por linea de comandos) y publica 127.0.0.1:8790 en
# la red privada con `tailscale serve` en el 8443. Nunca con Funnel. Se puede repetir sin romper nada.
set -euo pipefail

[[ "$(id -u)" == 0 ]] || { echo "ejecutalo con sudo" >&2; exit 1; }
REPO="${1:?falta DUENO/REPO-DE-DATOS}"
MANIFIESTO="${2:?falta la ruta del manifiesto}"
DESPLIEGA="${SUDO_USER:?ejecutalo con sudo desde tu usuario, no como root directo}"
ORIGEN="$(cd "$(dirname "$0")" && pwd)"
PUERTO_LOCAL=8790
PUERTO_TAILNET=8443

if ss -ltnH | awk '{print $4}' | grep -qE ":${PUERTO_LOCAL}$"; then
  docker ps --format '{{.Names}}' | grep -qx atlas || { echo "el ${PUERTO_LOCAL} esta ocupado" >&2; exit 1; }
fi
if tailscale serve status 2>/dev/null | grep -q ":${PUERTO_TAILNET}" && ! tailscale serve status | grep -A1 ":${PUERTO_TAILNET}" | grep -q "127.0.0.1:${PUERTO_LOCAL}"; then
  echo "el ${PUERTO_TAILNET} de tailscale serve ya apunta a otra cosa" >&2; exit 1
fi

id atlas >/dev/null 2>&1 || useradd --system --no-create-home --shell /usr/sbin/nologin atlas
install -d -o root -g root -m 755 /srv/atlas
install -d -o root -g atlas -m 711 /srv/atlas/secrets
install -d -o "$DESPLIEGA" -g "$DESPLIEGA" -m 755 /srv/atlas/despliegue
install -o root -g root -m 644 "$ORIGEN/compose.yaml" /srv/atlas/compose.yaml
install -o root -g root -m 755 "$ORIGEN/desplegar.sh" /srv/atlas/desplegar.sh
umask 022
printf 'ATLAS_REPO=%s\nATLAS_MANIFIESTO=%s\nATLAS_INTERVALO=300\n' "$REPO" "$MANIFIESTO" > /srv/atlas/atlas.env
chown root:root /srv/atlas/atlas.env
chmod 644 /srv/atlas/atlas.env
if [[ ! -f /srv/atlas/secrets/github_token ]]; then
  install -o root -g atlas -m 640 /dev/null /srv/atlas/secrets/github_token
fi
chown root:atlas /srv/atlas/secrets/github_token
chmod 640 /srv/atlas/secrets/github_token

tailscale serve --bg --https="${PUERTO_TAILNET}" "http://127.0.0.1:${PUERTO_LOCAL}"

echo "--- listo"
stat -c '%U:%G %a %n' /srv/atlas /srv/atlas/secrets /srv/atlas/secrets/github_token /srv/atlas/despliegue /srv/atlas/atlas.env /srv/atlas/compose.yaml /srv/atlas/desplegar.sh
id atlas
tailscale serve status
