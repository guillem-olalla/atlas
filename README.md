# Atlas

Mapa vivo de un harness de agentes: qué piezas hay (agentes, servicios, workflows, almacenes, APIs), cómo se llaman entre sí y en qué estado está cada una. Se pinta en 2D por capas, una columna por capa, con React Flow y la disposición de ELK.

Este repo es público y **no lleva datos**. El manifiesto real y los estados se leen en tiempo de ejecución, en el servidor, con un token de solo lectura. Aquí solo hay código y un manifiesto de ejemplo con nombres genéricos (`tests/datos/harness.yaml`).

## Qué hace la v1

- Lee un manifiesto YAML (nodos y aristas) y las issues del repo de datos, y calcula el estado de cada nodo:
  - con `issue`: cerrada = hecho; abierta con `bloqueado` = bloqueado; abierta con `en-curso` = en curso; el resto = pendiente (si lleva las dos etiquetas, gana `bloqueado`);
  - sin `issue`: hecho si `existe: true`, pendiente si no.
- Web: selector de fase (se ven esa fase y las anteriores), filtros por capa, estado, tipo, cliente y marca `personal`, y aislar uno o varios nodos (o un proyecto entero) con sus vecinos a N saltos.
- Avisos visibles si los datos tienen más de 15 minutos, si el token caduca en menos de 14 días o si la última lectura falló.
- Línea de comandos para el repo de datos:
  - `python -m atlas validar MANIFIESTO [--issues issues.json] [--local REPO=CARPETA]`: forma del manifiesto, que cada issue tenga su nodo (o la etiqueta `fuera-del-camino-critico`) y que cada pieza desplegable del repo esté en algún `cubre`.
  - `python -m atlas catalogo MANIFIESTO SALIDA --url-issues URL`: catálogo de agentes en markdown.
  - `python -m atlas revision MANIFIESTO --salida INFORME [--publico REPO] [--datos REPO]`: revisión nocturna de desajustes entre `cubre` y los repos, repos públicos sin nodo y nombres privados en el repo público.

Una pieza desplegable es un workflow de Actions, un servicio de Compose, un flujo de n8n exportado (`n8n/*.json`) o una unidad de systemd (`.service`, `.timer`). En `cubre` se escribe como `dueno/repo:ruta` o `dueno/repo:ruta#servicio`.

## Desarrollo

Nada se instala ni se construye en el portátil: `npm ci`, los tests y el build corren en GitHub Actions (`ci.yml`). El `package-lock.json` se genera con el workflow `lockfile` y se sube en un PR.

- `ci.yml`: `python` (pytest), `web` (vitest y build) e `imagen` (build de Docker y arranque sin root, de solo lectura y con 128 MB). Los tres son obligatorios en `main`.
- `publicar.yml`: en cada push a `main`, publica la imagen en GHCR y deja su digest en el resumen del job.

## Despliegue

Solo por digest, con `deploy/desplegar.sh`, en un contenedor sin root, de solo lectura, con `mem_limit` de 128 MB, escuchando en `127.0.0.1:8790` y publicado solo en la red privada con `tailscale serve` (nunca con Funnel). El token va como secreto de Compose en un archivo `root:atlas 640`.

1. Una vez, con sudo: `sudo bash deploy/preparar.sh DUENO/REPO-DE-DATOS ruta/al/manifiesto.yaml`. Crea el usuario `atlas`, `/srv/atlas`, el archivo vacío del token y `tailscale serve` en el 8443.
2. Una persona rellena el token sin que pase por la línea de comandos: `sudo sh -c 'cat > /srv/atlas/secrets/github_token'`, pega, Intro y Ctrl-D.
3. Cada versión, sin sudo, desde un usuario del grupo docker: `/srv/atlas/desplegar.sh ghcr.io/DUENO/atlas@sha256:…`, con el digest que deja `publicar.yml`.

## v2

Este mismo servicio suma el recolector de eventos: `POST /evento` con token por emisor, `GET /flujo` por SSE y `GET /estado`, con SQLite y 30 días de retención. La web añade una suscripción al flujo.
