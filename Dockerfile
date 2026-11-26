# Imagen del Atlas: la web construida y el servicio Python que la sirve con el mapa.
# Sin datos: el manifiesto y los estados se leen en tiempo de ejecucion con un token de solo lectura.

FROM node:22-slim AS web
WORKDIR /web
COPY web/package.json web/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY web/ ./
RUN npm run build

FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    ATLAS_WEB=/app/web
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY atlas/ atlas/
COPY --from=web /web/dist/ web/
# Usuario sin privilegios por defecto; el compose lo fija al del sistema `atlas` del VPS.
USER 65532:65532
EXPOSE 8790
HEALTHCHECK --interval=60s --timeout=5s --start-period=30s --retries=3 \
  CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8790/salud', timeout=4)"]
CMD ["uvicorn", "atlas.servidor:crear_desde_entorno", "--factory", "--host", "0.0.0.0", "--port", "8790", "--no-server-header"]
